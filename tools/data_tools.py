"""
Data tools for AnalystOS.

Provides secure dataset ingestion, schema introspection, column normalization,
duplicate checking, missing value detection, and date validation.
"""

from __future__ import annotations
import io
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd


COLUMN_ALIASES = {
    "Order ID": [
        "order_id", "order id", "orderid", "order_number", "ord_id", "transaction_id", "id", "trans_id"
    ],
    "Order Date": [
        "order_date", "order date", "orderdate", "date", "timestamp", "datetime", "sale_date", "trans_date"
    ],
    "Product ID": [
        "product_id", "product id", "productid", "item_id", "sku", "prod_id"
    ],
    "Product Name": [
        "product_name", "product name", "productname", "product", "item_name", "item", "title", "name", "description"
    ],
    "Category": [
        "category", "product_category", "dept", "department", "type", "category_name"
    ],
    "Customer ID": [
        "customer_id", "customer id", "customerid", "cust_id", "client_id", "user_id"
    ],
    "Region": [
        "region", "territory", "zone", "location", "market", "area", "state", "city", "country"
    ],
    "Quantity": [
        "quantity", "qty", "units", "volume", "count", "items_sold"
    ],
    "Unit Price": [
        "unit_price", "unit price", "unitprice", "price", "selling_price", "sales_price", "retail_price"
    ],
    "Unit Cost": [
        "unit_cost", "unit cost", "unitcost", "cost_price", "base_cost"
    ],
    "Revenue": [
        "revenue", "sales", "total_sales", "total_revenue", "amount", "total_amount", "gmv", "gross_sales"
    ],
    "Cost": [
        "cost", "total_cost", "cogs", "expenses"
    ],
    "Profit": [
        "profit", "net_profit", "earnings", "gross_profit", "margin_amount"
    ]
}


def normalize_dataset_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Intelligently map uploaded DataFrame columns to canonical AnalystOS schema names.
    Also auto-derives missing financial columns when constituent inputs exist.

    Returns:
    - (normalized_df, mapping_report)
    """
    if df is None or df.empty:
        return df, {}

    df_norm = df.copy()
    existing_cols = list(df_norm.columns)
    mapping_applied: Dict[str, str] = {}

    # Build lookup map of cleaned column names
    col_cleaned = {
        re.sub(r"[^a-z0-9]", "", str(c).lower()): c
        for c in existing_cols
    }

    # Match aliases
    for canonical_name, aliases in COLUMN_ALIASES.items():
        if canonical_name in df_norm.columns:
            continue  # Already canonical

        for alias in aliases:
            clean_alias = re.sub(r"[^a-z0-9]", "", alias.lower())
            if clean_alias in col_cleaned:
                orig_col = col_cleaned[clean_alias]
                df_norm.rename(columns={orig_col: canonical_name}, inplace=True)
                mapping_applied[orig_col] = canonical_name
                # Remove matched column from lookup so it isn't matched twice
                del col_cleaned[clean_alias]
                break

    # Auto-derive Revenue if missing but Quantity and Unit Price exist
    if "Revenue" not in df_norm.columns and "Quantity" in df_norm.columns and "Unit Price" in df_norm.columns:
        if pd.api.types.is_numeric_dtype(df_norm["Quantity"]) and pd.api.types.is_numeric_dtype(df_norm["Unit Price"]):
            df_norm["Revenue"] = (df_norm["Quantity"] * df_norm["Unit Price"]).round(2)
            mapping_applied["[Derived]"] = "Revenue = Quantity * Unit Price"

    # Auto-derive Cost if missing but Quantity and Unit Cost exist
    if "Cost" not in df_norm.columns and "Quantity" in df_norm.columns and "Unit Cost" in df_norm.columns:
        if pd.api.types.is_numeric_dtype(df_norm["Quantity"]) and pd.api.types.is_numeric_dtype(df_norm["Unit Cost"]):
            df_norm["Cost"] = (df_norm["Quantity"] * df_norm["Unit Cost"]).round(2)
            mapping_applied["[Derived]"] = "Cost = Quantity * Unit Cost"

    # Auto-derive Profit if missing but Revenue and Cost exist
    if "Profit" not in df_norm.columns and "Revenue" in df_norm.columns and "Cost" in df_norm.columns:
        if pd.api.types.is_numeric_dtype(df_norm["Revenue"]) and pd.api.types.is_numeric_dtype(df_norm["Cost"]):
            df_norm["Profit"] = (df_norm["Revenue"] - df_norm["Cost"]).round(2)
            mapping_applied["[Derived]"] = "Profit = Revenue - Cost"

    # If Product Name is missing but Product ID is present, populate Product Name
    if "Product Name" not in df_norm.columns and "Product ID" in df_norm.columns:
        df_norm["Product Name"] = df_norm["Product ID"].astype(str)

    # If Order ID is missing, generate synthetic sequential identifiers
    if "Order ID" not in df_norm.columns:
        df_norm["Order ID"] = [f"ORD-{10001 + i}" for i in range(len(df_norm))]

    return df_norm, mapping_applied


def load_csv(
    file_or_path: Union[str, io.BytesIO, io.StringIO, Any],
    max_rows: int = 500000,
    auto_normalize: bool = True
) -> pd.DataFrame:
    """
    Safely load a CSV file into a pandas DataFrame with automatic column normalization.

    Parameters:
    - file_or_path: File path or file-like buffer (e.g. from Streamlit file_uploader).
    - max_rows: Maximum number of rows allowed to prevent memory exhaustion attacks.
    - auto_normalize: If True, intelligently map standard column aliases.

    Returns:
    - pd.DataFrame: Clean loaded DataFrame.

    Raises:
    - ValueError: If file cannot be read, exceeds limits, or is empty.
    """
    try:
        if isinstance(file_or_path, str):
            df = pd.read_csv(file_or_path, nrows=max_rows)
        else:
            # File-like object (e.g. UploadedFile)
            df = pd.read_csv(file_or_path, nrows=max_rows)

        if df.empty:
            raise ValueError("The provided CSV file contains no records (empty dataset).")

        # Strip whitespace from column headers
        df.columns = [str(col).strip() for col in df.columns]

        if auto_normalize:
            df, _ = normalize_dataset_columns(df)

        return df

    except pd.errors.EmptyDataError:
        raise ValueError("The provided CSV file is empty (contains no columns or records).")
    except Exception as e:
        if isinstance(e, ValueError):
            raise e
        raise ValueError(f"Failed to load CSV: {str(e)}") from e


def inspect_schema(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Inspect the schema, dimensions, data types, and memory usage of a DataFrame.

    Returns a structured dictionary summary.
    """
    if df is None or df.empty:
        return {
            "row_count": 0,
            "column_count": 0,
            "columns": [],
            "dtypes": {},
            "memory_usage_mb": 0.0,
            "preview": []
        }

    dtypes_dict = {col: str(dtype) for col, dtype in df.dtypes.items()}
    memory_mb = round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)

    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": list(df.columns),
        "dtypes": dtypes_dict,
        "memory_usage_mb": float(memory_mb),
        "preview": df.head(10).to_dict(orient="records")
    }


def detect_missing_values(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Identify missing (null/NaN) values across all columns.

    Returns:
    - Dict with per-column counts, percentages, and total missing cells.
    """
    if df is None or df.empty:
        return {
            "total_missing_cells": 0,
            "total_cells": 0,
            "overall_missing_pct": 0.0,
            "column_missing": {}
        }

    total_cells = df.size
    missing_series = df.isna().sum()
    total_missing = int(missing_series.sum())

    col_missing = {}
    for col, count in missing_series.items():
        pct = round((count / len(df)) * 100, 2) if len(df) > 0 else 0.0
        col_missing[col] = {
            "missing_count": int(count),
            "missing_pct": float(pct)
        }

    overall_pct = round((total_missing / total_cells) * 100, 2) if total_cells > 0 else 0.0

    return {
        "total_missing_cells": total_missing,
        "total_cells": int(total_cells),
        "overall_missing_pct": float(overall_pct),
        "column_missing": col_missing
    }


def detect_duplicates(
    df: pd.DataFrame,
    subset: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Detect exact row duplicates or duplicates across a primary key column subset.

    Returns:
    - Dict with duplicate counts and affected row samples.
    """
    if df is None or df.empty:
        return {
            "total_duplicate_rows": 0,
            "duplicate_pct": 0.0,
            "id_duplicates": 0,
            "subset_checked": subset or "ALL"
        }

    total_dupes = int(df.duplicated().sum())
    pct = round((total_dupes / len(df)) * 100, 2)

    id_dupes = 0
    if subset and all(col in df.columns for col in subset):
        id_dupes = int(df.duplicated(subset=subset).sum())
    elif "Order ID" in df.columns:
        id_dupes = int(df.duplicated(subset=["Order ID"]).sum())

    return {
        "total_duplicate_rows": total_dupes,
        "duplicate_pct": float(pct),
        "id_duplicates": id_dupes,
        "subset_checked": subset or (["Order ID"] if "Order ID" in df.columns else "ALL")
    }


def validate_and_parse_dates(
    df: pd.DataFrame,
    date_column: str = "Order Date"
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Parse date column safely into datetime without altering unparseable values silently.

    Returns:
    - (augmented_df, summary_dict)
    """
    if df is None or df.empty:
        return df, {
            "has_date_column": False,
            "invalid_dates_count": 0,
            "min_date": None,
            "max_date": None,
            "date_range_days": 0
        }

    if date_column not in df.columns:
        return df, {
            "has_date_column": False,
            "column_name": date_column,
            "error": f"Date column '{date_column}' not found in dataset."
        }

    df_copy = df.copy()
    parsed_dates = pd.to_datetime(df_copy[date_column], errors="coerce")
    invalid_count = int(parsed_dates.isna().sum() - df_copy[date_column].isna().sum())
    valid_dates = parsed_dates.dropna()

    min_date = valid_dates.min().strftime("%Y-%m-%d") if not valid_dates.empty else None
    max_date = valid_dates.max().strftime("%Y-%m-%d") if not valid_dates.empty else None
    date_range_days = (valid_dates.max() - valid_dates.min()).days if not valid_dates.empty else 0

    df_copy["_parsed_date"] = parsed_dates
    df_copy["_year_month"] = parsed_dates.dt.to_period("M").astype(str)

    return df_copy, {
        "has_date_column": True,
        "column_name": date_column,
        "valid_dates_count": int(len(valid_dates)),
        "invalid_dates_count": int(invalid_count),
        "min_date": min_date,
        "max_date": max_date,
        "date_range_days": int(date_range_days)
    }
