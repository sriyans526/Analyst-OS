"""
Agent 3: Analytics Execution Agent for AnalystOS.

Responsibilities:
- Execute analytical tools deterministically on the dataset.
- Calculate revenue, cost, profit, profit margin, order counts, and AOV.
- Perform time-based comparisons (monthly trends, MoM growth).
- Analyze product, category, regional, and customer performance.
- Identify operational and statistical anomalies.
- Return structured metrics, tables, and calculated evidence.
"""

from __future__ import annotations
import pandas as pd
from tools.analytics_tools import (
    calculate_kpis,
    calculate_monthly_trends,
    analyze_category_performance,
    analyze_regional_performance,
    analyze_product_performance,
    analyze_customer_segments,
    detect_anomalies_and_changes,
)
from workflow.types import AnalyticsExecutionResult


class AnalyticsExecutionAgent:
    """
    Core computational agent responsible for executing analytical equations,
    aggregations, and statistical measurements across all dimensions.
    """

    def __init__(self):
        self.name = "Analytics Execution Agent"

    def execute_analytics(self, df: pd.DataFrame) -> AnalyticsExecutionResult:
        """
        Run the complete suite of analytical computations on the provided dataset.
        """
        if df is None or df.empty:
            return AnalyticsExecutionResult(
                kpis=calculate_kpis(pd.DataFrame()),
                monthly_trends=pd.DataFrame(),
                category_performance=pd.DataFrame(),
                regional_performance=pd.DataFrame(),
                product_performance={
                    "all_products": pd.DataFrame(),
                    "top_profit": pd.DataFrame(),
                    "bottom_profit": pd.DataFrame(),
                    "lowest_margin": pd.DataFrame(),
                    "highest_volume": pd.DataFrame()
                },
                customer_segments={
                    "total_customers": 0,
                    "repeat_customers": 0,
                    "repeat_rate_pct": 0.0,
                    "top_customers": pd.DataFrame()
                },
                anomalies=[]
            )

        # 1. Executive KPIs
        kpis = calculate_kpis(df)

        # 2. Monthly Trend Analysis
        monthly_trends = calculate_monthly_trends(df)

        # 3. Category Performance
        category_perf = analyze_category_performance(df)

        # 4. Regional Performance
        regional_perf = analyze_regional_performance(df)

        # 5. Product Level Breakdown
        product_perf = analyze_product_performance(df, top_n=5)

        # 6. Customer Dynamics
        customer_segments = analyze_customer_segments(df)

        # 7. Anomaly & Divergence Identification
        anomalies = detect_anomalies_and_changes(df)

        return AnalyticsExecutionResult(
            kpis=kpis,
            monthly_trends=monthly_trends,
            category_performance=category_perf,
            regional_performance=regional_perf,
            product_performance=product_perf,
            customer_segments=customer_segments,
            anomalies=anomalies
        )
