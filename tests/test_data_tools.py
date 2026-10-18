"""
Automated tests for data tools, column normalization, and validation tools.
"""

import io
import pytest
import pandas as pd
from tools.data_tools import (
    load_csv,
    normalize_dataset_columns,
    inspect_schema,
    detect_missing_values,
    detect_duplicates,
    validate_and_parse_dates,
)
from tools.validation_tools import (
    check_numeric_bounds,
    detect_outliers,
    validate_dataset_integrity,
)
from data.data_generator import generate_ecommerce_dataset


@pytest.fixture
def sample_valid_df():
    return generate_ecommerce_dataset(num_records=2000, seed=42)


def test_load_csv_from_buffer():
    csv_data = "Order ID,Revenue,Cost,Profit\nORD-1,100,60,40\nORD-2,200,120,80\n"
    buffer = io.StringIO(csv_data)
    df = load_csv(buffer)
    assert len(df) == 2
    assert "Order ID" in df.columns
    assert df["Profit"].tolist() == [40, 80]


def test_load_csv_empty_raises_error():
    empty_buffer = io.StringIO("")
    with pytest.raises(ValueError, match="empty"):
        load_csv(empty_buffer)


def test_normalize_dataset_columns_aliases():
    raw_df = pd.DataFrame({
        "order_id": ["TX-101", "TX-102"],
        "date": ["2023-01-15", "2023-01-16"],
        "product": ["Mechanical Keyboard", "USB Cable"],
        "dept": ["Electronics", "Electronics"],
        "qty": [2, 5],
        "price": [50.0, 10.0],
        "cost_price": [30.0, 4.0],
        "sales": [100.0, 50.0],
        "cost": [60.0, 20.0],
        "net_profit": [40.0, 30.0],
    })
    df_norm, mapping = normalize_dataset_columns(raw_df)
    assert "Order ID" in df_norm.columns
    assert "Order Date" in df_norm.columns
    assert "Product Name" in df_norm.columns
    assert "Category" in df_norm.columns
    assert "Quantity" in df_norm.columns
    assert "Unit Price" in df_norm.columns
    assert "Unit Cost" in df_norm.columns
    assert "Revenue" in df_norm.columns
    assert "Cost" in df_norm.columns
    assert "Profit" in df_norm.columns
    assert len(mapping) >= 5


def test_normalize_dataset_auto_derives_revenue_profit():
    raw_df = pd.DataFrame({
        "Quantity": [3, 2],
        "Unit Price": [20.0, 50.0],
        "Unit Cost": [10.0, 25.0]
    })
    df_norm, mapping = normalize_dataset_columns(raw_df)
    assert "Revenue" in df_norm.columns
    assert df_norm["Revenue"].tolist() == [60.0, 100.0]
    assert "Cost" in df_norm.columns
    assert df_norm["Cost"].tolist() == [30.0, 50.0]
    assert "Profit" in df_norm.columns
    assert df_norm["Profit"].tolist() == [30.0, 50.0]


def test_inspect_schema(sample_valid_df):
    schema = inspect_schema(sample_valid_df)
    assert schema["row_count"] == 2000
    assert schema["column_count"] >= 10
    assert "Revenue" in schema["columns"]
    assert "Profit" in schema["columns"]
    assert schema["memory_usage_mb"] > 0


def test_inspect_schema_empty():
    schema = inspect_schema(pd.DataFrame())
    assert schema["row_count"] == 0
    assert schema["columns"] == []


def test_detect_missing_values():
    df = pd.DataFrame({
        "A": [1, None, 3],
        "B": ["x", "y", None],
        "C": [10, 20, 30]
    })
    res = detect_missing_values(df)
    assert res["total_missing_cells"] == 2
    assert res["column_missing"]["A"]["missing_count"] == 1
    assert res["column_missing"]["B"]["missing_count"] == 1
    assert res["column_missing"]["C"]["missing_count"] == 0


def test_detect_duplicates():
    df = pd.DataFrame({
        "Order ID": ["ORD-1", "ORD-2", "ORD-1"],
        "Value": [10, 20, 10]
    })
    res = detect_duplicates(df, subset=["Order ID"])
    assert res["id_duplicates"] == 1


def test_validate_and_parse_dates(sample_valid_df):
    df_aug, summary = validate_and_parse_dates(sample_valid_df, "Order Date")
    assert summary["has_date_column"] is True
    assert summary["invalid_dates_count"] == 0
    assert summary["valid_dates_count"] == 2000
    assert "_parsed_date" in df_aug.columns
    assert summary["date_range_days"] > 300


def test_validate_and_parse_dates_with_invalid_dates():
    df = pd.DataFrame({
        "Order Date": ["2023-01-01", "invalid_date_xyz", "2023-05-10"]
    })
    df_aug, summary = validate_and_parse_dates(df, "Order Date")
    assert summary["invalid_dates_count"] == 1
    assert summary["valid_dates_count"] == 2


def test_validate_dataset_integrity_on_valid_data(sample_valid_df):
    report = validate_dataset_integrity(sample_valid_df)
    assert report["is_valid"] is True
    assert report["reliability_score"] >= 80.0
    assert report["confidence_tier"] in ["HIGH CONFIDENCE", "MEDIUM CONFIDENCE"]
    assert len(report["critical_errors"]) == 0
    assert report["formula_check"]["revenue_mismatch_count"] == 0
    assert report["formula_check"]["cost_mismatch_count"] == 0
    assert report["formula_check"]["profit_mismatch_count"] == 0


def test_validate_dataset_integrity_tampered_formula():
    df = pd.DataFrame({
        "Order ID": ["ORD-1"],
        "Order Date": ["2023-01-01"],
        "Product ID": ["P1"],
        "Product Name": ["Widget"],
        "Category": ["Gadgets"],
        "Quantity": [2],
        "Unit Price": [10.0],
        "Unit Cost": [5.0],
        "Revenue": [999.0],  # 2 * 10 should be 20, not 999
        "Cost": [10.0],
        "Profit": [50.0],   # 999 - 10 should be 989
    })
    report = validate_dataset_integrity(df)
    assert report["is_valid"] is False
    assert report["formula_check"]["revenue_mismatch_count"] == 1
    assert report["formula_check"]["profit_mismatch_count"] == 1
    assert any("Revenue formula mismatch" in err for err in report["critical_errors"])


def test_validate_dataset_integrity_missing_cost_profit_warning():
    # Only revenue and order info; no cost or profit
    df = pd.DataFrame({
        "Order ID": ["ORD-1", "ORD-2"],
        "Order Date": ["2023-01-01", "2023-01-02"],
        "Product Name": ["Item A", "Item B"],
        "Category": ["General", "General"],
        "Revenue": [150.0, 250.0]
    })
    report = validate_dataset_integrity(df)
    assert report["is_valid"] is True
    assert any("Cost/Profit columns missing" in w for w in report["warnings"])


def test_check_numeric_bounds():
    df = pd.DataFrame({
        "Quantity": [-5, 2],
        "Unit Price": [10.0, -1.0],
        "Unit Cost": [5.0, 5.0]
    })
    bounds = check_numeric_bounds(df)
    assert bounds["passed"] is False
    assert bounds["issues_found"] == 2
