"""
AnalystOS — Multi-Agent AI Business Investigation System.

Streamlit Application Entry Point.
"""

from __future__ import annotations
import os
import uuid
import streamlit as st
import pandas as pd

from tools.ingest import (
    DatasetArtifact,
    get_synthetic_artifact,
    load_file_artifact,
)
from workflow.orchestrator import MultiAgentOrchestrator
from ui.components import apply_custom_styles
from ui.views import (
    render_home_view,
    render_data_workspace_view,
    render_ai_investigator_view,
    render_analytics_dashboard_view,
    render_reports_view,
    render_investigation_history_view,
    render_about_view,
    KEY_ACTIVE_ARTIFACT,
    KEY_CHAT_HISTORY,
    KEY_INVESTIGATION_RESULT,
    KEY_INVESTIGATION_HISTORY,
    KEY_CURRENT_INV_ID,
    KEY_CHART_SPECS,
    KEY_REPORT_BYTES,
    KEY_LLM_API_KEY,
    KEY_NAV_SELECTION,
)


def reset_investigation():
    """Clear only investigation state, preserve dataset and config."""
    keys_to_clear = [
        KEY_CHAT_HISTORY,
        KEY_INVESTIGATION_RESULT,
        KEY_CURRENT_INV_ID,
        KEY_CHART_SPECS,
        KEY_REPORT_BYTES,
    ]
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]
    st.session_state[KEY_CURRENT_INV_ID] = str(uuid.uuid4())


def init_session_state():
    """Initialize application session state variables."""
    if "orchestrator" not in st.session_state:
        st.session_state["orchestrator"] = MultiAgentOrchestrator()

    if KEY_CURRENT_INV_ID not in st.session_state:
        st.session_state[KEY_CURRENT_INV_ID] = str(uuid.uuid4())

    if KEY_CHAT_HISTORY not in st.session_state:
        st.session_state[KEY_CHAT_HISTORY] = []

    if KEY_INVESTIGATION_HISTORY not in st.session_state:
        st.session_state[KEY_INVESTIGATION_HISTORY] = []

    if KEY_INVESTIGATION_RESULT not in st.session_state:
        st.session_state[KEY_INVESTIGATION_RESULT] = None

    if KEY_NAV_SELECTION not in st.session_state:
        st.session_state[KEY_NAV_SELECTION] = "Home"

    if KEY_ACTIVE_ARTIFACT not in st.session_state:
        st.session_state[KEY_ACTIVE_ARTIFACT] = None
        st.session_state["dataset"] = None
        st.session_state["dataset_source"] = "No active dataset"


def main():
    st.set_page_config(
        page_title="AnalystOS — Business Investigation System",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    apply_custom_styles()
    init_session_state()

    orchestrator: MultiAgentOrchestrator = st.session_state["orchestrator"]
    artifact: DatasetArtifact = st.session_state.get(KEY_ACTIVE_ARTIFACT, None)
    df: Optional[pd.DataFrame] = artifact.dataframe if artifact else None
    result = st.session_state.get(KEY_INVESTIGATION_RESULT, None)

    nav_options = [
        "Home",
        "Data Workspace",
        "AI Investigator",
        "Analytics Dashboard",
        "Reports",
        "Investigation History",
        "About & Architecture",
    ]

    # Sidebar Navigation & Settings
    with st.sidebar:
        st.markdown("## AnalystOS")
        st.markdown("**Enterprise Business Intelligence**")
        st.caption("Autonomous Multi-Agent Analytical System")
        st.markdown("---")

        if KEY_NAV_SELECTION not in st.session_state or st.session_state[KEY_NAV_SELECTION] not in nav_options:
            st.session_state[KEY_NAV_SELECTION] = "Home"

        # Check if user explicitly clicked the sidebar radio in this run
        user_clicked_radio = False
        if "sidebar_nav_radio" in st.session_state and st.session_state["sidebar_nav_radio"] in nav_options:
            if st.session_state.get("_last_sidebar_nav") != st.session_state["sidebar_nav_radio"]:
                user_clicked_radio = True
                st.session_state[KEY_NAV_SELECTION] = st.session_state["sidebar_nav_radio"]

        # If user did not just click the radio, ensure radio matches KEY_NAV_SELECTION
        if not user_clicked_radio:
            st.session_state["sidebar_nav_radio"] = st.session_state[KEY_NAV_SELECTION]

        nav_choice = st.radio(
            "System Navigation:",
            nav_options,
            key="sidebar_nav_radio"
        )
        st.session_state[KEY_NAV_SELECTION] = nav_choice
        st.session_state["_last_sidebar_nav"] = nav_choice

        st.markdown("---")
        st.markdown("### Active Dataset Status")
        if artifact is not None and df is not None and not df.empty:
            st.markdown(f"**Source:** `{artifact.filename}`")
            st.markdown(f"**Format:** `{artifact.source_type.upper()}`")
            st.markdown(f"**Rows:** `{len(df):,}` | **Cols:** `{len(df.columns)}`")
            if "Revenue" in df.columns and pd.api.types.is_numeric_dtype(df["Revenue"]):
                st.markdown(f"**Total GMV:** `${df['Revenue'].sum():,.0f}`")
        elif artifact is not None:
            st.markdown(f"**Source:** `{artifact.filename}` ({artifact.source_type.upper()})")
            if artifact.page_count:
                st.markdown(f"**Pages:** `{artifact.page_count}`")
        else:
            st.markdown("*No active dataset loaded.*")

        st.markdown("---")
        st.markdown("### Quick File Ingestion")
        sidebar_file = st.file_uploader(
            "Upload File (Max 50MB):",
            type=["csv", "xlsx", "xls", "json", "parquet", "tsv", "txt", "pdf"],
            key="sidebar_quick_file_uploader",
            help="Ingest a custom dataset or document to analyze it across all agents."
        )
        if sidebar_file is not None:
            file_mb = sidebar_file.size / (1024 * 1024)
            if file_mb > 50.0:
                st.sidebar.error("File exceeds 50MB limit.")
            else:
                st.sidebar.caption(f"Selected: `{sidebar_file.name}` ({file_mb:.2f} MB)")
                if st.sidebar.button("Load Dataset", key="sidebar_load_file_btn", type="primary", use_container_width=True):
                    try:
                        import io
                        sidebar_file.seek(0)
                        file_bytes = sidebar_file.read()
                        new_artifact = load_file_artifact(io.BytesIO(file_bytes), filename=sidebar_file.name)
                        if new_artifact.source_type == "excel":
                            new_artifact.metadata["raw_bytes"] = file_bytes
                        if new_artifact.errors:
                            st.sidebar.error(f"Ingestion failed: {'; '.join(new_artifact.errors)}")
                        else:
                            st.session_state[KEY_ACTIVE_ARTIFACT] = new_artifact
                            if new_artifact.dataframe is not None:
                                st.session_state["dataset"] = new_artifact.dataframe
                                st.session_state["dataset_source"] = f"{sidebar_file.name} ({len(new_artifact.dataframe):,} records)"
                            else:
                                st.session_state["dataset"] = None
                                st.session_state["dataset_source"] = f"{sidebar_file.name} ({new_artifact.source_type.upper()})"
                            reset_investigation()
                            st.sidebar.success(f"Loaded {sidebar_file.name}!")
                            st.rerun()
                    except Exception as ex:
                        st.sidebar.error(f"Ingestion failed: {str(ex)}")

        if artifact and artifact.source_type != "synthetic":
            if st.button("Switch to Synthetic Benchmark", use_container_width=True):
                synth_art = get_synthetic_artifact(num_records=3000, seed=42)
                st.session_state[KEY_ACTIVE_ARTIFACT] = synth_art
                st.session_state["dataset"] = synth_art.dataframe
                st.session_state["dataset_source"] = f"Synthetic Benchmark ({len(synth_art.dataframe):,} records)"
                reset_investigation()
                st.rerun()

        st.markdown("---")
        st.markdown("### Agent Pipeline Status")
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
                tag = "[Completed]"
            elif status == "RUNNING":
                tag = "[Running]"
            elif status == "FAILED":
                tag = "[Failed]"
            else:
                tag = "[Idle]"
            st.markdown(f"**{tag}** <small>{name}</small>", unsafe_allow_html=True)

        st.markdown("---")
        with st.expander("Settings & API Key Configuration", expanded=False):
            from llm.client import LLMClient
            probe_client = LLMClient()
            if probe_client.is_configured:
                st.success(f"Live AI Active: Provider {probe_client.provider.title()} ({probe_client.model})")
            else:
                st.info("Offline Mode: Deterministic analytical engine active (no API key required).")

            custom_key = st.text_input(
                "API Key (Gemini / OpenAI / Groq):",
                type="password",
                value=st.session_state.get(KEY_LLM_API_KEY, st.session_state.get("custom_llm_api_key", "")),
                help="Gemini keys (aistudio.google.com) are free. OpenAI keys start with sk-. Groq keys start with gsk_."
            )
            if custom_key != st.session_state.get(KEY_LLM_API_KEY, ""):
                st.session_state[KEY_LLM_API_KEY] = custom_key
                st.session_state["custom_llm_api_key"] = custom_key
                st.rerun()

        st.markdown("---")
        if st.button("Reset Investigation State", use_container_width=True):
            reset_investigation()
            st.rerun()

        st.markdown(
            "<div style='font-size: 0.72rem; color: #94A3B8; text-align: center; margin-top: 1rem;'>"
            "Deterministic Multi-Agent Architecture<br>Offline-First Analytical Engine"
            "</div>",
            unsafe_allow_html=True
        )

    # Route navigation view
    if nav_choice == "Home":
        render_home_view(orchestrator)
    elif nav_choice == "Data Workspace":
        render_data_workspace_view()
    elif nav_choice == "AI Investigator":
        render_ai_investigator_view(orchestrator)
    elif nav_choice == "Analytics Dashboard":
        render_analytics_dashboard_view()
    elif nav_choice == "Reports":
        render_reports_view()
    elif nav_choice == "Investigation History":
        render_investigation_history_view()
    elif nav_choice == "About & Architecture":
        render_about_view()


if __name__ == "__main__":
    main()
