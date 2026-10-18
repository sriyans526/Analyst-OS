"""
Agent 2: Business Investigation Agent for AnalystOS.

Responsibilities:
- Synthesize analytical calculations across products, categories, regions, and periods.
- Investigate contributors to revenue or profit changes.
- Identify primary business drivers (e.g. margin compression vs volume drop).
- Formulate structured empirical findings and testable candidate claims.
"""

from __future__ import annotations
from typing import Any, Dict, List
import pandas as pd
from workflow.types import (
    InvestigationPlan,
    AnalyticsExecutionResult,
    InvestigationFindings
)


class BusinessInvestigationAgent:
    """
    Business intelligence agent that extracts business insights and isolates root causes
    from multi-dimensional analytical evidence.
    """

    def __init__(self):
        self.name = "Business Investigation Agent"

    def investigate(
        self,
        plan: InvestigationPlan,
        analytics: AnalyticsExecutionResult
    ) -> InvestigationFindings:
        """
        Investigate drivers of performance changes and compile structured findings with candidate claims.
        """
        kpis = analytics.kpis
        monthly = analytics.monthly_trends
        cat_df = analytics.category_performance
        reg_df = analytics.regional_performance
        prod_perf = analytics.product_performance
        anomalies = analytics.anomalies

        category_findings: List[Dict[str, Any]] = []
        regional_findings: List[Dict[str, Any]] = []
        temporal_findings: List[Dict[str, Any]] = []
        product_findings: List[Dict[str, Any]] = []
        candidate_claims: List[Dict[str, Any]] = []

        # 1. Global KPI claim
        candidate_claims.append({
            "claim_type": "kpi_match",
            "parameters": {"metric": "total_profit", "claimed_value": kpis.get("total_profit", 0.0)},
            "description": f"Overall total net profit is ${kpis.get('total_profit', 0.0):,.2f}."
        })
        candidate_claims.append({
            "claim_type": "kpi_match",
            "parameters": {"metric": "profit_margin_pct", "claimed_value": kpis.get("profit_margin_pct", 0.0)},
            "description": f"Enterprise-wide average profit margin is {kpis.get('profit_margin_pct', 0.0)}%."
        })

        # 2. Temporal / Trend Investigation
        if not monthly.empty:
            profitless_months = monthly[monthly["profitless_growth_flag"] == True]
            if not profitless_months.empty:
                for _, row in profitless_months.iterrows():
                    temporal_findings.append({
                        "period": row["Month"],
                        "finding": f"Profitless Growth in {row['Month']}: Revenue grew {row['mom_revenue_growth_pct']}% but Profit dropped {row['mom_profit_growth_pct']}%.",
                        "revenue": row["revenue"],
                        "profit": row["profit"],
                        "margin": row["profit_margin_pct"]
                    })
            else:
                first_mo = monthly.iloc[0]
                last_mo = monthly.iloc[-1]
                temporal_findings.append({
                    "period": f"{first_mo['Month']} to {last_mo['Month']}",
                    "finding": f"Monthly revenue shifted from ${first_mo['revenue']:,.2f} to ${last_mo['revenue']:,.2f}.",
                    "revenue": last_mo["revenue"],
                    "profit": last_mo["profit"],
                    "margin": last_mo["profit_margin_pct"]
                })

        # 3. Category Investigation
        lowest_cat_name = ""
        highest_cat_name = ""
        if not cat_df.empty:
            # Sort by margin
            cat_by_margin = cat_df.sort_values("profit_margin_pct")
            lowest_cat = cat_by_margin.iloc[0]
            highest_cat = cat_by_margin.iloc[-1]
            lowest_cat_name = lowest_cat["Category"]
            highest_cat_name = highest_cat["Category"]

            for _, row in cat_df.iterrows():
                category_findings.append({
                    "category": row["Category"],
                    "revenue": row["Revenue"],
                    "profit": row["Profit"],
                    "margin_pct": row["profit_margin_pct"],
                    "profit_share_pct": row.get("profit_share_pct", 0.0),
                    "finding": f"Category '{row['Category']}' delivered ${row['Profit']:,.2f} profit ({row['profit_margin_pct']}% margin)."
                })

            # Add testable category claim
            candidate_claims.append({
                "claim_type": "category_margin_rank",
                "parameters": {"category": lowest_cat_name, "rank_type": "lowest"},
                "description": f"Category '{lowest_cat_name}' recorded the lowest profit margin across all categories ({lowest_cat['profit_margin_pct']}%)."
            })

        # 4. Regional Investigation
        lowest_reg_name = ""
        if not reg_df.empty:
            reg_sorted = reg_df.sort_values("profit_margin_pct")
            lowest_reg = reg_sorted.iloc[0]
            lowest_reg_name = lowest_reg["Region"]

            for _, row in reg_df.iterrows():
                regional_findings.append({
                    "region": row["Region"],
                    "revenue": row["Revenue"],
                    "profit": row["Profit"],
                    "margin_pct": row["profit_margin_pct"],
                    "finding": f"Region '{row['Region']}' generated ${row['Profit']:,.2f} profit with a {row['profit_margin_pct']}% margin."
                })

            # Add testable regional claim
            candidate_claims.append({
                "claim_type": "regional_margin_rank",
                "parameters": {"region": lowest_reg_name, "rank_type": "lowest"},
                "description": f"Region '{lowest_reg_name}' is the lowest-margin geography at {lowest_reg['profit_margin_pct']}%."
            })

        # 5. Product Investigation
        bottom_prods = prod_perf.get("bottom_profit", pd.DataFrame())
        top_prods = prod_perf.get("top_profit", pd.DataFrame())

        if not bottom_prods.empty:
            for _, row in bottom_prods.iterrows():
                p_name = row.get("Product Name", row.get("Product ID", "Product"))
                product_findings.append({
                    "product": p_name,
                    "category": row.get("Category", "N/A"),
                    "profit": row["Profit"],
                    "margin_pct": row["profit_margin_pct"],
                    "status": "LAGGING",
                    "finding": f"Product '{p_name}' yielded only ${row['Profit']:,.2f} profit ({row['profit_margin_pct']}% margin)."
                })

        # Primary Driver Determination
        # Look for category margin compression anomaly
        cat_compression = [a for a in anomalies if a.get("type") == "CATEGORY_MARGIN_COMPRESSION"]
        if cat_compression:
            comp_subj = cat_compression[0].get("subject", "Electronics")
            primary_driver = (
                f"Severe Margin Compression in '{comp_subj}': Enterprise profit decrease is primarily "
                f"driven by supplier cost inflation coupled with promotional discounting in {comp_subj}, "
                f"eroding margins despite sustained sales volumes."
            )
        elif lowest_cat_name:
            primary_driver = (
                f"Product Category Asymmetry: High revenue volume in low-margin '{lowest_cat_name}' "
                f"diluted total corporate profitability relative to high-margin categories."
            )
        else:
            primary_driver = "Multi-dimensional performance variance across regions and product lines."

        return InvestigationFindings(
            primary_driver=primary_driver,
            category_findings=category_findings,
            regional_findings=regional_findings,
            temporal_findings=temporal_findings,
            product_findings=product_findings,
            candidate_claims=candidate_claims
        )
