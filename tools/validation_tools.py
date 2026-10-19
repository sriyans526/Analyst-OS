"""
Validation tools for AnalystOS.

Provides data integrity audits, formula consistency checks, bound validations,
and outlier detection without modifying original data.
"""

from __future__ import annotations
from typing import Any, Dict, List
import numpy as np
import pandas as pd


# Core columns required to perform foundational sales analysis
CORE_SALES_COLUMNS = ["Revenue"]

# Full standard schema for complete margin and profitability diagnosis
STANDARD_COLUMNS = [
    "Order ID",
    "Order Date",
    "Product ID",
    "Product Name",
    "Category",
    "Quantity",
    "Unit Price",
    "Unit Cost",
    "Revenue",
    "Cost",
    "Profit"
]

OPTIONAL_COLUMNS = ["Region", "Customer ID"]


def check_numeric_bounds(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Check for non-positive quantities or negative unit prices and costs.
    """
    issues = []
    
    if "Quantity" in df.columns and pd.api.types.is_numeric_dtype(df["Quantity"]):
        invalid_qty = (df["Quantity"] <= 0) | df["Quantity"].isna()
        count = int(invalid_qty.sum())
        if count > 0:
            issues.append({
                "field": "Quantity",
                "severity": "CRITICAL",
                "count": count,
                "message": f"Found {count} records with non-positive or null Quantity."
            })

    if "Unit Price" in df.columns and pd.api.types.is_numeric_dtype(df["Unit Price"]):
        invalid_price = (df["Unit Price"] < 0) | df["Unit Price"].isna()
        count = int(invalid_price.sum())
        if count > 0:
            issues.append({
                "field": "Unit Price",
                "severity": "CRITICAL",
                "count": count,
                "message": f"Found {count} records with negative or null Unit Price."
            })

    if "Unit Cost" in df.columns and pd.api.types.is_numeric_dtype(df["Unit Cost"]):
        invalid_cost = (df["Unit Cost"] < 0) | df["Unit Cost"].isna()
        count = int(invalid_cost.sum())
        if count > 0:
            issues.append({
                "field": "Unit Cost",
                "severity": "CRITICAL",
                "count": count,
                "message": f"Found {count} records with negative or null Unit Cost."
            })

    return {
        "passed": len(issues) == 0,
        "issues_found": len(issues),
        "details": issues
    }


def detect_outliers(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Detect statistical outliers using the interquartile range (IQR) method and domain thresholds.
    """
    outliers = {}
    numeric_cols = ["Quantity", "Revenue", "Profit", "Unit Price"]

    for col in numeric_cols:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            series = df[col].dropna()
            if len(series) > 10:
                q25 = series.quantile(0.25)
                q75 = series.quantile(0.75)
                iqr = q75 - q25
                lower_bound = q25 - 2.5 * iqr
                upper_bound = q75 + 2.5 * iqr

                flagged = series[(series < lower_bound) | (series > upper_bound)]
                outliers[col] = {
                    "count": int(len(flagged)),
                    "percentage": round(float(len(flagged) / len(series) * 100), 2),
                    "lower_threshold": round(float(lower_bound), 2),
                    "upper_threshold": round(float(upper_bound), 2),
                    "max_observed": round(float(series.max()), 2),
                    "min_observed": round(float(series.min()), 2),
                }

    # Business specific checks: negative profit transactions
    negative_profit_count = 0
    if "Profit" in df.columns and pd.api.types.is_numeric_dtype(df["Profit"]):
        negative_profit_count = int((df["Profit"] < 0).sum())

    return {
        "column_outliers": outliers,
        "negative_profit_orders": negative_profit_count,
        "negative_profit_pct": round(float(negative_profit_count / len(df) * 100), 2) if len(df) > 0 else 0.0
    }


def validate_dataset_integrity(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Comprehensive multi-point validation of dataset integrity.

    Checks:
    1. Mandatory column presence (distinguishing essential sales vs profit dimensions).
    2. Formula consistency:
       - Revenue == Quantity * Unit Price
       - Cost == Quantity * Unit Cost
       - Profit == Revenue - Cost
    3. Numeric boundaries (no negative prices or non-positive quantities).
    4. Outlier statistics.
    5. Overall reliability scoring (0-100%).

    Returns a structured audit report. Does NOT modify the dataset.
    """
    if df is None or df.empty:
        return {
            "is_valid": False,
            "reliability_score": 0.0,
            "confidence_tier": "INVALID",
            "critical_errors": ["The dataset is completely empty or null."],
            "warnings": [],
            "schema_check": {"missing_required_columns": STANDARD_COLUMNS},
            "formula_check": {"revenue_valid": False, "cost_valid": False, "profit_valid": False},
            "bounds_check": {"passed": False},
            "outlier_summary": {}
        }

    critical_errors: List[str] = []
    warnings: List[str] = []
    score = 100.0

    # 1. Essential Sales Check
    has_revenue = "Revenue" in df.columns and pd.api.types.is_numeric_dtype(df["Revenue"])
    has_qty_price = (
        "Quantity" in df.columns and "Unit Price" in df.columns and
        pd.api.types.is_numeric_dtype(df["Quantity"]) and pd.api.types.is_numeric_dtype(df["Unit Price"])
    )

    if not has_revenue and not has_qty_price:
        warnings.append(
            "Financial sales metrics ('Revenue' or 'Quantity' + 'Unit Price') not detected in dataset. "
            "General profiling, distributions, category comparisons, and custom column mappings remain enabled, "
            "but revenue and profit metrics will be unavailable until mapped."
        )
        score -= 15.0

    # Missing standard columns check
    missing_standard = [col for col in STANDARD_COLUMNS if col not in df.columns]
    if missing_standard:
        # Check if cost/profit specifically are missing
        cost_profit_missing = [c for c in ["Cost", "Profit", "Unit Cost"] if c in missing_standard]
        if cost_profit_missing:
            warnings.append(
                f"Cost/Profit columns missing ({cost_profit_missing}). Revenue, order volume, and category sales "
                f"will be analyzed, but net profit and margin analysis will be disabled."
            )
            score -= min(20.0, len(cost_profit_missing) * 6.0)

        other_missing = [c for c in missing_standard if c not in cost_profit_missing]
        if other_missing:
            warnings.append(f"Standard columns missing: {other_missing}. Related sub-analyses will be skipped.")
            score -= min(15.0, len(other_missing) * 3.0)

    missing_optional = [col for col in OPTIONAL_COLUMNS if col not in df.columns]
    if missing_optional:
        warnings.append(f"Optional recommended columns absent: {missing_optional}")
        score -= 3.0

    # 2. Formula checks (when relevant columns exist)
    tolerance = 0.15  # rounding difference tolerance for cents
    formula_results = {
        "revenue_mismatch_count": 0,
        "cost_mismatch_count": 0,
        "profit_mismatch_count": 0
    }

    if all(col in df.columns for col in ["Quantity", "Unit Price", "Revenue"]):
        if pd.api.types.is_numeric_dtype(df["Quantity"]) and pd.api.types.is_numeric_dtype(df["Unit Price"]) and pd.api.types.is_numeric_dtype(df["Revenue"]):
            expected_rev = df["Quantity"] * df["Unit Price"]
            rev_diff = (df["Revenue"] - expected_rev).abs()
            rev_mismatches = int((rev_diff > tolerance).sum())
            formula_results["revenue_mismatch_count"] = rev_mismatches
            if rev_mismatches > 0:
                pct = round(rev_mismatches / len(df) * 100, 2)
                critical_errors.append(
                    f"Revenue formula mismatch: {rev_mismatches} rows ({pct}%) do not equal Quantity * Unit Price."
                )
                score -= min(25.0, pct * 2.0)

    if all(col in df.columns for col in ["Quantity", "Unit Cost", "Cost"]):
        if pd.api.types.is_numeric_dtype(df["Quantity"]) and pd.api.types.is_numeric_dtype(df["Unit Cost"]) and pd.api.types.is_numeric_dtype(df["Cost"]):
            expected_cost = df["Quantity"] * df["Unit Cost"]
            cost_diff = (df["Cost"] - expected_cost).abs()
            cost_mismatches = int((cost_diff > tolerance).sum())
            formula_results["cost_mismatch_count"] = cost_mismatches
            if cost_mismatches > 0:
                pct = round(cost_mismatches / len(df) * 100, 2)
                critical_errors.append(
                    f"Cost formula mismatch: {cost_mismatches} rows ({pct}%) do not equal Quantity * Unit Cost."
                )
                score -= min(20.0, pct * 2.0)

    if all(col in df.columns for col in ["Revenue", "Cost", "Profit"]):
        if pd.api.types.is_numeric_dtype(df["Revenue"]) and pd.api.types.is_numeric_dtype(df["Cost"]) and pd.api.types.is_numeric_dtype(df["Profit"]):
            expected_profit = df["Revenue"] - df["Cost"]
            profit_diff = (df["Profit"] - expected_profit).abs()
            profit_mismatches = int((profit_diff > tolerance).sum())
            formula_results["profit_mismatch_count"] = profit_mismatches
            if profit_mismatches > 0:
                pct = round(profit_mismatches / len(df) * 100, 2)
                critical_errors.append(
                    f"Profit formula mismatch: {profit_mismatches} rows ({pct}%) do not equal Revenue - Cost."
                )
                score -= min(25.0, pct * 2.0)

    # 3. Numeric bounds check
    bounds = check_numeric_bounds(df)
    if not bounds["passed"]:
        for issue in bounds["details"]:
            critical_errors.append(issue["message"])
            score -= 10.0

    # 4. Outliers
    outliers = detect_outliers(df)
    if outliers.get("negative_profit_orders", 0) > 0:
        count = outliers["negative_profit_orders"]
        pct = outliers["negative_profit_pct"]
        warnings.append(
            f"Detected {count} orders ({pct}%) operating at a negative profit (loss-making transactions). "
            f"This is economically valid but signals high business risk."
        )

    # Final Score and Tier
    score = max(0.0, round(score, 1))
    is_valid = len(critical_errors) == 0

    if score >= 80.0 and is_valid:
        tier = "HIGH CONFIDENCE"
    elif score >= 50.0 and is_valid:
        tier = "MEDIUM CONFIDENCE"
    else:
        tier = "POOR / COMPROMISED"

    return {
        "is_valid": is_valid,
        "reliability_score": score,
        "confidence_tier": tier,
        "total_records_inspected": len(df),
        "critical_errors": critical_errors,
        "warnings": warnings,
        "schema_check": {
            "required_present": [col for col in STANDARD_COLUMNS if col in df.columns],
            "missing_required": missing_standard,
            "optional_present": [col for col in OPTIONAL_COLUMNS if col in df.columns],
            "missing_optional": missing_optional
        },
        "formula_check": formula_results,
        "bounds_check": bounds,
        "outlier_summary": outliers
    }
