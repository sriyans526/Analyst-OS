"""
Data tools for AnalystOS.

Provides secure dataset ingestion, schema introspection, column normalization,
duplicate checking, missing value detection, and date validation.
"""

from __future__ import annotations
import io
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd


COLUMN_ALIASES = {
    "Order ID": [
        "order_id", "order id", "orderid", "order_number", "ord_id", "transaction_id", "trans_id",
        "id", "bill_id", "invoice_id", "bill_number", "bill_no", "invoice_no", "receipt_id", "receipt_no"
    ],
    "Order Date": [
        "order_date", "order date", "orderdate", "date", "timestamp", "datetime", "sale_date", "trans_date",
        "transaction_date", "bill_date", "time", "created_at", "trans_time", "sale_time"
    ],
    "Product ID": [
        "product_id", "product id", "productid", "item_id", "sku", "prod_id", "menu_id", "item_code", "product_code"
    ],
    "Product Name": [
        "product_name", "product name", "productname", "product", "item_name", "item", "title", "name",
        "description", "menu_item", "dish", "sku_name", "item_description", "product_description"
    ],
    "Category": [
        "category", "product_category", "dept", "department", "type", "category_name", "item_category",
        "menu_category", "group", "class", "product_type", "item_type"
    ],
    "Customer ID": [
        "customer_id", "customer id", "customerid", "cust_id", "client_id", "user_id", "customer",
        "client", "buyer", "customer_name", "member_id"
    ],
    "Region": [
        "region", "territory", "zone", "location", "market", "area", "state", "city", "country",
        "store", "store_location", "branch", "outlet", "outlet_location"
    ],
    "Quantity": [
        "quantity", "qty", "units", "volume", "count", "items_sold", "units_sold", "quantity_sold",
        "items", "num_items", "item_qty", "order_quantity"
    ],
    "Unit Price": [
        "unit_price", "unit price", "unitprice", "price", "selling_price", "sales_price", "retail_price",
        "rate", "price_per_unit", "item_price", "menu_price", "unit_rate"
    ],
    "Unit Cost": [
        "unit_cost", "unit cost", "unitcost", "cost_price", "base_cost", "cost_per_unit", "cost_rate"
    ],
    "Revenue": [
        "revenue", "sales", "total_sales", "total_revenue", "amount", "total_amount", "gmv", "gross_sales",
        "total", "total_spent", "spent", "bill_amount", "subtotal", "grand_total", "price_total",
        "turnover", "net_sales", "transaction_amount", "line_total", "amount_spent"
    ],
    "Cost": [
        "cost", "total_cost", "cogs", "expenses", "expense", "total_expense"
    ],
    "Profit": [
        "profit", "net_profit", "earnings", "gross_profit", "margin_amount", "net_margin"
    ],
    "Payment Method": [
        "payment_method", "payment_mode", "payment_type", "payment", "tender", "pay_mode", "card_type"
    ]
}


def _coerce_numeric_series(series: pd.Series) -> pd.Series:
    """Safely convert currency/formatted string numbers into float series."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    cleaned = series.astype(str).str.replace(r"[\$,\s€£₹]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")


def normalize_dataset_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Intelligently map uploaded DataFrame columns to canonical AnalystOS schema names.
    Safely handles arbitrary schema structures and auto-derives missing financial columns
    when constituent inputs exist.

    Returns:
    - (normalized_df, mapping_report)
    """
    if df is None or df.empty:
        return df, {}

    df_norm = df.copy()
    existing_cols = list(df_norm.columns)
    mapping_applied: Dict[str, str] = {}

    # Build lookup map of cleaned column names (strip non-alphanumeric, lower)
    col_cleaned = {
        re.sub(r"[^a-z0-9]", "", str(c).lower()): c
        for c in existing_cols
    }

    # Match aliases to canonical names
    for canonical_name, aliases in COLUMN_ALIASES.items():
        if canonical_name in df_norm.columns:
            continue  # Already canonical

        for alias in aliases:
            clean_alias = re.sub(r"[^a-z0-9]", "", alias.lower())
            if clean_alias in col_cleaned:
                orig_col = col_cleaned[clean_alias]
                df_norm.rename(columns={orig_col: canonical_name}, inplace=True)
                mapping_applied[orig_col] = canonical_name
                del col_cleaned[clean_alias]
                break

    # Coerce numeric fields if present as strings
    for num_col in ["Revenue", "Cost", "Profit", "Quantity", "Unit Price", "Unit Cost"]:
        if num_col in df_norm.columns and not pd.api.types.is_numeric_dtype(df_norm[num_col]):
            coerced = _coerce_numeric_series(df_norm[num_col])
            if coerced.notna().sum() > 0:
                df_norm[num_col] = coerced

    # Auto-derive Revenue if missing but Quantity and Unit Price exist
    if "Revenue" not in df_norm.columns and "Quantity" in df_norm.columns and "Unit Price" in df_norm.columns:
        qty_num = _coerce_numeric_series(df_norm["Quantity"])
        price_num = _coerce_numeric_series(df_norm["Unit Price"])
        if qty_num.notna().sum() > 0 and price_num.notna().sum() > 0:
            df_norm["Quantity"] = qty_num
            df_norm["Unit Price"] = price_num
            df_norm["Revenue"] = (qty_num * price_num).round(2)
            mapping_applied["[Derived]"] = "Revenue = Quantity * Unit Price"

    # Auto-derive Cost if missing but Quantity and Unit Cost exist
    if "Cost" not in df_norm.columns and "Quantity" in df_norm.columns and "Unit Cost" in df_norm.columns:
        qty_num = _coerce_numeric_series(df_norm["Quantity"])
        cost_num = _coerce_numeric_series(df_norm["Unit Cost"])
        if qty_num.notna().sum() > 0 and cost_num.notna().sum() > 0:
            df_norm["Quantity"] = qty_num
            df_norm["Unit Cost"] = cost_num
            df_norm["Cost"] = (qty_num * cost_num).round(2)
            mapping_applied["[Derived]"] = "Cost = Quantity * Unit Cost"

    # Auto-derive Profit if missing but Revenue and Cost exist
    if "Profit" not in df_norm.columns and "Revenue" in df_norm.columns and "Cost" in df_norm.columns:
        rev_num = _coerce_numeric_series(df_norm["Revenue"])
        cost_num = _coerce_numeric_series(df_norm["Cost"])
        if rev_num.notna().sum() > 0 and cost_num.notna().sum() > 0:
            df_norm["Revenue"] = rev_num
            df_norm["Cost"] = cost_num
            df_norm["Profit"] = (rev_num - cost_num).round(2)
            mapping_applied["[Derived]"] = "Profit = Revenue - Cost"

    # If Product Name is missing but Product ID is present, populate Product Name
    if "Product Name" not in df_norm.columns and "Product ID" in df_norm.columns:
        df_norm["Product Name"] = df_norm["Product ID"].astype(str)

    return df_norm, mapping_applied


def detect_dataset_columns(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Inspect columns of an uploaded DataFrame, categorizing each by data type
    and inferring potential analytical roles (Revenue, Quantity, Date, Category, etc.).
    """
    if df is None or df.empty:
        return {"columns": {}, "inferred_roles": {}}

    detected = {}
    inferred_roles = {}

    for col in df.columns:
        series = df[col]
        dtype_str = str(series.dtype)
        is_num = pd.api.types.is_numeric_dtype(series)
        is_date = pd.api.types.is_datetime64_any_dtype(series)
        unique_cnt = int(series.nunique())
        null_cnt = int(series.isna().sum())

        # Check if text column can be parsed as dates
        if not is_num and not is_date and unique_cnt > 0:
            sample_non_null = series.dropna().head(10).astype(str)
            date_matches = 0
            for val in sample_non_null:
                val_clean = val.strip()
                if re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", val_clean) or re.match(r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", val_clean):
                    date_matches += 1
            if date_matches >= max(1, len(sample_non_null) * 0.7):
                is_date = True

        # Inferred broad data type
        if is_date:
            col_type = "Date / Time"
        elif is_num:
            col_type = "Numeric"
        elif unique_cnt <= 60 or unique_cnt <= max(5, len(df) * 0.05):
            col_type = "Categorical"
        elif unique_cnt >= len(df) * 0.85:
            col_type = "Identifier"
        else:
            col_type = "Text"

        # Determine matched role if any
        matched_role = None
        cleaned_name = re.sub(r"[^a-z0-9]", "", str(col).lower())
        for canonical, aliases in COLUMN_ALIASES.items():
            if col == canonical:
                matched_role = canonical
                break
            for a in aliases:
                if cleaned_name == re.sub(r"[^a-z0-9]", "", a.lower()):
                    matched_role = canonical
                    break
            if matched_role:
                break

        if not matched_role:
            if is_date:
                matched_role = "Order Date (Suggested)"
            elif is_num and any(w in cleaned_name for w in ["rev", "sale", "amt", "price", "val", "spend", "cost", "total", "fee", "bill"]):
                matched_role = "Financial Metric (Suggested)"

        samples = [str(v) for v in series.dropna().head(3).tolist()]

        detected[col] = {
            "type": col_type,
            "dtype": dtype_str,
            "unique_count": unique_cnt,
            "null_count": null_cnt,
            "samples": samples,
            "inferred_role": matched_role or "General Field"
        }
        if matched_role:
            inferred_roles[matched_role] = col

    return {
        "columns": detected,
        "inferred_roles": inferred_roles
    }


def apply_user_column_mapping(
    df: pd.DataFrame,
    mapping: Dict[str, str]
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Apply user-specified column mappings to canonical AnalystOS metrics.

    Parameters:
    - df: The active DataFrame.
    - mapping: Dictionary of {canonical_role: original_column_name}.

    Returns:
    - (updated_df, changes_applied)
    """
    if df is None or df.empty or not mapping:
        return df, {}

    updated_df = df.copy()
    changes = {}

    for canonical_name, orig_col in mapping.items():
        if orig_col and orig_col in updated_df.columns and orig_col != canonical_name:
            if canonical_name in updated_df.columns:
                updated_df.drop(columns=[canonical_name], inplace=True)
            updated_df.rename(columns={orig_col: canonical_name}, inplace=True)
            changes[orig_col] = canonical_name

    # Coerce mapped numeric fields
    for col in ["Revenue", "Quantity", "Unit Price", "Cost", "Profit", "Unit Cost"]:
        if col in updated_df.columns:
            updated_df[col] = _coerce_numeric_series(updated_df[col])

    # Auto-derive Revenue if Quantity and Unit Price are mapped but Revenue is not
    if "Revenue" not in updated_df.columns and "Quantity" in updated_df.columns and "Unit Price" in updated_df.columns:
        qty_num = _coerce_numeric_series(updated_df["Quantity"])
        price_num = _coerce_numeric_series(updated_df["Unit Price"])
        if qty_num.notna().sum() > 0 and price_num.notna().sum() > 0:
            updated_df["Revenue"] = (qty_num * price_num).round(2)
            changes["[Derived]"] = "Revenue = Quantity * Unit Price"

    # Auto-derive Profit if Revenue and Cost are present but Profit is not
    if "Profit" not in updated_df.columns and "Revenue" in updated_df.columns and "Cost" in updated_df.columns:
        rev_num = _coerce_numeric_series(updated_df["Revenue"])
        cost_num = _coerce_numeric_series(updated_df["Cost"])
        if rev_num.notna().sum() > 0 and cost_num.notna().sum() > 0:
            updated_df["Profit"] = (rev_num - cost_num).round(2)
            changes["[Derived]"] = "Profit = Revenue - Cost"

    return updated_df, changes


def read_csv_with_encoding_fallbacks(
    file_or_buffer: Any,
    max_rows: Optional[int] = None,
    default_sep: Optional[str] = None
) -> Tuple[pd.DataFrame, str]:
    """
    Robustly read a CSV or delimited text file/buffer using multi-encoding fallback
    and delimiter autodetection.

    Encoding hierarchy:
    1. utf-8
    2. utf-8-sig (handles UTF-8 with BOM without corrupting column headers)
    3. cp1252 (Windows-1252 Western - standard for Windows Excel CSV exports, handles byte 0xa0)
    4. Auto-detected encoding via charset_normalizer (if installed and detected)
    5. latin-1 / iso-8859-1 (as fallback to preserve byte fidelity without replacing)

    Parameters:
    - file_or_buffer: Filepath, bytes, io.BytesIO, io.StringIO, or Streamlit UploadedFile.
    - max_rows: Maximum rows to read.
    - default_sep: Predefined separator (e.g. '\t' for TSV). If None, auto-detects commas,
      semicolons, tabs, and pipes.

    Returns:
    - (DataFrame, successful_encoding_name)

    Raises:
    - ValueError: If the file is empty, corrupted, or unreadable across all encodings.
    """
    if isinstance(file_or_buffer, io.StringIO):
        content = file_or_buffer.getvalue()
        if not content.strip():
            raise ValueError("The provided CSV file contains no records (empty dataset).")
        read_kwargs = {"nrows": max_rows}
        if default_sep is not None:
            read_kwargs["sep"] = default_sep
        df = pd.read_csv(io.StringIO(content), **read_kwargs)
        if default_sep is None and len(df.columns) == 1:
            first_col = str(df.columns[0])
            if ";" in first_col or "\t" in first_col or "|" in first_col:
                df = pd.read_csv(io.StringIO(content), sep=None, engine="python", nrows=max_rows)
        return df, "utf-8"

    # Extract raw bytes safely from any buffer or path
    raw_bytes: bytes = b""
    if isinstance(file_or_buffer, bytes):
        raw_bytes = file_or_buffer
    elif isinstance(file_or_buffer, str):
        if os.path.exists(file_or_buffer):
            with open(file_or_buffer, "rb") as f:
                raw_bytes = f.read()
        else:
            raw_bytes = file_or_buffer.encode("utf-8", errors="replace")
    elif hasattr(file_or_buffer, "getvalue"):
        val = file_or_buffer.getvalue()
        raw_bytes = val.encode("utf-8", errors="replace") if isinstance(val, str) else val
    elif hasattr(file_or_buffer, "read"):
        if hasattr(file_or_buffer, "seek"):
            file_or_buffer.seek(0)
        read_val = file_or_buffer.read()
        raw_bytes = read_val.encode("utf-8", errors="replace") if isinstance(read_val, str) else read_val
        if hasattr(file_or_buffer, "seek"):
            file_or_buffer.seek(0)
    else:
        raise ValueError("Unsupported input format for CSV ingestion.")

    if not raw_bytes or not raw_bytes.strip():
        raise ValueError("The provided CSV file contains no records (empty dataset).")

    # Strict encoding priority order
    candidate_encodings = ["utf-8", "utf-8-sig", "cp1252"]

    # Auto-detect via charset_normalizer if available
    try:
        import charset_normalizer
        sample = raw_bytes[:131072]
        match = charset_normalizer.from_bytes(sample).best()
        if match and match.encoding:
            det = match.encoding.lower()
            if det not in [e.lower() for e in candidate_encodings]:
                candidate_encodings.append(det)
    except Exception:
        pass

    # Latin-1 as final fallback to preserve byte fidelity
    if "latin-1" not in [e.lower() for e in candidate_encodings]:
        candidate_encodings.append("latin-1")
    if "iso-8859-1" not in [e.lower() for e in candidate_encodings]:
        candidate_encodings.append("iso-8859-1")

    last_error = None
    for enc in candidate_encodings:
        try:
            buf = io.BytesIO(raw_bytes)
            read_kwargs = {"encoding": enc, "nrows": max_rows}
            if default_sep is not None:
                read_kwargs["sep"] = default_sep
            df = pd.read_csv(buf, **read_kwargs)

            # Autodetect non-comma delimiter if single fused column detected
            if default_sep is None and len(df.columns) == 1:
                first_col = str(df.columns[0])
                if ";" in first_col or "\t" in first_col or "|" in first_col:
                    buf.seek(0)
                    df = pd.read_csv(buf, encoding=enc, sep=None, engine="python", nrows=max_rows)

            if df.empty:
                raise ValueError("The provided CSV file contains no records (empty dataset).")

            return df, enc
        except (UnicodeDecodeError, UnicodeError) as ue:
            last_error = ue
            continue
        except pd.errors.EmptyDataError:
            raise ValueError("The provided CSV file is empty (contains no columns or records).")
        except Exception as ex:
            if default_sep is None:
                try:
                    buf = io.BytesIO(raw_bytes)
                    df = pd.read_csv(buf, encoding=enc, sep=None, engine="python", nrows=max_rows)
                    if not df.empty:
                        return df, enc
                except Exception:
                    pass
            last_error = ex
            continue

    raise ValueError(
        f"Unable to read CSV across supported encodings ({', '.join(candidate_encodings[:3])}, latin-1). "
        f"Please verify the file is a text CSV. Error: {str(last_error)}"
    )


def load_csv(
    file_or_path: Union[str, io.BytesIO, io.StringIO, Any],
    max_rows: int = 500000,
    auto_normalize: bool = True
) -> pd.DataFrame:
    """
    Safely load a CSV file into a pandas DataFrame with automatic column normalization
    and multi-encoding fallback.

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
        df, _ = read_csv_with_encoding_fallbacks(file_or_path, max_rows=max_rows)

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
