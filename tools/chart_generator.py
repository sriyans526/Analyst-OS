"""
Question-driven chart generation for AnalystOS.

Analyzes natural language business queries, maps them to available DataFrame columns,
and generates relevant Plotly visualizations dynamically.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from tools.analytics_tools import (
    calculate_monthly_trends,
    analyze_category_performance,
    analyze_regional_performance,
    analyze_product_performance,
)


def suggest_charts_for_question(question: str, df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Return a deduplicated list of chart specifications based on question keywords
    and available columns in the active DataFrame.
    """
    if df is None or df.empty:
        return []

    charts = []
    seen_types = set()
    q_lower = (question or "").lower()
    has_date = "Order Date" in df.columns or any("date" in c.lower() for c in df.columns)

    # 1. Time trend questions
    if any(w in q_lower for w in ["trend", "monthly", "over time", "when", "period", "trajectory"]):
        if has_date:
            charts.append({"type": "monthly_trend", "title": "Monthly Revenue and Profit Trend"})
            seen_types.add("monthly_trend")

    # 2. Profit / margin compression questions
    if any(w in q_lower for w in ["profit", "margin", "decline", "fall", "decrease", "drop", "loss"]):
        if "monthly_trend" not in seen_types and has_date:
            charts.append({"type": "monthly_trend", "title": "Revenue vs Profit Trajectory"})
            seen_types.add("monthly_trend")
        if "Category" in df.columns and "category_bar" not in seen_types:
            charts.append({"type": "category_bar", "title": "Category Profit Margin Comparison"})
            seen_types.add("category_bar")

    # 3. Category / product questions
    if any(w in q_lower for w in ["category", "product", "which", "top", "best", "worst", "sku", "item"]):
        if "Category" in df.columns and "category_bar" not in seen_types:
            charts.append({"type": "category_bar", "title": "Category Performance Comparison"})
            seen_types.add("category_bar")
        if ("Product Name" in df.columns or "Product ID" in df.columns) and "product_bar" not in seen_types:
            charts.append({"type": "product_bar", "title": "Top vs Underperforming Products"})
            seen_types.add("product_bar")

    # 4. Regional questions
    if any(w in q_lower for w in ["region", "where", "geographic", "location", "territory", "south", "west", "north", "east"]):
        if "Region" in df.columns and "regional_bar" not in seen_types:
            charts.append({"type": "regional_bar", "title": "Regional Profit Margin"})
            seen_types.add("regional_bar")

    # Fallback: if no specific charts suggested, provide baseline overview charts
    if not charts:
        if has_date and "Revenue" in df.columns:
            charts.append({"type": "monthly_trend", "title": "Monthly Financial Trajectory"})
        elif "Category" in df.columns and "Revenue" in df.columns:
            charts.append({"type": "category_bar", "title": "Category Performance Comparison"})
        else:
            # Generic first numeric column distribution
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            if numeric_cols:
                charts.append({"type": "distribution", "column": numeric_cols[0], "title": f"Distribution of {numeric_cols[0]}"})

    return charts


def render_chart_spec(spec: Dict[str, Any], df: pd.DataFrame) -> go.Figure:
    """
    Build and return a publication-quality Plotly figure from a chart spec.
    """
    chart_type = spec.get("type", "")
    title = spec.get("title", "Analysis Chart")

    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(title="No data available for rendering", template="plotly_white")
        return fig

    if chart_type == "monthly_trend":
        date_col = "Order Date" if "Order Date" in df.columns else next((c for c in df.columns if "date" in c.lower()), None)
        if not date_col:
            fig = go.Figure()
            fig.update_layout(title="No date column found for monthly trend")
            return fig

        monthly_df = calculate_monthly_trends(df, date_column=date_col)
        if monthly_df.empty:
            fig = go.Figure()
            fig.update_layout(title="Insufficient date records for monthly trend")
            return fig

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(
                x=monthly_df["Month"],
                y=monthly_df["revenue"],
                name="Revenue ($)",
                marker_color="#2563EB",
                opacity=0.8,
                hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.2f}<extra></extra>"
            ),
            secondary_y=False
        )
        fig.add_trace(
            go.Scatter(
                x=monthly_df["Month"],
                y=monthly_df["profit"],
                name="Net Profit ($)",
                line=dict(color="#059669", width=3),
                mode="lines+markers",
                hovertemplate="<b>%{x}</b><br>Profit: $%{y:,.2f}<extra></extra>"
            ),
            secondary_y=False
        )
        if "profit_margin_pct" in monthly_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=monthly_df["Month"],
                    y=monthly_df["profit_margin_pct"],
                    name="Profit Margin (%)",
                    line=dict(color="#D97706", width=2, dash="dot"),
                    mode="lines+markers",
                    hovertemplate="<b>%{x}</b><br>Margin: %{y:.1f}%<extra></extra>"
                ),
                secondary_y=True
            )

        fig.update_layout(
            title=dict(text=title, font=dict(size=15, color="#1E293B")),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=60, b=40),
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            xaxis=dict(showgrid=True, gridcolor="#F1F5F9", tickangle=-45),
            yaxis=dict(showgrid=True, gridcolor="#F1F5F9", title="Currency ($)"),
            yaxis2=dict(title="Margin (%)", showgrid=False)
        )
        return fig

    elif chart_type == "category_bar":
        if "Category" not in df.columns:
            fig = go.Figure()
            fig.update_layout(title="Category column missing")
            return fig

        cat_df = analyze_category_performance(df)
        if cat_df.empty:
            fig = go.Figure()
            fig.update_layout(title="No category performance data")
            return fig

        cat_df = cat_df.sort_values("profit_margin_pct", ascending=True)
        colors = [
            "#DC2626" if m < 15.0 else ("#D97706" if m < 30.0 else "#059669")
            for m in cat_df["profit_margin_pct"]
        ]

        fig = go.Figure(go.Bar(
            x=cat_df["profit_margin_pct"],
            y=cat_df["Category"],
            orientation="h",
            marker_color=colors,
            text=[f"{m:.1f}%" for m in cat_df["profit_margin_pct"]],
            textposition="auto",
            hovertemplate="<b>%{y}</b><br>Profit Margin: %{x:.2f}%<extra></extra>"
        ))
        fig.update_layout(
            title=dict(text=title, font=dict(size=15, color="#1E293B")),
            xaxis_title="Profit Margin (%)",
            yaxis_title="Category",
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            margin=dict(l=40, r=40, t=50, b=40),
            xaxis=dict(showgrid=True, gridcolor="#F1F5F9")
        )
        return fig

    elif chart_type == "regional_bar":
        if "Region" not in df.columns:
            fig = go.Figure()
            fig.update_layout(title="Region column missing")
            return fig

        reg_df = analyze_regional_performance(df)
        if reg_df.empty:
            fig = go.Figure()
            fig.update_layout(title="No regional performance data")
            return fig

        fig = px.bar(
            reg_df,
            x="Region",
            y="Profit" if "Profit" in reg_df.columns else "Revenue",
            color="profit_margin_pct" if "profit_margin_pct" in reg_df.columns else None,
            color_continuous_scale="Viridis",
            text="profit_margin_pct" if "profit_margin_pct" in reg_df.columns else None,
            title=title
        )
        if "profit_margin_pct" in reg_df.columns:
            fig.update_traces(texttemplate="%{text:.1f}% Margin", textposition="outside")

        fig.update_layout(
            title_font_size=15,
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            margin=dict(l=40, r=40, t=50, b=40),
            yaxis=dict(showgrid=True, gridcolor="#F1F5F9", title="Profit ($)" if "Profit" in reg_df.columns else "Revenue ($)")
        )
        return fig

    elif chart_type == "product_bar":
        prod_perf = analyze_product_performance(df, top_n=5)
        top = prod_perf.get("top_profit", pd.DataFrame())
        bottom = prod_perf.get("bottom_profit", pd.DataFrame())

        if top.empty or bottom.empty:
            fig = go.Figure()
            fig.update_layout(title="Insufficient product level data")
            return fig

        top_subset = top.copy()
        top_subset["Segment"] = "Top 5 Contributors"
        bottom_subset = bottom.copy()
        bottom_subset["Segment"] = "Bottom 5 Underperformers"
        combined = pd.concat([top_subset, bottom_subset]).sort_values("Profit", ascending=True)

        y_col = "Product Name" if "Product Name" in combined.columns else "Product ID"
        fig = px.bar(
            combined,
            x="Profit",
            y=y_col,
            color="Segment",
            orientation="h",
            color_discrete_map={"Top 5 Contributors": "#059669", "Bottom 5 Underperformers": "#DC2626"},
            title=title
        )
        fig.update_layout(
            title_font_size=15,
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            margin=dict(l=40, r=40, t=50, b=40),
            xaxis=dict(showgrid=True, gridcolor="#F1F5F9", title="Total Net Profit ($)"),
            yaxis=dict(title="")
        )
        return fig

    elif chart_type == "distribution":
        col_name = spec.get("column")
        if col_name and col_name in df.columns:
            fig = px.histogram(df, x=col_name, nbins=30, title=title)
            fig.update_layout(
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                margin=dict(l=40, r=40, t=50, b=40),
                xaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
                yaxis=dict(showgrid=True, gridcolor="#F1F5F9")
            )
            return fig

    # Default fallback
    fig = go.Figure()
    fig.update_layout(title=f"Chart type '{chart_type}' rendered")
    return fig
