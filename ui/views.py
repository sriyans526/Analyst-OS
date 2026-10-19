"""
UI Views and Page Renderers for AnalystOS.

Clean, enterprise SaaS design without emojis.
Implements the 7 core navigation sections:
1. Home
2. Data Workspace
3. AI Investigator
4. Analytics Dashboard
5. Reports
6. Investigation History
7. About & Architecture
"""

from __future__ import annotations
import io
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
import pandas as pd
import streamlit as st
import plotly.express as px

from tools.ingest import (
    DatasetArtifact,
    load_file_artifact,
    load_excel_artifact,
    get_synthetic_artifact,
)
from tools.data_tools import (
    detect_dataset_columns,
    apply_user_column_mapping,
    inspect_schema,
)
from tools.validation_tools import validate_dataset_integrity
from tools.analytics_tools import (
    calculate_kpis,
    calculate_monthly_trends,
    analyze_category_performance,
    analyze_regional_performance,
    analyze_product_performance,
    detect_anomalies_and_changes,
)
from tools.chart_generator import suggest_charts_for_question, render_chart_spec
from ui.charts import (
    create_monthly_trend_chart,
    create_category_margin_chart,
    create_regional_chart,
    create_product_profit_chart,
)
from workflow.orchestrator import MultiAgentOrchestrator
from workflow.types import InvestigationResult, AgentStatus
from reports.pdf_generator import generate_investigation_report, generate_dashboard_report

# Session state keys
KEY_ACTIVE_ARTIFACT = "active_artifact"
KEY_CHAT_HISTORY = "chat_history"
KEY_INVESTIGATION_RESULT = "investigation_result"
KEY_INVESTIGATION_HISTORY = "investigation_history"
KEY_CURRENT_INV_ID = "current_investigation_id"
KEY_CHART_SPECS = "chart_specs"
KEY_REPORT_BYTES = "report_bytes"
KEY_LLM_API_KEY = "llm_api_key"
KEY_NAV_SELECTION = "system_navigation_selection"


def navigate_to(page: str):
    """Programmatically transition to a system navigation page."""
    st.session_state[KEY_NAV_SELECTION] = page
    st.session_state["sidebar_nav_radio"] = page
    st.rerun()


def _get_active_artifact() -> Optional[DatasetArtifact]:
    """Retrieve the active DatasetArtifact from session state."""
    return st.session_state.get(KEY_ACTIVE_ARTIFACT, None)


def _render_active_dataset_banner(artifact: Optional[DatasetArtifact]):
    """Render a clean enterprise banner showing active dataset info."""
    if artifact is not None:
        source_name = artifact.filename
        source_type = artifact.source_type.upper()
        if artifact.dataframe is not None:
            records_count = f"{len(artifact.dataframe):,} records"
            cols_count = f"{len(artifact.dataframe.columns)} columns"
            st.markdown(f"""
            <div class="banner-container">
                <b>Active Dataset:</b> <code>{source_name}</code> ({source_type}) &nbsp;|&nbsp; 
                <span>{records_count}</span> &nbsp;|&nbsp; 
                <span>{cols_count}</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            page_info = f"{artifact.page_count} pages" if artifact.page_count else "Document"
            st.markdown(f"""
            <div class="banner-container">
                <b>Active Document:</b> <code>{source_name}</code> ({source_type}) &nbsp;|&nbsp; 
                <span>{page_info}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="banner-container" style="border-left-color: #94A3B8;">
            <b>No Active Dataset Loaded.</b> Please load sample data or upload a file in the <b>Data Workspace</b>.
        </div>
        """, unsafe_allow_html=True)


# ==============================================================================
# VIEW 1: HOME
# ==============================================================================
def render_home_view(orchestrator: MultiAgentOrchestrator):
    """Render Section 1: Home."""
    st.markdown('<div class="main-header">AnalystOS Business Intelligence Platform</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Autonomous multi-agent analytical system with adversarial claim verification and evidence-backed decision intelligence.</div>', unsafe_allow_html=True)

    artifact = _get_active_artifact()

    # Active dataset status card
    with st.container(border=True):
        st.markdown("### Active Dataset Status")
        if artifact is not None and artifact.dataframe is not None:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Dataset Name", artifact.filename)
            c2.metric("Total Records", f"{len(artifact.dataframe):,}")
            c3.metric("Columns", f"{len(artifact.dataframe.columns)}")
            rel_score = artifact.validation_report.get("reliability_score", "N/A")
            c4.metric("Reliability Score", f"{rel_score}%" if rel_score != "N/A" else "Verified")
        elif artifact is not None:
            st.info(f"Active Document: {artifact.filename} ({artifact.source_type.upper()}) - {artifact.page_count or 1} page(s).")
        else:
            st.info("No active dataset is currently loaded in memory. You can load our pre-configured benchmark data or upload your custom transaction file.")

    st.write("")

    # Quick action buttons row
    st.markdown("### Quick Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Load Sample Data", use_container_width=True, type="primary"):
            synth = get_synthetic_artifact(num_records=3000, seed=42)
            st.session_state[KEY_ACTIVE_ARTIFACT] = synth
            st.session_state["dataset"] = synth.dataframe
            st.session_state["dataset_source"] = f"Synthetic Benchmark ({len(synth.dataframe):,} records)"
            st.session_state[KEY_INVESTIGATION_RESULT] = None
            st.success("Loaded synthetic benchmark dataset (3,000 records).")
            st.rerun()

    with col2:
        if st.button("Upload Dataset", use_container_width=True, key="home_upload_dataset_btn"):
            navigate_to("Data Workspace")

    with col3:
        if st.button("Start Investigation", use_container_width=True, key="home_start_inv_btn"):
            navigate_to("AI Investigator")

    st.write("")

    # 3-step getting started guide
    st.markdown("### Getting Started Guide")
    g1, g2, g3 = st.columns(3)
    with g1:
        with st.container(border=True):
            st.markdown("#### 1. Ingest Data")
            st.markdown(
                "Upload transactions in CSV, Excel (XLSX/XLS), JSON, Parquet, TSV, or PDF. "
                "Headers are automatically normalized to canonical metrics."
            )
    with g2:
        with st.container(border=True):
            st.markdown("#### 2. AI Investigation")
            st.markdown(
                "Submit natural language questions. Six specialized agents audit data, formulate plans, "
                "execute computations, and verify findings adversarially."
            )
    with g3:
        with st.container(border=True):
            st.markdown("#### 3. Executive Reports")
            st.markdown(
                "Explore interactive multi-dimensional dashboards and generate publication-quality "
                "formal PDF reports with concrete strategic recommendations."
            )


# ==============================================================================
# VIEW 2: DATA WORKSPACE
# ==============================================================================
def render_data_workspace_view():
    """Render Section 2: Data Workspace."""
    st.markdown('<div class="main-header">Data Workspace & Ingestion Hub</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Unified multi-format dataset ingestion, schema introspection, and data reliability governance.</div>', unsafe_allow_html=True)

    tab_upload, tab_synthetic = st.tabs([
        "Upload File (CSV, Excel, JSON, Parquet, TSV, PDF)",
        "Synthetic Benchmark Dataset"
    ])

    with tab_upload:
        st.markdown("#### Upload Data File")
        st.markdown(
            "Upload sales, revenue, or transaction data. Supported extensions: "
            "`CSV`, `XLSX`, `XLS`, `JSON`, `PARQUET`, `TSV`, `TXT`, `PDF`."
        )

        uploaded_file = st.file_uploader(
            "Select or drop file:",
            type=["csv", "xlsx", "xls", "json", "parquet", "tsv", "txt", "pdf"],
            key="workspace_file_uploader",
            help="Files up to 50MB are supported."
        )

        if uploaded_file is not None:
            file_mb = uploaded_file.size / (1024 * 1024)
            if file_mb > 50.0:
                st.error("File exceeds 50MB safety limit. Please upload a smaller file slice.")
            else:
                st.info(f"Selected file: **{uploaded_file.name}** ({file_mb:.2f} MB)")

                # If Excel file, inspect available sheets before loading
                sheet_to_load = None
                fname_lower = uploaded_file.name.lower()
                if fname_lower.endswith((".xlsx", ".xls")):
                    try:
                        excel_file = pd.ExcelFile(uploaded_file)
                        sheet_names = excel_file.sheet_names
                        if len(sheet_names) > 1:
                            sheet_to_load = st.selectbox(
                                "Select sheet to import:",
                                sheet_names,
                                index=0,
                                key="upload_sheet_selector"
                            )
                        elif sheet_names:
                            sheet_to_load = sheet_names[0]
                    except Exception as ex:
                        st.warning(f"Note: Could not inspect workbook sheets: {ex}")

                # Clearly visible explicit Load Dataset button
                if st.button("Load Dataset", type="primary", key="btn_load_workspace_file", use_container_width=True):
                    with st.spinner(f"Ingesting and validating '{uploaded_file.name}'..."):
                        try:
                            uploaded_file.seek(0)
                            raw_bytes = uploaded_file.read()

                            if fname_lower.endswith((".xlsx", ".xls")) and sheet_to_load:
                                artifact = load_excel_artifact(io.BytesIO(raw_bytes), filename=uploaded_file.name, sheet_name=sheet_to_load)
                            else:
                                artifact = load_file_artifact(io.BytesIO(raw_bytes), filename=uploaded_file.name)

                            # Cache raw bytes for Excel sheet switching
                            if fname_lower.endswith((".xlsx", ".xls")):
                                artifact.metadata["raw_bytes"] = raw_bytes

                            if artifact.errors:
                                st.error("Failed to load dataset:\n\n" + "\n".join(f"- {e}" for e in artifact.errors))
                            else:
                                st.session_state[KEY_ACTIVE_ARTIFACT] = artifact
                                if artifact.dataframe is not None:
                                    st.session_state["dataset"] = artifact.dataframe
                                    st.session_state["dataset_source"] = f"{artifact.filename} ({len(artifact.dataframe):,} records)"
                                    st.session_state["upload_success_message"] = (
                                        f"Successfully loaded '{uploaded_file.name}': "
                                        f"{len(artifact.dataframe):,} rows, {len(artifact.dataframe.columns)} columns."
                                    )
                                else:
                                    st.session_state["dataset"] = None
                                    st.session_state["dataset_source"] = f"{artifact.filename} ({artifact.source_type.upper()})"
                                    st.session_state["upload_success_message"] = (
                                        f"Successfully loaded document '{uploaded_file.name}' ({artifact.page_count or 1} page(s))."
                                    )

                                from app import reset_investigation
                                reset_investigation()
                                st.rerun()
                        except Exception as ex:
                            st.error(f"Ingestion failed: {str(ex)}")

        # Display success message if a file was recently loaded
        if "upload_success_message" in st.session_state:
            st.success(st.session_state["upload_success_message"])

    with tab_synthetic:
        st.markdown("#### Reproducible E-Commerce Benchmark Dataset")
        st.markdown(
            "AnalystOS includes a pre-configured synthetic sales benchmark with realistic business dynamics: "
            "Q4 profitless growth, H2 Electronics margin compression, and South regional discount drag."
        )

        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            records_count = st.slider("Record Count:", min_value=2000, max_value=10000, value=3000, step=500, key="slider_synth_records")
        with c2:
            seed_val = st.number_input("Random Seed:", value=42, step=1, key="input_synth_seed")
        with c3:
            st.write("")
            st.write("")
            if st.button("Generate Benchmark", type="primary", use_container_width=True):
                with st.spinner("Generating consistent e-commerce benchmark data..."):
                    synth_art = get_synthetic_artifact(num_records=records_count, seed=int(seed_val))
                    st.session_state[KEY_ACTIVE_ARTIFACT] = synth_art
                    st.session_state["dataset"] = synth_art.dataframe
                    st.session_state["dataset_source"] = f"Synthetic Benchmark ({records_count:,} records, seed={seed_val})"
                    st.session_state.pop("upload_success_message", None)
                    from app import reset_investigation
                    reset_investigation()
                    st.success(f"Generated and loaded {len(synth_art.dataframe):,} records.")
                    st.rerun()

    # Active dataset profile and audits
    active_art = _get_active_artifact()
    if active_art is not None:
        st.write("")
        st.markdown("---")
        st.markdown(f"### Active Dataset Profile: `{active_art.filename}` ({active_art.source_type.upper()})")

        # Action buttons: Replace or Remove
        b1, b2, _ = st.columns([1, 1, 3])
        with b1:
            if st.button("Remove Dataset", use_container_width=True, key="btn_remove_dataset"):
                st.session_state[KEY_ACTIVE_ARTIFACT] = None
                if "dataset" in st.session_state:
                    del st.session_state["dataset"]
                st.session_state["dataset_source"] = "No active dataset"
                st.session_state.pop("upload_success_message", None)
                from app import reset_investigation
                reset_investigation()
                st.rerun()
        with b2:
            if st.button("Reload Benchmark", use_container_width=True, key="btn_reload_benchmark"):
                synth = get_synthetic_artifact(num_records=3000, seed=42)
                st.session_state[KEY_ACTIVE_ARTIFACT] = synth
                st.session_state["dataset"] = synth.dataframe
                st.session_state["dataset_source"] = f"Synthetic Benchmark ({len(synth.dataframe):,} records)"
                st.session_state.pop("upload_success_message", None)
                from app import reset_investigation
                reset_investigation()
                st.rerun()

        # If current active artifact is Excel, offer sheet switcher
        if active_art.source_type == "excel" and len(active_art.sheet_names) > 1 and active_art.metadata.get("raw_bytes"):
            st.markdown("##### Switch Sheet in Current Excel Workbook")
            current_sheet_idx = 0
            if active_art.selected_sheet in active_art.sheet_names:
                current_sheet_idx = active_art.sheet_names.index(active_art.selected_sheet)

            selected_sheet = st.selectbox(
                "Available Workbook Sheets:",
                active_art.sheet_names,
                index=current_sheet_idx,
                key="active_excel_sheet_selector"
            )
            if selected_sheet != active_art.selected_sheet:
                if st.button("Switch to Selected Sheet", key="btn_switch_sheet_loaded"):
                    raw_bytes = active_art.metadata["raw_bytes"]
                    new_art = load_excel_artifact(io.BytesIO(raw_bytes), filename=active_art.filename, sheet_name=selected_sheet)
                    new_art.metadata["raw_bytes"] = raw_bytes
                    st.session_state[KEY_ACTIVE_ARTIFACT] = new_art
                    st.session_state["dataset"] = new_art.dataframe
                    st.session_state["dataset_source"] = f"{new_art.filename} [{selected_sheet}] ({len(new_art.dataframe):,} records)"
                    st.session_state["upload_success_message"] = f"Switched to sheet '{selected_sheet}' ({len(new_art.dataframe):,} records)."
                    from app import reset_investigation
                    reset_investigation()
                    st.rerun()

        # Display errors or warnings if present
        if active_art.errors:
            for err in active_art.errors:
                st.error(f"[Error] {err}")
        if active_art.warnings:
            for warn in active_art.warnings:
                st.warning(f"[Warning] {warn}")

        df = active_art.dataframe
        if df is not None and not df.empty:
            schema_info = active_art.schema
            val_rep = active_art.validation_report

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Total Rows", f"{len(df):,}")
            m2.metric("Columns", f"{len(df.columns)}")
            m3.metric("Memory Usage", f"{schema_info.get('memory_usage_mb', 0.0):.1f} MB")
            m4.metric("Reliability Score", f"{val_rep.get('reliability_score', 100)}%")
            m5.metric("Confidence Tier", val_rep.get("confidence_tier", "HIGH CONFIDENCE"))

            with st.expander("Column Schema & Data Types", expanded=False):
                col_data = []
                for col in df.columns:
                    col_data.append({
                        "Column": col,
                        "Type": str(df[col].dtype),
                        "Non-Null Count": int(df[col].notna().sum()),
                        "Unique Values": int(df[col].nunique())
                    })
                st.dataframe(pd.DataFrame(col_data), use_container_width=True)

            with st.expander("Data Configuration & Column Mapping", expanded=True):
                st.markdown("#### Detected Columns & Inferred Semantic Meanings")
                st.markdown(
                    "AnalystOS automatically analyzes column data types and infers potential business roles. "
                    "Review detected fields below and confirm or adjust mappings to canonical AnalystOS metrics."
                )

                detected_info = active_art.metadata.get("detected_columns")
                if not detected_info or not isinstance(detected_info, dict) or "columns" not in detected_info:
                    detected_info = detect_dataset_columns(df)
                    active_art.metadata["detected_columns"] = detected_info

                col_meta = detected_info.get("columns", {})
                inferred_roles = detected_info.get("inferred_roles", {})

                if col_meta:
                    det_rows = []
                    for c_name, c_props in col_meta.items():
                        samples_str = ", ".join(c_props.get("samples", [])[:2])
                        det_rows.append({
                            "Dataset Column": c_name,
                            "Detected Type": c_props.get("type", "General"),
                            "Inferred Role": c_props.get("inferred_role", "General Field"),
                            "Sample Values": samples_str
                        })
                    st.dataframe(pd.DataFrame(det_rows), use_container_width=True, hide_index=True)

                st.write("")
                st.markdown("#### Canonical AnalystOS Metric Mapping")
                st.caption(
                    "Map your dataset's columns to standard AnalystOS analytical fields. "
                    "If Revenue is not mapped but Quantity and Unit Price are, Revenue will be auto-calculated. "
                    "If Profit is not mapped but Revenue and Cost are, Profit will be auto-calculated."
                )

                canonical_fields = [
                    ("Revenue", "Top-line revenue / sales amount (e.g. Total Spent, Sales, Amount, Total)"),
                    ("Quantity", "Volume or item count sold (e.g. Quantity, Qty, Units Sold)"),
                    ("Unit Price", "Price per unit or product rate (e.g. Price, Unit Price, Rate)"),
                    ("Cost", "Total product or operational cost (e.g. Cost, Total Cost, Expenses)"),
                    ("Profit", "Net bottom-line profit or margin amount (e.g. Profit, Net Profit)"),
                    ("Order Date", "Date or timestamp of transaction (e.g. Transaction Date, Date)"),
                    ("Category", "Product category, type, or department (e.g. Category, Dept)"),
                    ("Region", "Geographic market, store, or location (e.g. Location, Region, City)"),
                    ("Product Name", "Product or item description (e.g. Item, Product Name, SKU)")
                ]

                col_choices = ["[Not Mapped]"] + list(df.columns)
                user_mapping = {}

                c_m1, c_m2, c_m3 = st.columns(3)
                mapping_cols = [c_m1, c_m2, c_m3]

                for idx, (canonical, help_text) in enumerate(canonical_fields):
                    target_ui_col = mapping_cols[idx % 3]
                    with target_ui_col:
                        default_idx = 0
                        if canonical in df.columns:
                            default_idx = col_choices.index(canonical)
                        elif canonical in inferred_roles and inferred_roles[canonical] in col_choices:
                            default_idx = col_choices.index(inferred_roles[canonical])

                        selected_col = st.selectbox(
                            f"**{canonical}**",
                            options=col_choices,
                            index=default_idx,
                            help=help_text,
                            key=f"col_map_select_{canonical}"
                        )
                        if selected_col != "[Not Mapped]":
                            user_mapping[canonical] = selected_col

                st.write("")
                if st.button("Apply Column Mapping", type="primary", key="btn_apply_col_mapping"):
                    updated_df, changes = apply_user_column_mapping(df, user_mapping)
                    active_art.dataframe = updated_df
                    active_art.schema = inspect_schema(updated_df)
                    active_art.validation_report = validate_dataset_integrity(updated_df)
                    active_art.metadata["detected_columns"] = detect_dataset_columns(updated_df)
                    if "column_mapping" not in active_art.metadata:
                        active_art.metadata["column_mapping"] = {}
                    active_art.metadata["column_mapping"].update(changes)

                    st.session_state["dataset"] = updated_df
                    changes_desc = ", ".join(f"{k} -> {v}" for k, v in changes.items()) if changes else "Mappings verified."
                    st.session_state["upload_success_message"] = f"Column mapping successfully applied: {changes_desc}"
                    st.rerun()

            with st.expander("Data Preview (First 20 Rows)", expanded=True):
                st.dataframe(df.head(20), use_container_width=True)

        elif active_art.extracted_text:
            st.info(f"Extracted document text ({len(active_art.extracted_text):,} characters).")
            with st.expander("Document Text Preview", expanded=True):
                st.text_area("Extracted Content:", value=active_art.extracted_text[:4000], height=300, disabled=True)


# ==============================================================================
# VIEW 3: AI INVESTIGATOR
# ==============================================================================
def render_ai_investigator_view(orchestrator: MultiAgentOrchestrator):
    """Render Section 3: AI Investigator."""
    st.markdown('<div class="main-header">AI Investigator</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Ask natural language business questions. Powered by autonomous 6-agent investigation and adversarial verification.</div>', unsafe_allow_html=True)

    artifact = _get_active_artifact()
    _render_active_dataset_banner(artifact)

    # Reset button prominently placed
    col_reset, col_spacer = st.columns([2, 5])
    with col_reset:
        if st.button("Reset Investigation", use_container_width=True):
            from app import reset_investigation
            reset_investigation()
            st.success("Investigation state reset successfully.")
            st.rerun()

    st.write("")

    # Sample questions as clickable buttons
    st.markdown("<b>Sample Business Questions:</b>", unsafe_allow_html=True)
    sq1, sq2, sq3, sq4 = st.columns(4)
    preset_q = None
    with sq1:
        if st.button("Why did profits decrease?"):
            preset_q = "Why did our profits decrease, which products or regions contributed most to the decline, and what actions should we take?"
    with sq2:
        if st.button("Regional margin disparities?"):
            preset_q = "Which regions are underperforming in profit margin and what is driving the regional disparity?"
    with sq3:
        if st.button("Top and bottom products?"):
            preset_q = "What are our top and bottom performing products by net profit and margin efficiency?"
    with sq4:
        if st.button("Profitless growth in peak months?"):
            preset_q = "Is there evidence of profitless growth where revenue expanded but net margins collapsed?"

    # Chat history initialization
    if KEY_CHAT_HISTORY not in st.session_state:
        st.session_state[KEY_CHAT_HISTORY] = []

    # Display chat conversation
    for msg in st.session_state[KEY_CHAT_HISTORY]:
        role = msg.get("role", "assistant")
        with st.chat_message(role):
            st.markdown(msg.get("content", ""))

            # If message contains associated charts, render them
            chart_specs = msg.get("chart_specs", [])
            if chart_specs and artifact and artifact.dataframe is not None:
                with st.expander("Investigation Visualizations", expanded=True):
                    for spec in chart_specs:
                        fig = render_chart_spec(spec, artifact.dataframe)
                        st.plotly_chart(fig, use_container_width=True)

            # If message contains evidence verification summary
            evidence_summary = msg.get("evidence_summary")
            if evidence_summary:
                with st.expander("Adversarial Verification Audit", expanded=False):
                    st.markdown(evidence_summary)

            # If message has download report button
            inv_res = msg.get("investigation_result")
            if inv_res and artifact:
                pdf_bytes = generate_investigation_report(inv_res, artifact, msg.get("question", "Business Question"))
                st.download_button(
                    label="Download Investigation Report (PDF)",
                    data=pdf_bytes,
                    file_name="AnalystOS_Investigation_Report.pdf",
                    mime="application/pdf",
                    key=f"dl_pdf_{msg.get('msg_id', uuid.uuid4())}"
                )

    # User input bar
    user_prompt = st.chat_input("Enter your business question regarding revenue, margins, or operations...")
    question_to_run = preset_q or user_prompt

    if question_to_run:
        msg_id = str(uuid.uuid4())
        # Append user message
        st.session_state[KEY_CHAT_HISTORY].append({
            "msg_id": msg_id,
            "role": "user",
            "content": question_to_run
        })

        if artifact is None:
            st.session_state[KEY_CHAT_HISTORY].append({
                "msg_id": str(uuid.uuid4()),
                "role": "assistant",
                "content": "No active dataset is loaded. Please load a dataset in the Data Workspace to begin an investigation."
            })
            st.rerun()

        elif artifact.dataframe is not None:
            # Full 6-agent workflow
            with st.spinner("Running 6-agent investigation..."):
                status_placeholder = st.empty()

                def _live_status(agent_name: str, status: AgentStatus, record):
                    status_placeholder.text(f"Executing: {agent_name} [{status.value}]")

                res = orchestrator.run_investigation(
                    question=question_to_run,
                    df=artifact.dataframe,
                    status_callback=_live_status
                )
                status_placeholder.empty()

                if res.success and res.decision_report:
                    st.session_state[KEY_INVESTIGATION_RESULT] = res

                    # Formulate comprehensive response text
                    answer_text = (
                        f"### Executive Synthesis\n\n{res.decision_report.executive_summary}\n\n"
                        f"**Primary Root Cause Driver:**\n{res.findings.primary_driver}\n\n"
                        f"#### Strategic Recommendations:\n"
                    )
                    for rec in res.decision_report.recommendations:
                        answer_text += f"- **[{rec.id}] {rec.title}** ({rec.target_area}): {rec.expected_outcome}\n"

                    # Build evidence audit text
                    ev_text = f"**Verification Score:** {res.verification_report.verification_score}%\n\n"
                    ev_text += f"- Verified Claims: {res.verification_report.passed_count}\n"
                    ev_text += f"- Rejected Claims: {res.verification_report.failed_count}\n\n"
                    for p in res.verification_report.passed_checks:
                        ev_text += f"- [Passed] **{p.get('claim', '')}**: {p.get('evidence', '')}\n"

                    # Question-driven chart suggestions
                    suggested_charts = suggest_charts_for_question(question_to_run, artifact.dataframe)
                    st.session_state[KEY_CHART_SPECS] = suggested_charts

                    # Add to chat history
                    st.session_state[KEY_CHAT_HISTORY].append({
                        "msg_id": str(uuid.uuid4()),
                        "role": "assistant",
                        "content": answer_text,
                        "question": question_to_run,
                        "chart_specs": suggested_charts,
                        "evidence_summary": ev_text,
                        "investigation_result": res
                    })

                    # Add to investigation history
                    if KEY_INVESTIGATION_HISTORY not in st.session_state:
                        st.session_state[KEY_INVESTIGATION_HISTORY] = []

                    st.session_state[KEY_INVESTIGATION_HISTORY].append({
                        "id": str(uuid.uuid4()),
                        "question": question_to_run,
                        "dataset": artifact.filename,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "result": res,
                        "summary_preview": res.decision_report.executive_summary[:200] + "..."
                    })

                else:
                    st.session_state[KEY_CHAT_HISTORY].append({
                        "msg_id": str(uuid.uuid4()),
                        "role": "assistant",
                        "content": f"Investigation halted: {res.error}"
                    })

            st.rerun()

        elif artifact.extracted_text:
            # PDF-only text response
            with st.spinner("Analyzing document text..."):
                from llm.investigator import AIInvestigator
                inv = AIInvestigator()
                chat_res = inv.chat(
                    message=question_to_run,
                    df=pd.DataFrame(),
                    orchestrator=orchestrator,
                    chat_history=st.session_state[KEY_CHAT_HISTORY]
                )
                answer = chat_res["response"]
                if "No dataset is currently loaded" in answer:
                    answer = (
                        f"Document-grounded analysis of '{artifact.filename}':\n\n"
                        f"The document contains {artifact.page_count or 1} page(s) of unstructured text. "
                        f"Direct numerical transactional computations are disabled because no structured financial tables were extracted."
                    )

                st.session_state[KEY_CHAT_HISTORY].append({
                    "msg_id": str(uuid.uuid4()),
                    "role": "assistant",
                    "content": answer
                })
            st.rerun()


# ==============================================================================
# VIEW 4: ANALYTICS DASHBOARD
# ==============================================================================
def render_analytics_dashboard_view():
    """Render Section 4: Analytics Dashboard."""
    st.markdown('<div class="main-header">Analytics Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Interactive multidimensional financial and operational intelligence.</div>', unsafe_allow_html=True)

    artifact = _get_active_artifact()
    _render_active_dataset_banner(artifact)

    if artifact is None or artifact.dataframe is None or artifact.dataframe.empty:
        with st.container(border=True):
            st.markdown("### No Tabular Dataset Active")
            st.markdown(
                "The Analytics Dashboard requires an active dataset with structured records. "
                "You can upload your custom transaction file or load our pre-configured e-commerce benchmark."
            )
            col_b1, col_b2, _ = st.columns([1, 1, 2])
            with col_b1:
                if st.button("Go to Data Workspace", type="primary", key="dash_goto_workspace_btn"):
                    navigate_to("Data Workspace")
            with col_b2:
                if st.button("Load Demo Benchmark", key="dash_load_benchmark_btn"):
                    synth = get_synthetic_artifact(num_records=3000, seed=42)
                    st.session_state[KEY_ACTIVE_ARTIFACT] = synth
                    st.session_state["dataset"] = synth.dataframe
                    st.session_state["dataset_source"] = f"Synthetic Benchmark ({len(synth.dataframe):,} records)"
                    st.session_state[KEY_INVESTIGATION_RESULT] = None
                    st.rerun()
        return

    df = artifact.dataframe

    # Filter row
    f_cols = []
    has_cat = "Category" in df.columns
    has_reg = "Region" in df.columns

    filter_dict = {}
    c_f1, c_f2 = st.columns(2)
    with c_f1:
        if has_cat:
            cats = ["All"] + sorted(list(df["Category"].dropna().unique()))
            selected_cat = st.selectbox("Filter Category:", cats)
            if selected_cat != "All":
                filter_dict["Category"] = selected_cat
        else:
            selected_cat = "All"

    with c_f2:
        if has_reg:
            regs = ["All"] + sorted(list(df["Region"].dropna().unique()))
            selected_reg = st.selectbox("Filter Region:", regs)
            if selected_reg != "All":
                filter_dict["Region"] = selected_reg
        else:
            selected_reg = "All"

    filtered_df = df.copy()
    if selected_cat != "All":
        filtered_df = filtered_df[filtered_df["Category"] == selected_cat]
    if selected_reg != "All":
        filtered_df = filtered_df[filtered_df["Region"] == selected_reg]

    # KPI Summary Cards (only display metrics if available)
    kpis = calculate_kpis(filtered_df)
    k_cols = st.columns(5)
    with k_cols[0]:
        if kpis.get("has_revenue"):
            st.metric("Total Revenue", f"${kpis['total_revenue']:,.0f}")
        else:
            st.metric("Total Revenue", "Unavailable", help="Revenue column not identified or mapped in dataset.")
    with k_cols[1]:
        if kpis.get("has_profit"):
            st.metric("Net Profit", f"${kpis['total_profit']:,.0f}")
        else:
            st.metric("Net Profit", "Unavailable", help="Profit / Cost column not identified or mapped in dataset.")
    with k_cols[2]:
        if kpis.get("has_revenue") and kpis.get("has_profit"):
            st.metric("Profit Margin", f"{kpis['profit_margin_pct']}%")
        else:
            st.metric("Profit Margin", "Unavailable", help="Margin requires mapped Revenue and Profit/Cost.")
    with k_cols[3]:
        st.metric("Total Orders", f"{kpis['total_orders']:,}")
    with k_cols[4]:
        if kpis.get("has_revenue"):
            st.metric("Avg Order Value", f"${kpis['average_order_value']:,.1f}")
        else:
            st.metric("Avg Order Value", "Unavailable", help="Requires mapped Revenue column.")

    st.write("")

    # Visualizations Grid
    has_date = "Order Date" in filtered_df.columns or any("date" in c.lower() for c in filtered_df.columns)
    if has_date:
        date_col = "Order Date" if "Order Date" in filtered_df.columns else [c for c in filtered_df.columns if "date" in c.lower()][0]
        monthly_df = calculate_monthly_trends(filtered_df, date_column=date_col)
        if not monthly_df.empty:
            if kpis.get("has_revenue") or kpis.get("has_profit"):
                st.plotly_chart(create_monthly_trend_chart(monthly_df), use_container_width=True)
            else:
                fig_orders = px.line(
                    monthly_df,
                    x="Month",
                    y="orders",
                    markers=True,
                    title="Monthly Activity / Transaction Volume"
                )
                fig_orders.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF")
                st.plotly_chart(fig_orders, use_container_width=True)
    else:
        st.caption("Note: Date column not detected. Monthly trend chart is unavailable.")

    g1, g2 = st.columns(2)
    with g1:
        if has_cat:
            cat_df = analyze_category_performance(filtered_df)
            if not cat_df.empty and (kpis.get("has_revenue") or kpis.get("has_profit")):
                st.plotly_chart(create_category_margin_chart(cat_df), use_container_width=True)
            elif not cat_df.empty:
                cat_counts = filtered_df["Category"].value_counts().reset_index()
                cat_counts.columns = ["Category", "Count"]
                fig_cat_count = px.bar(cat_counts.head(10), x="Category", y="Count", title="Top Categories by Record Count")
                fig_cat_count.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF")
                st.plotly_chart(fig_cat_count, use_container_width=True)
        else:
            potential_cats = [c for c in filtered_df.columns if filtered_df[c].dtype == "object" and filtered_df[c].nunique() <= 50]
            if potential_cats:
                sample_cat = potential_cats[0]
                cat_counts = filtered_df[sample_cat].value_counts().reset_index()
                cat_counts.columns = [sample_cat, "Count"]
                fig_alt = px.bar(cat_counts.head(10), x=sample_cat, y="Count", title=f"Distribution by {sample_cat} (Categorical)")
                fig_alt.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF")
                st.plotly_chart(fig_alt, use_container_width=True)
            else:
                st.caption("Category breakdown unavailable (no categorical column mapped).")

    with g2:
        if has_reg:
            reg_df = analyze_regional_performance(filtered_df)
            if not reg_df.empty and (kpis.get("has_revenue") or kpis.get("has_profit")):
                st.plotly_chart(create_regional_chart(reg_df), use_container_width=True)
            elif not reg_df.empty:
                reg_counts = filtered_df["Region"].value_counts().reset_index()
                reg_counts.columns = ["Region", "Count"]
                fig_reg_count = px.bar(reg_counts.head(10), x="Region", y="Count", title="Top Locations / Regions by Count")
                fig_reg_count.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF")
                st.plotly_chart(fig_reg_count, use_container_width=True)
        else:
            st.caption("Regional breakdown unavailable (Region / Location column not mapped).")

    if ("Product Name" in filtered_df.columns or "Product ID" in filtered_df.columns) and (kpis.get("has_revenue") or kpis.get("has_profit")):
        prod_perf = analyze_product_performance(filtered_df, top_n=5)
        st.plotly_chart(create_product_profit_chart(prod_perf), use_container_width=True)
    elif "Product Name" in filtered_df.columns or "Product ID" in filtered_df.columns:
        p_col = "Product Name" if "Product Name" in filtered_df.columns else "Product ID"
        top_items = filtered_df[p_col].value_counts().head(10).reset_index()
        top_items.columns = [p_col, "Transactions"]
        fig_items = px.bar(top_items, x=p_col, y="Transactions", title=f"Top 10 {p_col} by Frequency")
        fig_items.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF")
        st.plotly_chart(fig_items, use_container_width=True)

    # General dataset charts: correlation heatmap & distributions & missing values
    numeric_df = filtered_df.select_dtypes(include=["number"])
    if len(numeric_df.columns) > 1:
        with st.expander("Correlation Heatmap (Numeric Columns)", expanded=False):
            corr = numeric_df.corr().round(2)
            fig_corr = px.imshow(corr, text_auto=True, color_continuous_scale="RdBu_r", title="Correlation Matrix")
            fig_corr.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF")
            st.plotly_chart(fig_corr, use_container_width=True)

    if not numeric_df.empty:
        with st.expander("Numeric Column Distributions & Statistics", expanded=False):
            st.dataframe(numeric_df.describe().round(2).T, use_container_width=True)

    null_counts = filtered_df.isna().sum()
    if null_counts.sum() > 0:
        with st.expander("Missing Value Analysis", expanded=False):
            null_df = pd.DataFrame({"Column": null_counts.index, "Missing Values": null_counts.values})
            null_df = null_df[null_df["Missing Values"] > 0].sort_values("Missing Values", ascending=False)
            fig_null = px.bar(null_df, x="Column", y="Missing Values", title="Missing Values per Column")
            fig_null.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF")
            st.plotly_chart(fig_null, use_container_width=True)

    # Operational Anomalies
    anomalies = detect_anomalies_and_changes(filtered_df)
    if anomalies:
        st.markdown("### Operational Anomalies & Divergence Flags")
        for anom in anomalies:
            st.warning(f"[{anom.get('severity', 'WARNING')}] {anom.get('type')}: {anom.get('subject')} — {anom.get('description')}")

    # Generate Dashboard PDF Report Button
    st.write("")
    st.markdown("---")
    analytics_payload = {
        "kpis": kpis,
        "category_performance": analyze_category_performance(filtered_df) if has_cat else pd.DataFrame()
    }
    dash_pdf = generate_dashboard_report(analytics_payload, artifact, filter_dict)
    st.download_button(
        label="Generate & Download Dashboard Report (PDF)",
        data=dash_pdf,
        file_name="AnalystOS_Dashboard_Report.pdf",
        mime="application/pdf",
        type="primary"
    )


# ==============================================================================
# VIEW 5: REPORTS
# ==============================================================================
def render_reports_view():
    """Render Section 5: Reports."""
    st.markdown('<div class="main-header">Reports Center</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Download publication-grade executive PDF reports and tabular CSV extracts.</div>', unsafe_allow_html=True)

    artifact = _get_active_artifact()
    res: Optional[InvestigationResult] = st.session_state.get(KEY_INVESTIGATION_RESULT, None)

    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("#### Formal Investigation Report (PDF)")
            if res and res.success:
                st.markdown(f"**Target Query:** `{res.question}`")
                st.markdown(f"**Generated:** {res.timestamp}")
                pdf_bytes = generate_investigation_report(res, artifact, res.question)
                st.download_button(
                    label="Download Investigation Report (PDF)",
                    data=pdf_bytes,
                    file_name="AnalystOS_Executive_Investigation_Report.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
                st.download_button(
                    label="Download Investigation Report (Markdown)",
                    data=res.markdown_report,
                    file_name="AnalystOS_Report.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            else:
                st.info("Execute an investigation in the AI Investigator tab to generate an executive report.")

    with c2:
        with st.container(border=True):
            st.markdown("#### Tabular Data Exports (CSV)")
            if artifact and artifact.dataframe is not None and not artifact.dataframe.empty:
                df = artifact.dataframe
                monthly_csv = calculate_monthly_trends(df).to_csv(index=False)
                cat_csv = analyze_category_performance(df).to_csv(index=False)
                raw_csv = df.to_csv(index=False)

                st.download_button("Export Monthly Trends (CSV)", data=monthly_csv, file_name="monthly_trends.csv", mime="text/csv", use_container_width=True)
                st.download_button("Export Category Breakdown (CSV)", data=cat_csv, file_name="category_performance.csv", mime="text/csv", use_container_width=True)
                st.download_button("Export Active Dataset (CSV)", data=raw_csv, file_name="active_dataset.csv", mime="text/csv", use_container_width=True)
            else:
                st.info("No active dataset loaded for CSV export.")

    if res and res.success and res.markdown_report:
        st.write("")
        with st.expander("Report Preview (Markdown)", expanded=True):
            st.markdown(res.markdown_report)


# ==============================================================================
# VIEW 6: INVESTIGATION HISTORY
# ==============================================================================
def render_investigation_history_view():
    """Render Section 6: Investigation History."""
    st.markdown('<div class="main-header">Investigation History</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Review and restore past multi-agent investigations executed during this session.</div>', unsafe_allow_html=True)

    history = st.session_state.get(KEY_INVESTIGATION_HISTORY, [])
    if not history:
        st.info("No prior investigations recorded in this session. Run queries in the AI Investigator tab to create history entries.")
        return

    for idx, item in enumerate(reversed(history)):
        with st.container(border=True):
            col_text, col_btn = st.columns([4, 1])
            with col_text:
                st.markdown(f"**Question:** `{item.get('question')}`")
                st.caption(f"Dataset: {item.get('dataset')} | Executed: {item.get('timestamp')}")
                st.markdown(f"*{item.get('summary_preview')}*")
            with col_btn:
                if st.button("Reopen", key=f"reopen_{item.get('id', idx)}", use_container_width=True):
                    st.session_state[KEY_INVESTIGATION_RESULT] = item.get("result")
                    navigate_to("AI Investigator")


# ==============================================================================
# VIEW 7: ABOUT & ARCHITECTURE
# ==============================================================================
def render_about_view():
    """Render Section 7: About & Architecture."""
    st.markdown('<div class="main-header">About & System Architecture</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Technical specifications, multi-agent contracts, and data privacy principles.</div>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("### Six-Agent Investigation Architecture")
        st.markdown("""
        AnalystOS implements an autonomous six-agent pipeline where each agent enforces a strict typed contract:
        
        1. **Data Reliability Agent:** Audits numeric bounds, formula consistency, missing values, and date parsing without modifying raw records.
        2. **Planning Agent:** Deconstructs natural language business questions into analytical tasks, required metrics, and testable hypotheses.
        3. **Analytics Execution Agent:** Computes KPIs, monthly trajectory tables, segment contributions, and operational anomalies deterministically.
        4. **Business Investigation Agent:** Isolates primary root cause drivers and synthesizes testable candidate claims across dimensions.
        5. **Critic / Verification Agent:** Adversarially audits candidate claims against raw facts, mathematically verifying or rejecting assertions.
        6. **Decision / Outcome Agent:** Synthesizes verified findings into prioritized issues, actionable strategic recommendations, and limitations.
        """)

    with st.container(border=True):
        st.markdown("### Supported File Formats")
        st.markdown("""
        - **CSV:** Delimited tabular files with automatic column alias normalization.
        - **Excel (XLSX / XLS):** Multi-sheet workbooks with sheet selector.
        - **JSON:** Tabular and key-value records.
        - **Parquet:** Columnar storage format.
        - **TSV / TXT:** Tab-separated and text records.
        - **PDF:** Document text and embedded table extraction via pdfplumber.
        """)

    with st.container(border=True):
        st.markdown("### Technology Stack")
        st.markdown("""
        - **Framework:** Python 3.12, Streamlit
        - **Data Processing:** Pandas, NumPy, PyArrow
        - **Visualization:** Plotly Express & Graph Objects
        - **Reporting:** ReportLab Platypus PDF Generator
        - **LLM Integration:** Google Gemini, OpenAI, Groq (with deterministic offline engine fallback)
        """)

    with st.container(border=True):
        st.markdown("### Data Privacy & Governance")
        st.markdown(
            "All computations are executed in-memory. Uploaded datasets are never transmitted to external servers "
            "unless an optional cloud LLM API key is explicitly configured by the user."
        )
