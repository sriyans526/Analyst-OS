"""
AnalystOS — Multi-Agent AI Business Investigation System.

Streamlit Application Entry Point.
"""

from __future__ import annotations
import os
import streamlit as st
import pandas as pd

from tools.data_tools import load_csv
from data.data_generator import generate_ecommerce_dataset
from workflow.orchestrator import MultiAgentOrchestrator
from ui.components import apply_custom_styles
from ui.views import (
    render_overview_view,
    render_data_management_view,
    render_investigation_view,
    render_analytics_dashboard_view,
    render_workflow_inspector_view,
    render_final_report_view,
    render_export_view,
)


def init_session_state():
    """Initialize application session state variables."""
    if "orchestrator" not in st.session_state:
        st.session_state["orchestrator"] = MultiAgentOrchestrator()

    if "dataset" not in st.session_state:
        # Load pre-generated synthetic dataset if available, otherwise generate
        csv_path = os.path.join(os.path.dirname(__file__), "data", "synthetic_sales.csv")
        if os.path.exists(csv_path):
            try:
                st.session_state["dataset"] = load_csv(csv_path)
                st.session_state["dataset_source"] = f"Synthetic Benchmark ({len(st.session_state['dataset']):,} records)"
            except Exception:
                st.session_state["dataset"] = generate_ecommerce_dataset(num_records=3000, seed=42)
                st.session_state["dataset_source"] = "Synthetic E-Commerce (3,000 records)"
        else:
            st.session_state["dataset"] = generate_ecommerce_dataset(num_records=3000, seed=42, output_path=csv_path)
            st.session_state["dataset_source"] = "Synthetic E-Commerce (3,000 records)"

    if "investigation_result" not in st.session_state:
        st.session_state["investigation_result"] = None

    if "question_input" not in st.session_state:
        st.session_state["question_input"] = (
            "Why did our profits decrease, which products or regions contributed most to the decline, "
            "and what actions should we take?"
        )


def main():
    st.set_page_config(
        page_title="AnalystOS — Multi-Agent Business Investigation System",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    apply_custom_styles()
    init_session_state()

    orchestrator: MultiAgentOrchestrator = st.session_state["orchestrator"]
    df: pd.DataFrame = st.session_state.get("dataset", None)
    result = st.session_state.get("investigation_result", None)

    # Sidebar Navigation & Context
    with st.sidebar:
        st.markdown("## 📈 AnalystOS")
        st.markdown("**Multi-Agent Business Investigation**")
        st.caption("College Placement Project • AI Business Intelligence")
        st.markdown("---")

        nav_choice = st.radio(
            "System Navigation:",
            [
                "📊 Overview",
                "📁 Data Management",
                "🔍 Business Investigation",
                "📈 Analytics Dashboard",
                "🤖 Multi-Agent Workflow",
                "📑 Final Investigation Report",
                "💾 Export Center",
            ],
            index=0
        )

        st.markdown("---")
        st.markdown("### 📋 Active Dataset Status")
        if df is not None and not df.empty:
            st.markdown(f"**Source:** `{st.session_state.get('dataset_source', 'Default')}`")
            st.markdown(f"**Rows:** `{len(df):,}` | **Cols:** `{len(df.columns)}`")
            if "Revenue" in df.columns:
                st.markdown(f"**Total GMV:** `${df['Revenue'].sum():,.0f}`")
        else:
            st.markdown("*No active dataset loaded.*")

        st.markdown("---")
        st.markdown("### 📤 Quick CSV Upload")
        sidebar_file = st.file_uploader(
            "Drop your CSV here (Max 50MB):",
            type=["csv"],
            key="sidebar_quick_csv_uploader",
            help="Upload a custom transaction CSV to immediately analyze it across all agents."
        )
        if sidebar_file is not None:
            file_mb = sidebar_file.size / (1024 * 1024)
            if file_mb > 50.0:
                st.sidebar.error("File exceeds 50MB limit.")
            else:
                curr_src = st.session_state.get("dataset_source", "")
                if sidebar_file.name not in curr_src:
                    try:
                        df_up = load_csv(sidebar_file, auto_normalize=True)
                        st.session_state["dataset"] = df_up
                        st.session_state["dataset_source"] = f"Uploaded CSV: {sidebar_file.name}"
                        st.session_state["investigation_result"] = None
                        st.sidebar.success(f"Loaded {sidebar_file.name}!")
                        st.rerun()
                    except Exception as ex:
                        st.sidebar.error(f"Upload failed: {str(ex)}")

        if "Uploaded CSV" in st.session_state.get("dataset_source", ""):
            if st.button("⚙️ Switch to Synthetic Benchmark", use_container_width=True):
                csv_path = os.path.join(os.path.dirname(__file__), "data", "synthetic_sales.csv")
                if os.path.exists(csv_path):
                    st.session_state["dataset"] = load_csv(csv_path, auto_normalize=True)
                else:
                    st.session_state["dataset"] = generate_ecommerce_dataset(num_records=3000, seed=42)
                st.session_state["dataset_source"] = "Synthetic Benchmark (3,000 records)"
                st.session_state["investigation_result"] = None
                st.rerun()

        st.markdown("---")
        st.markdown("### 🤖 Agent Pipeline Status")
        agent_names = [
            "Data Reliability Agent",
            "Planning Agent",
            "Analytics Execution Agent",
            "Business Investigation Agent",
            "Critic / Verification Agent",
            "Decision / Outcome Agent",
        ]

        for name in agent_names:
            rec = result.agent_records.get(name) if result and result.agent_records else None
            status = rec.status.value if rec else "IDLE"
            if status == "COMPLETED":
                icon = "🟢"
            elif status == "RUNNING":
                icon = "🟡"
            elif status == "FAILED":
                icon = "🔴"
            else:
                icon = "⚪"
            st.markdown(f"{icon} <small>**{name}**</small>", unsafe_allow_html=True)

        st.markdown("---")
        with st.expander("🔑 AI Engine & Model Settings", expanded=False):
            from llm.client import LLMClient
            probe_client = LLMClient()
            if probe_client.is_configured:
                st.success(f"🟢 Active Provider: {probe_client.provider.title()} ({probe_client.model})")
            else:
                st.info("🔵 Mode: Offline Analytical Engine (100% Free / Zero API Cost)")

            custom_key = st.text_input(
                "Gemini/OpenAI/Groq API Key (Optional):",
                type="password",
                value=st.session_state.get("custom_llm_api_key", ""),
                help="Enter your API key to activate live cloud LLM reasoning. Leave blank to run offline."
            )
            if custom_key != st.session_state.get("custom_llm_api_key", ""):
                st.session_state["custom_llm_api_key"] = custom_key
                st.rerun()

        st.markdown("---")
        if st.button("🔄 Reset Investigation", use_container_width=True):
            st.session_state["investigation_result"] = None
            st.rerun()

        st.markdown(
            "<div style='font-size: 0.72rem; color: #94A3B8; text-align: center; margin-top: 1rem;'>"
            "Deterministic Multi-Agent Architecture<br>100% Offline • Zero LLM Cost"
            "</div>",
            unsafe_allow_html=True
        )

    # Route navigation view
    if nav_choice == "📊 Overview":
        render_overview_view(df)
    elif nav_choice == "📁 Data Management":
        render_data_management_view()
    elif nav_choice == "🔍 Business Investigation":
        render_investigation_view(orchestrator)
    elif nav_choice == "📈 Analytics Dashboard":
        render_analytics_dashboard_view(df)
    elif nav_choice == "🤖 Multi-Agent Workflow":
        render_workflow_inspector_view(result)
    elif nav_choice == "📑 Final Investigation Report":
        render_final_report_view(result)
    elif nav_choice == "💾 Export Center":
        render_export_view(result, df)


if __name__ == "__main__":
    main()
