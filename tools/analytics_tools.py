"""
Analytics tools for AnalystOS.

Provides deterministic mathematical calculations for KPIs, trends, category/regional/product
performance, customer metrics, anomaly identification, and claim verification.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


def calculate_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate executive financial and operational KPIs from the dataset.

    Returns:
    - total_revenue, total_cost, total_profit, profit_margin_pct,
      total_orders, total_units, average_order_value (AOV), average_profit_per_order.
    """
    if df is None or df.empty:
        return {
            "total_revenue": 0.0,
            "total_cost": 0.0,
            "total_profit": 0.0,
            "profit_margin_pct": 0.0,
            "total_orders": 0,
            "total_units": 0,
            "average_order_value": 0.0,
            "average_profit_per_order": 0.0,
        }

    has_revenue = "Revenue" in df.columns and pd.api.types.is_numeric_dtype(df["Revenue"])
    has_cost = "Cost" in df.columns and pd.api.types.is_numeric_dtype(df["Cost"])
    has_profit = "Profit" in df.columns and pd.api.types.is_numeric_dtype(df["Profit"])
    has_quantity = "Quantity" in df.columns and pd.api.types.is_numeric_dtype(df["Quantity"])

    total_revenue = float(df["Revenue"].sum()) if has_revenue else 0.0
    total_cost = float(df["Cost"].sum()) if has_cost else 0.0
    total_profit = float(df["Profit"].sum()) if has_profit else (total_revenue - total_cost if has_revenue and has_cost else 0.0)
    total_orders = int(df["Order ID"].nunique()) if "Order ID" in df.columns else int(len(df))
    total_units = int(df["Quantity"].sum()) if has_quantity else 0

    margin_pct = round((total_profit / total_revenue) * 100, 2) if total_revenue != 0 and has_revenue and (has_profit or has_cost) else 0.0
    aov = round(total_revenue / total_orders, 2) if total_orders > 0 and has_revenue else 0.0
    avg_profit_order = round(total_profit / total_orders, 2) if total_orders > 0 and (has_profit or has_cost) else 0.0

    return {
        "total_revenue": round(total_revenue, 2),
        "total_cost": round(total_cost, 2),
        "total_profit": round(total_profit, 2),
        "profit_margin_pct": margin_pct,
        "total_orders": total_orders,
        "total_units": total_units,
        "average_order_value": aov,
        "average_profit_per_order": avg_profit_order,
        "has_revenue": has_revenue,
        "has_cost": has_cost,
        "has_profit": has_profit or (has_revenue and has_cost),
        "has_quantity": has_quantity,
    }


def calculate_monthly_trends(
    df: pd.DataFrame,
    date_column: str = "Order Date"
) -> pd.DataFrame:
    """
    Calculate month-by-month financial metrics and Month-over-Month (MoM) growth rates.
    """
    if df is None or df.empty or date_column not in df.columns:
        return pd.DataFrame()

    df_work = df.copy()
    parsed_dates = pd.to_datetime(df_work[date_column], errors="coerce")
    df_work["_month"] = parsed_dates.dt.to_period("M").astype(str)

    # Filter out invalid dates
    df_work = df_work[df_work["_month"] != "NaT"]
    if df_work.empty:
        return pd.DataFrame()

    agg_rules = {}
    if "Revenue" in df_work.columns:
        agg_rules["revenue"] = ("Revenue", "sum")
    if "Cost" in df_work.columns:
        agg_rules["cost"] = ("Cost", "sum")
    if "Profit" in df_work.columns:
        agg_rules["profit"] = ("Profit", "sum")
    if "Order ID" in df_work.columns:
        agg_rules["orders"] = ("Order ID", "nunique")
    else:
        agg_rules["orders"] = ("Revenue", "count") if "Revenue" in df_work.columns else ("_month", "count")
    if "Quantity" in df_work.columns:
        agg_rules["units"] = ("Quantity", "sum")
    else:
        agg_rules["units"] = ("Revenue", "count") if "Revenue" in df_work.columns else ("_month", "count")

    monthly = df_work.groupby("_month").agg(**agg_rules).reset_index().rename(columns={"_month": "Month"})
    monthly = monthly.sort_values("Month").reset_index(drop=True)

    if "revenue" not in monthly.columns:
        monthly["revenue"] = 0.0
    if "cost" not in monthly.columns:
        monthly["cost"] = 0.0
    if "profit" not in monthly.columns:
        monthly["profit"] = 0.0

    # Round base aggregates
    monthly["revenue"] = monthly["revenue"].round(2)
    monthly["cost"] = monthly["cost"].round(2)
    monthly["profit"] = monthly["profit"].round(2)

    # Calculate profit margin per month
    monthly["profit_margin_pct"] = np.where(
        monthly["revenue"] != 0,
        (monthly["profit"] / monthly["revenue"] * 100).round(2),
        0.0
    )

    # Calculate MoM growth percentages
    monthly["mom_revenue_growth_pct"] = (
        monthly["revenue"].pct_change() * 100
    ).round(2).fillna(0.0)

    monthly["mom_profit_growth_pct"] = (
        monthly["profit"].pct_change() * 100
    ).round(2).fillna(0.0)

    # Flag "Profitless Growth" months (Revenue up, Profit down)
    monthly["profitless_growth_flag"] = (
        (monthly["mom_revenue_growth_pct"] > 0) & (monthly["mom_profit_growth_pct"] < 0)
    )

    return monthly


def analyze_category_performance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze financial performance, margins, and contribution shares per product category.
    """
    if df is None or df.empty or "Category" not in df.columns:
        return pd.DataFrame()

    total_revenue = df["Revenue"].sum() if "Revenue" in df.columns else 0.0
    total_profit = df["Profit"].sum() if "Profit" in df.columns else 0.0

    agg_rules = {}
    if "Revenue" in df.columns:
        agg_rules["Revenue"] = "sum"
    if "Cost" in df.columns:
        agg_rules["Cost"] = "sum"
    if "Profit" in df.columns:
        agg_rules["Profit"] = "sum"
    if "Order ID" in df.columns:
        agg_rules["Order ID"] = "nunique"
    if "Quantity" in df.columns:
        agg_rules["Quantity"] = "sum"

    if not agg_rules:
        return pd.DataFrame()

    grouped = df.groupby("Category").agg(agg_rules).reset_index()

    if "Revenue" not in grouped.columns:
        grouped["Revenue"] = 0.0
    if "Cost" not in grouped.columns:
        grouped["Cost"] = 0.0
    if "Profit" not in grouped.columns:
        grouped["Profit"] = 0.0

    grouped["Revenue"] = grouped["Revenue"].round(2)
    grouped["Cost"] = grouped["Cost"].round(2)
    grouped["Profit"] = grouped["Profit"].round(2)

    grouped["profit_margin_pct"] = np.where(
        grouped["Revenue"] != 0,
        (grouped["Profit"] / grouped["Revenue"] * 100).round(2),
        0.0
    )

    grouped["revenue_share_pct"] = np.where(
        total_revenue != 0,
        (grouped["Revenue"] / total_revenue * 100).round(2),
        0.0
    )

    grouped["profit_share_pct"] = np.where(
        total_profit != 0,
        (grouped["Profit"] / total_profit * 100).round(2),
        0.0
    )

    return grouped.sort_values("Profit", ascending=False).reset_index(drop=True)


def analyze_regional_performance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze revenue, profit, margins, and average order value across geographical regions.
    """
    if df is None or df.empty or "Region" not in df.columns:
        return pd.DataFrame()

    total_profit = df["Profit"].sum() if "Profit" in df.columns else 0.0

    agg_rules = {}
    if "Revenue" in df.columns:
        agg_rules["Revenue"] = "sum"
    if "Cost" in df.columns:
        agg_rules["Cost"] = "sum"
    if "Profit" in df.columns:
        agg_rules["Profit"] = "sum"
    if "Order ID" in df.columns:
        agg_rules["Order ID"] = "nunique"
    if "Quantity" in df.columns:
        agg_rules["Quantity"] = "sum"

    if not agg_rules:
        return pd.DataFrame()

    grouped = df.groupby("Region").agg(agg_rules).reset_index()

    grouped["Revenue"] = grouped["Revenue"].round(2)
    grouped["Cost"] = grouped["Cost"].round(2)
    grouped["Profit"] = grouped["Profit"].round(2)

    grouped["profit_margin_pct"] = np.where(
        grouped["Revenue"] != 0,
        (grouped["Profit"] / grouped["Revenue"] * 100).round(2),
        0.0
    )

    if "Order ID" in grouped.columns:
        grouped["aov"] = np.where(
            grouped["Order ID"] != 0,
            (grouped["Revenue"] / grouped["Order ID"]).round(2),
            0.0
        )

    grouped["profit_contribution_pct"] = np.where(
        total_profit != 0,
        (grouped["Profit"] / total_profit * 100).round(2),
        0.0
    )

    return grouped.sort_values("Profit", ascending=False).reset_index(drop=True)


def analyze_product_performance(
    df: pd.DataFrame,
    top_n: int = 5
) -> Dict[str, pd.DataFrame]:
    """
    Evaluate product-level profitability, margins, and sales volume.
    Returns:
    - all_products: Full product performance table
    - top_profit: Top N products by total profit
    - bottom_profit: Lowest N products by total profit
    - lowest_margin: Lowest margin products
    - highest_volume: Top N products by units sold
    """
    if df is None or df.empty:
        return {
            "all_products": pd.DataFrame(),
            "top_profit": pd.DataFrame(),
            "bottom_profit": pd.DataFrame(),
            "lowest_margin": pd.DataFrame(),
            "highest_volume": pd.DataFrame(),
        }

    group_keys = [col for col in ["Product ID", "Product Name", "Category"] if col in df.columns]
    if not group_keys:
        return {
            "all_products": pd.DataFrame(),
            "top_profit": pd.DataFrame(),
            "bottom_profit": pd.DataFrame(),
            "lowest_margin": pd.DataFrame(),
            "highest_volume": pd.DataFrame(),
        }

    agg_rules = {}
    if "Revenue" in df.columns:
        agg_rules["Revenue"] = "sum"
    if "Cost" in df.columns:
        agg_rules["Cost"] = "sum"
    if "Profit" in df.columns:
        agg_rules["Profit"] = "sum"
    if "Quantity" in df.columns:
        agg_rules["Quantity"] = "sum"
    if "Unit Price" in df.columns:
        agg_rules["Unit Price"] = "mean"
    if "Unit Cost" in df.columns:
        agg_rules["Unit Cost"] = "mean"

    if not agg_rules:
        return {
            "all_products": pd.DataFrame(),
            "top_profit": pd.DataFrame(),
            "bottom_profit": pd.DataFrame(),
            "lowest_margin": pd.DataFrame(),
            "highest_volume": pd.DataFrame(),
        }

    summary = df.groupby(group_keys).agg(agg_rules).reset_index()

    if "Revenue" not in summary.columns:
        summary["Revenue"] = 0.0
    if "Cost" not in summary.columns:
        summary["Cost"] = 0.0
    if "Profit" not in summary.columns:
        summary["Profit"] = 0.0

    summary["Revenue"] = summary["Revenue"].round(2)
    summary["Cost"] = summary["Cost"].round(2)
    summary["Profit"] = summary["Profit"].round(2)

    if "Unit Price" in summary.columns:
        summary["avg_unit_price"] = summary["Unit Price"].round(2)
        summary = summary.drop(columns=["Unit Price"])
    if "Unit Cost" in summary.columns:
        summary["avg_unit_cost"] = summary["Unit Cost"].round(2)
        summary = summary.drop(columns=["Unit Cost"])

    summary["profit_margin_pct"] = np.where(
        summary["Revenue"] != 0,
        (summary["Profit"] / summary["Revenue"] * 100).round(2),
        0.0
    )

    top_profit = summary.sort_values("Profit", ascending=False).head(top_n).reset_index(drop=True)
    bottom_profit = summary.sort_values("Profit", ascending=True).head(top_n).reset_index(drop=True)
    lowest_margin = summary.sort_values("profit_margin_pct", ascending=True).head(top_n).reset_index(drop=True)
    highest_volume = (
        summary.sort_values("Quantity", ascending=False).head(top_n).reset_index(drop=True)
        if "Quantity" in summary.columns else pd.DataFrame()
    )

    return {
        "all_products": summary,
        "top_profit": top_profit,
        "bottom_profit": bottom_profit,
        "lowest_margin": lowest_margin,
        "highest_volume": highest_volume,
    }


def analyze_customer_segments(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze customer concentration, repeat purchase rate, and top buyers.
    """
    if df is None or df.empty or "Customer ID" not in df.columns:
        return {
            "total_customers": 0,
            "repeat_customers": 0,
            "repeat_rate_pct": 0.0,
            "top_customers": pd.DataFrame()
        }

    cust_summary = df.groupby("Customer ID").agg(
        orders=("Order ID", "nunique") if "Order ID" in df.columns else ("Revenue", "count"),
        total_spent=("Revenue", "sum"),
        total_profit=("Profit", "sum"),
    ).reset_index()

    cust_summary["total_spent"] = cust_summary["total_spent"].round(2)
    cust_summary["total_profit"] = cust_summary["total_profit"].round(2)

    total_cust = len(cust_summary)
    repeat_cust = int((cust_summary["orders"] > 1).sum())
    repeat_rate = round((repeat_cust / total_cust * 100), 2) if total_cust > 0 else 0.0

    top_customers = cust_summary.sort_values("total_spent", ascending=False).head(10).reset_index(drop=True)

    return {
        "total_customers": total_cust,
        "repeat_customers": repeat_cust,
        "repeat_rate_pct": repeat_rate,
        "top_customers": top_customers
    }


def detect_anomalies_and_changes(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Identify key operational, temporal, and category anomalies:
    1. Profitless growth months (Revenue up, Profit down).
    2. Category H1 vs H2 margin collapse.
    3. Low-performing regions.
    4. Severe margin compression products.
    """
    findings = []
    if df is None or df.empty:
        return findings

    # Check monthly dynamics if date column present
    if "Order Date" in df.columns:
        monthly = calculate_monthly_trends(df)
        if not monthly.empty and len(monthly) >= 2:
            # Check profitless growth months
            profitless_months = monthly[monthly["profitless_growth_flag"] == True]
            for _, row in profitless_months.iterrows():
                findings.append({
                    "type": "TEMPORAL_DIVERGENCE",
                    "severity": "HIGH",
                    "subject": f"Month {row['Month']}",
                    "metric": "Revenue vs Profit Divergence",
                    "value": f"MoM Revenue: +{row['mom_revenue_growth_pct']}% vs MoM Profit: {row['mom_profit_growth_pct']}%",
                    "description": (
                        f"In {row['Month']}, sales volume and revenue increased by "
                        f"{row['mom_revenue_growth_pct']}%, but net profit declined by "
                        f"{abs(row['mom_profit_growth_pct'])}%, demonstrating severe margin compression."
                    )
                })

            # Check H1 (Jan-Jun) vs H2 (Jul-Dec) category shift
            df_time = df.copy()
            parsed_dates = pd.to_datetime(df_time["Order Date"], errors="coerce")
            df_time["_half"] = np.where(parsed_dates.dt.month <= 6, "H1", "H2")

            if "Category" in df_time.columns and set(df_time["_half"].unique()) == {"H1", "H2"}:
                cat_h1 = df_time[df_time["_half"] == "H1"].groupby("Category").agg(
                    rev=("Revenue", "sum"), prof=("Profit", "sum")
                ).reset_index()
                cat_h1["h1_margin"] = (cat_h1["prof"] / cat_h1["rev"] * 100).round(2)

                cat_h2 = df_time[df_time["_half"] == "H2"].groupby("Category").agg(
                    rev=("Revenue", "sum"), prof=("Profit", "sum")
                ).reset_index()
                cat_h2["h2_margin"] = (cat_h2["prof"] / cat_h2["rev"] * 100).round(2)

                cat_merged = pd.merge(cat_h1, cat_h2, on="Category", how="inner")
                cat_merged["margin_delta"] = (cat_merged["h2_margin"] - cat_merged["h1_margin"]).round(2)

                for _, row in cat_merged.iterrows():
                    if row["margin_delta"] < -5.0:
                        findings.append({
                            "type": "CATEGORY_MARGIN_COMPRESSION",
                            "severity": "CRITICAL",
                            "subject": row["Category"],
                            "metric": "H1 to H2 Margin Delta",
                            "value": f"{row['margin_delta']} percentage points (from {row['h1_margin']}% in H1 to {row['h2_margin']}% in H2)",
                            "description": (
                                f"Category '{row['Category']}' suffered a severe margin erosion of "
                                f"{abs(row['margin_delta'])}% between the first and second half of the year."
                            )
                        })

    # Check Regional differences
    if "Region" in df.columns:
        regional = analyze_regional_performance(df)
        overall_kpis = calculate_kpis(df)
        overall_margin = overall_kpis["profit_margin_pct"]

        for _, row in regional.iterrows():
            margin_diff = round(row["profit_margin_pct"] - overall_margin, 2)
            if margin_diff < -4.0:
                findings.append({
                    "type": "REGIONAL_UNDERPERFORMANCE",
                    "severity": "MEDIUM",
                    "subject": f"Region {row['Region']}",
                    "metric": "Regional Profit Margin",
                    "value": f"{row['profit_margin_pct']}% (vs {overall_margin}% company avg)",
                    "description": (
                        f"Region '{row['Region']}' is lagging company benchmark by {abs(margin_diff)} "
                        f"percentage points in margin efficiency."
                    )
                })

    # Check individual products with compressed or negative profit
    product_stats = analyze_product_performance(df, top_n=5)
    bottom_prods = product_stats.get("bottom_profit", pd.DataFrame())
    for _, row in bottom_prods.iterrows():
        if row["profit_margin_pct"] < 10.0 or row["Profit"] < 0:
            findings.append({
                "type": "PRODUCT_MARGIN_COLLAPSE",
                "severity": "HIGH",
                "subject": row.get("Product Name", row.get("Product ID", "Product")),
                "metric": "Product Profit Margin",
                "value": f"{row['profit_margin_pct']}% (Total Profit: ${row['Profit']:,.2f})",
                "description": (
                    f"Product '{row.get('Product Name', row.get('Product ID'))}' generated a low margin of "
                    f"{row['profit_margin_pct']}%, contributing minimally to net enterprise profit."
                )
            })

    return findings


def verify_claim(
    df: pd.DataFrame,
    claim_type: str,
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Independently verify an analytical assertion against raw dataset facts.
    Returns:
    - passed: bool
    - expected_value: actual measured value from data
    - claimed_value: claim submitted for review
    - difference: difference between claimed and expected
    - evidence_note: explanatory verification note
    """
    if df is None or df.empty:
        return {
            "passed": False,
            "claim_type": claim_type,
            "error": "Dataset is empty; cannot verify claims."
        }

    tolerance = parameters.get("tolerance", 0.05)

    if claim_type == "kpi_match":
        metric = parameters.get("metric", "total_profit")
        claimed_val = float(parameters.get("claimed_value", 0.0))
        kpis = calculate_kpis(df)
        actual_val = float(kpis.get(metric, 0.0))
        diff = round(abs(claimed_val - actual_val), 2)
        passed = diff <= (abs(actual_val) * tolerance + 0.05)

        return {
            "passed": bool(passed),
            "claim_type": claim_type,
            "metric": metric,
            "claimed_value": claimed_val,
            "actual_value": actual_val,
            "difference": diff,
            "evidence_note": (
                f"Claimed {metric}={claimed_val:,.2f}; actual computed from raw data is {actual_val:,.2f}."
                if passed else
                f"REJECTED: Claimed {metric}={claimed_val:,.2f} does not match computed value {actual_val:,.2f}."
            )
        }

    elif claim_type == "category_margin_rank":
        # E.g. claim that Category X has the lowest or highest margin
        rank_type = parameters.get("rank_type", "lowest")  # 'lowest' or 'highest'
        claimed_category = parameters.get("category", "")
        cat_df = analyze_category_performance(df)
        if cat_df.empty:
            return {"passed": False, "claim_type": claim_type, "error": "No category data"}

        target_row = cat_df.iloc[-1] if rank_type == "lowest" else cat_df.iloc[0]
        actual_category = target_row["Category"]
        passed = (claimed_category.lower() == actual_category.lower())

        return {
            "passed": bool(passed),
            "claim_type": claim_type,
            "claimed_category": claimed_category,
            "actual_category": actual_category,
            "actual_margin": float(target_row["profit_margin_pct"]),
            "evidence_note": (
                f"Verified: {actual_category} is indeed the {rank_type} margin category ({target_row['profit_margin_pct']}%)."
                if passed else
                f"REJECTED: Claimed {claimed_category} is not the {rank_type} margin category. Actual is {actual_category}."
            )
        }

    elif claim_type == "regional_margin_rank":
        rank_type = parameters.get("rank_type", "lowest")
        claimed_region = parameters.get("region", "")
        reg_df = analyze_regional_performance(df)
        if reg_df.empty:
            return {"passed": False, "claim_type": claim_type, "error": "No regional data"}

        # Sort by profit_margin_pct
        reg_df_sorted = reg_df.sort_values("profit_margin_pct")
        target_row = reg_df_sorted.iloc[0] if rank_type == "lowest" else reg_df_sorted.iloc[-1]
        actual_region = target_row["Region"]
        passed = (claimed_region.lower() == actual_region.lower())

        return {
            "passed": bool(passed),
            "claim_type": claim_type,
            "claimed_region": claimed_region,
            "actual_region": actual_region,
            "actual_margin": float(target_row["profit_margin_pct"]),
            "evidence_note": (
                f"Verified: Region {actual_region} is the {rank_type} margin region at {target_row['profit_margin_pct']}%."
                if passed else
                f"REJECTED: Claimed region {claimed_region} is not the {rank_type} margin region. Actual is {actual_region}."
            )
        }

    return {
        "passed": False,
        "claim_type": claim_type,
        "error": f"Unsupported claim verification type: {claim_type}"
    }
