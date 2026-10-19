"""
Unit tests for question-driven chart generation in AnalystOS.
"""

import pytest
import pandas as pd
import plotly.graph_objects as go
from tools.chart_generator import suggest_charts_for_question, render_chart_spec
from data.data_generator import generate_ecommerce_dataset


@pytest.fixture
def test_df():
    return generate_ecommerce_dataset(num_records=2000, seed=42)


def test_suggest_charts_trend(test_df):
    question = "What is our monthly revenue and profit trend over time?"
    specs = suggest_charts_for_question(question, test_df)
    types = [s["type"] for s in specs]
    assert "monthly_trend" in types


def test_suggest_charts_category(test_df):
    question = "Which product category had the worst margin?"
    specs = suggest_charts_for_question(question, test_df)
    types = [s["type"] for s in specs]
    assert "category_bar" in types


def test_suggest_charts_regional(test_df):
    question = "Which region is underperforming in sales and profit?"
    specs = suggest_charts_for_question(question, test_df)
    types = [s["type"] for s in specs]
    assert "regional_bar" in types


def test_suggest_charts_profit_decline(test_df):
    question = "Why did our profits decrease in H2?"
    specs = suggest_charts_for_question(question, test_df)
    types = [s["type"] for s in specs]
    assert len(specs) > 0
    assert any(t in ["monthly_trend", "category_bar"] for t in types)


def test_render_chart_spec_monthly_trend(test_df):
    spec = {"type": "monthly_trend", "title": "Monthly Trajectory"}
    fig = render_chart_spec(spec, test_df)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 2


def test_render_chart_spec_category_bar(test_df):
    spec = {"type": "category_bar", "title": "Category Performance"}
    fig = render_chart_spec(spec, test_df)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 1


def test_render_chart_spec_regional_bar(test_df):
    spec = {"type": "regional_bar", "title": "Regional Profit Margin"}
    fig = render_chart_spec(spec, test_df)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 1
