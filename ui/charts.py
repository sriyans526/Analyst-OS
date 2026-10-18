"""
Plotly visualization builders for AnalystOS.

Provides interactive, publication-grade business intelligence charts.
"""

from __future__ import annotations
from typing import Any, Dict
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_monthly_trend_chart(monthly_df: pd.DataFrame) -> go.Figure:
    """
    Generate dual-axis monthly financial trajectory chart (Revenue, Cost, Profit & Margin).
    """
    if monthly_df is None or monthly_df.empty:
        fig = go.Figure()
        fig.update_layout(title="No Monthly Data Available")
        return fig

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Revenue Bar
    fig.add_trace(
        go.Bar(
            x=monthly_df["Month"],
            y=monthly_df["revenue"],
            name="Revenue ($)",
            marker_color="#3B82F6",
            opacity=0.75,
            hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.2f}<extra></extra>"
        ),
        secondary_y=False
    )

    # Net Profit Line
    fig.add_trace(
        go.Scatter(
            x=monthly_df["Month"],
            y=monthly_df["profit"],
            name="Net Profit ($)",
            line=dict(color="#10B981", width=3),
            mode="lines+markers",
            hovertemplate="<b>%{x}</b><br>Net Profit: $%{y:,.2f}<extra></extra>"
        ),
        secondary_y=False
    )

    # Profit Margin % Line on Secondary Axis
    fig.add_trace(
        go.Scatter(
            x=monthly_df["Month"],
            y=monthly_df["profit_margin_pct"],
            name="Profit Margin (%)",
            line=dict(color="#F59E0B", width=2, dash="dot"),
            mode="lines+markers",
            hovertemplate="<b>%{x}</b><br>Margin: %{y:.1f}%<extra></extra>"
        ),
        secondary_y=True
    )

    fig.update_layout(
        title="<b>Monthly Revenue, Net Profit & Margin Trajectory</b>",
        title_font_size=16,
        barmode="group",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        xaxis=dict(showgrid=True, gridcolor="#F1F5F9", tickangle=-45),
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9", title="Currency ($)"),
        yaxis2=dict(title="Margin (%)", showgrid=False, range=[0, max(50.0, monthly_df["profit_margin_pct"].max() * 1.25)])
    )

    return fig


def create_category_margin_chart(cat_df: pd.DataFrame) -> go.Figure:
    """
    Generate horizontal bar chart comparing Category Profit Margins.
    """
    if cat_df is None or cat_df.empty:
        fig = go.Figure()
        fig.update_layout(title="No Category Data Available")
        return fig

    df_sorted = cat_df.sort_values("profit_margin_pct", ascending=True)

    # Color palette based on margin threshold
    colors = [
        "#EF4444" if m < 15.0 else ("#F59E0B" if m < 30.0 else "#10B981")
        for m in df_sorted["profit_margin_pct"]
    ]

    fig = go.Figure(go.Bar(
        x=df_sorted["profit_margin_pct"],
        y=df_sorted["Category"],
        orientation="h",
        marker_color=colors,
        text=[f"{m:.1f}%" for m in df_sorted["profit_margin_pct"]],
        textposition="auto",
        hovertemplate="<b>%{y}</b><br>Profit Margin: %{x:.2f}%<extra></extra>"
    ))

    fig.update_layout(
        title="<b>Profit Margin by Product Category</b>",
        title_font_size=16,
        xaxis_title="Profit Margin (%)",
        yaxis_title="Category",
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=40, r=40, t=50, b=40),
        xaxis=dict(showgrid=True, gridcolor="#F1F5F9")
    )

    return fig


def create_regional_chart(reg_df: pd.DataFrame) -> go.Figure:
    """
    Generate regional comparison chart showing Revenue and Profit Margin.
    """
    if reg_df is None or reg_df.empty:
        fig = go.Figure()
        fig.update_layout(title="No Regional Data Available")
        return fig

    fig = px.bar(
        reg_df,
        x="Region",
        y="Profit",
        color="profit_margin_pct",
        color_continuous_scale="Viridis",
        title="<b>Regional Profit & Margin Distribution</b>",
        text="profit_margin_pct",
        hover_data={"Revenue": ":$,.2f", "Profit": ":$,.2f", "profit_margin_pct": ":.2f%"}
    )

    fig.update_traces(
        texttemplate="%{text:.1f}% Margin",
        textposition="outside"
    )

    fig.update_layout(
        title_font_size=16,
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=40, r=40, t=50, b=40),
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9", title="Total Profit ($)")
    )

    return fig


def create_product_profit_chart(prod_perf: Dict[str, pd.DataFrame]) -> go.Figure:
    """
    Generate comparison of Top 5 vs Bottom 5 Products by Profit.
    """
    top = prod_perf.get("top_profit", pd.DataFrame())
    bottom = prod_perf.get("bottom_profit", pd.DataFrame())

    if top.empty or bottom.empty:
        fig = go.Figure()
        fig.update_layout(title="No Product Data Available")
        return fig

    top_subset = top.copy()
    top_subset["Segment"] = "Top 5 Contributors"

    bottom_subset = bottom.copy()
    bottom_subset["Segment"] = "Bottom 5 Underperformers"

    combined = pd.concat([top_subset, bottom_subset]).sort_values("Profit", ascending=True)

    fig = px.bar(
        combined,
        x="Profit",
        y="Product Name" if "Product Name" in combined.columns else "Product ID",
        color="Segment",
        orientation="h",
        color_discrete_map={"Top 5 Contributors": "#10B981", "Bottom 5 Underperformers": "#EF4444"},
        title="<b>Product Profitability: Top Drivers vs Laggards</b>",
        hover_data={"profit_margin_pct": ":.1f%", "Revenue": ":$,.2f"}
    )

    fig.update_layout(
        title_font_size=16,
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=40, r=40, t=50, b=40),
        xaxis=dict(showgrid=True, gridcolor="#F1F5F9", title="Total Profit ($)"),
        yaxis=dict(title="")
    )

    return fig
