"""
Automated tests for analytics tools and claim verification.
"""

import pytest
import pandas as pd
from tools.analytics_tools import (
    calculate_kpis,
    calculate_monthly_trends,
    analyze_category_performance,
    analyze_regional_performance,
    analyze_product_performance,
    analyze_customer_segments,
    detect_anomalies_and_changes,
    verify_claim,
)
from data.data_generator import generate_ecommerce_dataset


@pytest.fixture
def sample_df():
    return generate_ecommerce_dataset(num_records=2500, seed=42)


def test_calculate_kpis_empty():
    kpis = calculate_kpis(pd.DataFrame())
    assert kpis["total_revenue"] == 0.0
    assert kpis["profit_margin_pct"] == 0.0
    assert kpis["total_orders"] == 0


def test_calculate_kpis_values(sample_df):
    kpis = calculate_kpis(sample_df)
    assert kpis["total_revenue"] > 0
    assert kpis["total_cost"] > 0
    assert kpis["total_profit"] > 0
    # Strict formula check: Margin = (Profit / Revenue) * 100
    expected_margin = round((kpis["total_profit"] / kpis["total_revenue"]) * 100, 2)
    assert abs(kpis["profit_margin_pct"] - expected_margin) <= 0.01
    assert kpis["total_orders"] > 0
    assert kpis["average_order_value"] > 0


def test_calculate_monthly_trends(sample_df):
    trends = calculate_monthly_trends(sample_df)
    assert not trends.empty
    assert len(trends) == 12  # 12 calendar months
    assert "Month" in trends.columns
    assert "revenue" in trends.columns
    assert "profit" in trends.columns
    assert "mom_revenue_growth_pct" in trends.columns
    assert "mom_profit_growth_pct" in trends.columns


def test_analyze_category_performance(sample_df):
    cat_df = analyze_category_performance(sample_df)
    assert not cat_df.empty
    assert "Category" in cat_df.columns
    assert "Electronics" in cat_df["Category"].values
    assert "Office Supplies" in cat_df["Category"].values
    # Total revenue share should sum to ~100%
    assert abs(cat_df["revenue_share_pct"].sum() - 100.0) <= 0.5


def test_analyze_regional_performance(sample_df):
    reg_df = analyze_regional_performance(sample_df)
    assert not reg_df.empty
    assert len(reg_df) == 4
    for region in ["North", "South", "East", "West"]:
        assert region in reg_df["Region"].values


def test_analyze_product_performance(sample_df):
    prod_results = analyze_product_performance(sample_df, top_n=3)
    assert not prod_results["all_products"].empty
    assert len(prod_results["top_profit"]) == 3
    assert len(prod_results["bottom_profit"]) == 3
    assert len(prod_results["lowest_margin"]) == 3


def test_analyze_customer_segments(sample_df):
    cust_res = analyze_customer_segments(sample_df)
    assert cust_res["total_customers"] > 0
    assert 0 <= cust_res["repeat_rate_pct"] <= 100


def test_detect_anomalies_and_changes(sample_df):
    anomalies = detect_anomalies_and_changes(sample_df)
    assert isinstance(anomalies, list)
    assert len(anomalies) > 0
    # Should catch Electronics margin compression or temporal divergence
    types = [a["type"] for a in anomalies]
    assert any(t in types for t in ["CATEGORY_MARGIN_COMPRESSION", "TEMPORAL_DIVERGENCE", "REGIONAL_UNDERPERFORMANCE"])


def test_verify_claim_kpi_match_pass(sample_df):
    kpis = calculate_kpis(sample_df)
    correct_profit = kpis["total_profit"]
    res = verify_claim(sample_df, "kpi_match", {"metric": "total_profit", "claimed_value": correct_profit})
    assert res["passed"] is True
    assert "Claimed total_profit=" in res["evidence_note"]


def test_verify_claim_kpi_match_fail(sample_df):
    res = verify_claim(sample_df, "kpi_match", {"metric": "total_profit", "claimed_value": 999999999.0})
    assert res["passed"] is False
    assert "REJECTED" in res["evidence_note"]


def test_verify_claim_regional_margin_rank(sample_df):
    # In synthetic dataset South has lower margin
    res = verify_claim(sample_df, "regional_margin_rank", {"region": "South", "rank_type": "lowest"})
    assert res["passed"] is True
