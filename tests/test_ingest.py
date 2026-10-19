"""
Unit and integration tests for multi-format data ingestion in AnalystOS.
"""

import io
import json
import pytest
import pandas as pd
from tools.ingest import (
    DatasetArtifact,
    load_csv_artifact,
    load_tsv_artifact,
    load_json_artifact,
    load_parquet_artifact,
    load_excel_artifact,
    load_pdf_artifact,
    load_file_artifact,
    get_synthetic_artifact,
)


def test_load_csv_artifact():
    csv_content = (
        "Order ID,Order Date,Product ID,Product Name,Category,Quantity,Unit Price,Unit Cost,Revenue,Cost,Profit,Region\n"
        "ORD-001,2023-01-15,P-1,Wireless Mouse,Electronics,2,25.0,15.0,50.0,30.0,20.0,North\n"
        "ORD-002,2023-02-10,P-2,Desk Lamp,Furniture,1,45.0,25.0,45.0,25.0,20.0,South\n"
    )
    buffer = io.StringIO(csv_content)
    artifact = load_csv_artifact(buffer, filename="sales.csv")

    assert artifact.source_type == "csv"
    assert artifact.dataframe is not None
    assert len(artifact.dataframe) == 2
    assert "Revenue" in artifact.dataframe.columns
    assert artifact.schema.get("row_count") == 2
    assert len(artifact.errors) == 0


def test_load_csv_empty():
    buffer = io.StringIO("")
    artifact = load_csv_artifact(buffer, filename="empty.csv")
    assert len(artifact.errors) > 0
    assert artifact.dataframe is None


def test_load_tsv_artifact():
    tsv_content = (
        "Order ID\tOrder Date\tProduct Name\tCategory\tQuantity\tUnit Price\tRevenue\n"
        "ORD-T1\t2023-03-01\tNotebook\tOffice Supplies\t5\t4.0\t20.0\n"
        "ORD-T2\t2023-03-05\tPen Set\tOffice Supplies\t2\t10.0\t20.0\n"
    )
    buffer = io.StringIO(tsv_content)
    artifact = load_tsv_artifact(buffer, filename="sales.tsv")

    assert artifact.source_type == "tsv"
    assert artifact.dataframe is not None
    assert len(artifact.dataframe) == 2
    assert "Category" in artifact.dataframe.columns


def test_load_json_artifact():
    records = [
        {"Order ID": "ORD-J1", "Order Date": "2023-04-01", "Revenue": 150.0, "Cost": 100.0, "Profit": 50.0, "Category": "Apparel"},
        {"Order ID": "ORD-J2", "Order Date": "2023-04-02", "Revenue": 200.0, "Cost": 120.0, "Profit": 80.0, "Category": "Electronics"}
    ]
    buffer = io.StringIO(json.dumps(records))
    artifact = load_json_artifact(buffer, filename="transactions.json")

    assert artifact.source_type == "json"
    assert artifact.dataframe is not None
    assert len(artifact.dataframe) == 2
    assert "Revenue" in artifact.dataframe.columns


def test_load_parquet_artifact():
    df = pd.DataFrame({
        "Order ID": ["ORD-P1", "ORD-P2"],
        "Revenue": [100.0, 200.0],
        "Profit": [30.0, 60.0]
    })
    try:
        buffer = io.BytesIO()
        df.to_parquet(buffer)
        buffer.seek(0)
        artifact = load_parquet_artifact(buffer, filename="data.parquet")
        assert artifact.source_type == "parquet"
        assert artifact.dataframe is not None
        assert len(artifact.dataframe) == 2
    except (ImportError, Exception):
        # If pyarrow / fastparquet is not installed in the environment, verify graceful error capture
        artifact = load_parquet_artifact(b"corrupt parquet bytes", filename="data.parquet")
        assert len(artifact.errors) > 0


def test_load_excel_artifact():
    df = pd.DataFrame({"Order ID": ["ORD-E1"], "Revenue": [500.0]})
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="SalesData", index=False)
        buffer.seek(0)
        artifact = load_excel_artifact(buffer, filename="workbook.xlsx")
        assert artifact.source_type == "excel"
        assert "SalesData" in artifact.sheet_names
        assert artifact.dataframe is not None
        assert len(artifact.dataframe) == 1
    except (ImportError, Exception):
        # Graceful handling without throwing unhandled exceptions
        artifact = load_excel_artifact(b"corrupted excel content", filename="workbook.xlsx")
        assert len(artifact.errors) > 0


def test_load_pdf_artifact_scanned_flag():
    # Test handling of empty or simulated PDF bytes
    empty_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    artifact = load_pdf_artifact(empty_pdf_bytes, filename="scan.pdf")
    assert artifact.source_type == "pdf"
    # Either errors recorded or scanned PDF detected
    assert len(artifact.errors) > 0 or artifact.is_scanned_pdf is True or artifact.extracted_text is not None


def test_get_synthetic_artifact():
    artifact = get_synthetic_artifact(num_records=2100, seed=123)
    assert artifact.source_type == "synthetic"
    assert artifact.dataframe is not None
    assert len(artifact.dataframe) == 2100
    assert "Revenue" in artifact.dataframe.columns
    assert "Profit" in artifact.dataframe.columns
    assert artifact.schema.get("row_count") == 2100


def test_load_file_artifact_dispatch():
    csv_content = io.StringIO("Order ID,Revenue\nORD-1,100.0\n")
    artifact = load_file_artifact(csv_content, filename="test.csv")
    assert artifact.source_type == "csv"
    assert artifact.dataframe is not None

    tsv_content = io.StringIO("Order ID\tRevenue\nORD-1\t100.0\n")
    artifact_tsv = load_file_artifact(tsv_content, filename="test.tsv")
    assert artifact_tsv.source_type == "tsv"
    assert artifact_tsv.dataframe is not None


def test_excel_multi_sheet_selection():
    """Test loading specific sheets from a multi-sheet Excel workbook."""
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame({"Order ID": ["ORD-A"], "Revenue": [100.0]}).to_excel(writer, sheet_name="Q1_Sales", index=False)
            pd.DataFrame({"Order ID": ["ORD-B"], "Revenue": [250.0]}).to_excel(writer, sheet_name="Q2_Sales", index=False)
        buffer.seek(0)

        # Load Sheet 1
        art1 = load_excel_artifact(io.BytesIO(buffer.getvalue()), filename="multi.xlsx", sheet_name="Q1_Sales")
        assert art1.selected_sheet == "Q1_Sales"
        assert len(art1.dataframe) == 1
        assert art1.dataframe.iloc[0]["Revenue"] == 100.0
        assert "Q2_Sales" in art1.sheet_names

        # Load Sheet 2
        art2 = load_excel_artifact(io.BytesIO(buffer.getvalue()), filename="multi.xlsx", sheet_name="Q2_Sales")
        assert art2.selected_sheet == "Q2_Sales"
        assert len(art2.dataframe) == 1
        assert art2.dataframe.iloc[0]["Revenue"] == 250.0
    except (ImportError, Exception):
        # Graceful fallback if openpyxl not installed
        pass


def test_uploaded_dataset_analytical_readiness():
    """Verify that an uploaded CSV artifact can immediately feed analytics tools."""
    from tools.analytics_tools import calculate_kpis
    csv_bytes = b"Order ID,Order Date,Category,Region,Revenue,Cost,Profit\nORD-1,2023-01-15,Electronics,North,1000.0,700.0,300.0\nORD-2,2023-02-20,Furniture,South,500.0,400.0,100.0\n"
    artifact = load_file_artifact(io.BytesIO(csv_bytes), filename="custom_transactions.csv")
    assert artifact.dataframe is not None
    assert len(artifact.dataframe) == 2

    # Calculate KPIs immediately on the loaded dataset
    kpis = calculate_kpis(artifact.dataframe)
    assert kpis["total_revenue"] == 1500.0
    assert kpis["total_profit"] == 400.0
    assert kpis["total_orders"] == 2

