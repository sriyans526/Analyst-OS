"""
Section and view renderers for AnalystOS Streamlit Application.
"""

from __future__ import annotations
import os
import io
from typing import Optional
import pandas as pd
import streamlit as st

from tools.analytics_tools import (
    calculate_kpis,
    calculate_monthly_trends,
    analyze_category_performance,
    analyze_regional_performance,
    analyze_product_performance,
    detect_anomalies_and_changes,
)
from tools.data_tools import inspect_schema, detect_missing_values, detect_duplicates, load_csv
from tools.validation_tools import validate_dataset_integrity
from data.data_generator import generate_ecommerce_dataset
from workflow.orchestrator import MultiAgentOrchestrator
from workflow.types import InvestigationResult, AgentStatus
from ui.charts import (
    create_monthly_trend_chart,
    create_category_margin_chart,
    create_regional_chart,
    create_product_profit_chart,
)
from ui.components import render_agent_status_card


def render_overview_view(df: pd.DataFrame):
    """Render Section A: Overview."""
    st.markdown('<div class="main-header">AnalystOS — Multi-Agent Business Investigation System</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Autonomous multi-agent analytical system with adversarial claim verification and evidence-backed decision intelligence.</div>', unsafe_allow_html=True)

    if df is None or df.empty:
        st.warning("⚠️ No dataset loaded. Please navigate to the Data Management tab to load data.")
        return

    active_source = st.session_state.get("dataset_source", "Synthetic Benchmark")
    st.markdown(f"""
    <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #3B82F6; padding: 0.6rem 1rem; border-radius: 6px; margin-bottom: 1.2rem; font-size: 0.9rem; color: #1E293B;">
        📊 <b>Active Dataset:</b> <code>{active_source}</code> ({len(df):,} records) &nbsp;|&nbsp; 
        <span>To analyze your own file, use <b>Quick CSV Upload</b> in the sidebar or open <b>📁 Data Management</b>.</span>
    </div>
    """, unsafe_allow_html=True)

    kpis = calculate_kpis(df)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Revenue</div>
            <div class="metric-value">${kpis['total_revenue']:,.0f}</div>
            <div class="metric-sub">{kpis['total_units']:,} units sold</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Net Profit</div>
            <div class="metric-value" style="color: #10B981;">${kpis['total_profit']:,.0f}</div>
            <div class="metric-sub">${kpis['total_cost']:,.0f} total cost</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        margin_color = "#10B981" if kpis['profit_margin_pct'] >= 25 else "#F59E0B"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Profit Margin</div>
            <div class="metric-value" style="color: {margin_color};">{kpis['profit_margin_pct']}%</div>
            <div class="metric-sub">Net Margin Efficiency</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Orders</div>
            <div class="metric-value">{kpis['total_orders']:,}</div>
            <div class="metric-sub">Unique Transactions</div>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Order Value (AOV)</div>
            <div class="metric-value">${kpis['average_order_value']:,.1f}</div>
            <div class="metric-sub">${kpis['average_profit_per_order']:,.1f} profit / order</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.write("")

    # Visual previews
    c_left, c_right = st.columns([3, 2])
    with c_left:
        monthly_df = calculate_monthly_trends(df)
        st.plotly_chart(create_monthly_trend_chart(monthly_df), use_container_width=True)
    with c_right:
        cat_df = analyze_category_performance(df)
        st.plotly_chart(create_category_margin_chart(cat_df), use_container_width=True)


def render_data_management_view():
    """Render Section B: Data Management."""
    st.markdown('<div class="main-header">Data Management & Dataset Governance</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Seamlessly upload your enterprise CSV transaction logs or configure the reproducible synthetic benchmark dataset.</div>', unsafe_allow_html=True)

    tab_upload, tab_synthetic = st.tabs([
        "📂 Upload My Own CSV File",
        "⚙️ Use Built-in Synthetic Benchmark"
    ])

    with tab_upload:
        st.markdown("### 📤 Upload Your Business Transaction CSV")
        st.markdown(
            "Upload any e-commerce or retail sales dataset. AnalystOS automatically parses column headers, "
            "normalizes standard business metrics, and executes real-time data integrity audits."
        )

        with st.expander("ℹ️ Supported Dataset Schema & Formatting Guide", expanded=False):
            st.markdown("""
            **Supported & Auto-Mapped Columns (Case-Insensitive):**
            - **Order ID:** `Order ID`, `order_id`, `transaction_id`, `id` *(Auto-generated if absent)*
            - **Order Date:** `Order Date`, `order_date`, `date`, `timestamp`, `sale_date`
            - **Product Name / ID:** `Product Name`, `Product ID`, `product`, `item`, `sku`, `title`
            - **Category:** `Category`, `product_category`, `department`, `dept`
            - **Region:** `Region`, `territory`, `zone`, `location`, `state`, `market`
            - **Quantity:** `Quantity`, `qty`, `units`, `volume`, `count`
            - **Unit Price:** `Unit Price`, `unit_price`, `price`, `selling_price`
            - **Unit Cost:** `Unit Cost`, `unit_cost`, `cost_price`, `base_cost`
            - **Revenue:** `Revenue`, `sales`, `total_sales`, `amount` *(Auto-computed as Quantity × Unit Price if absent)*
            - **Cost:** `Cost`, `total_cost`, `cogs` *(Auto-computed as Quantity × Unit Cost if absent)*
            - **Profit:** `Profit`, `net_profit`, `margin` *(Auto-computed as Revenue − Cost if absent)*

            **Safety & Limits:**
            - **Application File Size Limit:** 50 MB (Configured in `.streamlit/config.toml` within Streamlit's 200MB ceiling).
            - **Missing Column Adaptability:** If Cost or Profit are not in your file, top-line sales, order volume, and category trends will still be analyzed, and profit-margin analysis will be safely disabled.
            """)

        uploaded_file = st.file_uploader(
            "Select or Drag & Drop a CSV File (Max 50MB):",
            type=["csv"],
            key="data_mgmt_file_uploader",
            help="Upload an e-commerce or retail transaction CSV up to 50MB."
        )

        if uploaded_file is not None:
            file_size_bytes = uploaded_file.size
            file_size_mb = file_size_bytes / (1024 * 1024)
            file_size_str = f"{file_size_mb:.2f} MB" if file_size_mb >= 1.0 else f"{file_size_bytes / 1024:.1f} KB"

            if file_size_mb > 50.0:
                st.error(f"⛔ File size ({file_size_str}) exceeds the 50MB safety limit. Please upload a smaller slice.")
            else:
                try:
                    with st.spinner(f"Ingesting and normalizing '{uploaded_file.name}'..."):
                        raw_bytes = uploaded_file.getvalue()
                        df_uploaded = load_csv(io.BytesIO(raw_bytes), auto_normalize=True)

                        # Set active dataset in session state
                        st.session_state["dataset"] = df_uploaded
                        st.session_state["dataset_source"] = f"Uploaded CSV: {uploaded_file.name} ({file_size_str})"
                        st.session_state["investigation_result"] = None

                        st.success(
                            f"✅ Successfully loaded **{uploaded_file.name}** ({file_size_str})! "
                            f"Parsed **{len(df_uploaded):,} rows** and **{len(df_uploaded.columns)} columns**. "
                            f"Active across all analytics and investigation agents."
                        )
                except Exception as e:
                    st.error(f"Failed to ingest CSV: {str(e)}")

    with tab_synthetic:
        st.markdown("### ⚙️ Reproducible Synthetic Benchmark Dataset")
        st.markdown(
            "AnalystOS includes a pre-configured, realistic 3,000-order transaction benchmark "
            "with demonstrative business phenomena (Q4 profitless growth, H2 Electronics margin squeeze, and South regional discount drag)."
        )

        c_sync1, c_sync2, c_sync3 = st.columns([2, 1, 1])
        with c_sync1:
            records_count = st.slider("Record Count to Generate:", min_value=2000, max_value=10000, value=3000, step=500, key="synth_slider")
        with c_sync2:
            seed_val = st.number_input("Random Seed:", value=42, step=1, key="synth_seed")
        with c_sync3:
            st.write("")
            st.write("")
            if st.button("🔄 Generate & Switch", type="primary", use_container_width=True, key="btn_synth_switch"):
                with st.spinner("Generating consistent e-commerce benchmark data..."):
                    new_df = generate_ecommerce_dataset(num_records=records_count, seed=int(seed_val))
                    st.session_state["dataset"] = new_df
                    st.session_state["dataset_source"] = f"Synthetic Benchmark ({records_count:,} records, seed={seed_val})"
                    st.session_state["investigation_result"] = None
                    st.success(f"Generated and switched to {len(new_df):,} benchmark records!")
                    st.rerun()

    # Active Dataset Full Audit & Introspection Section
    active_df = st.session_state.get("dataset", None)
    if active_df is not None:
        st.markdown("---")
        st.markdown(f"### 📋 Active Dataset: `{st.session_state.get('dataset_source', 'Default')}`")

        # Full Data Reliability Audit
        audit_report = validate_dataset_integrity(active_df)
        score = audit_report["reliability_score"]
        tier = audit_report["confidence_tier"]
        missing_info = detect_missing_values(active_df)
        dupes_info = detect_duplicates(active_df)
        _, date_summary = validate_and_parse_dates(active_df)
        schema_info = inspect_schema(active_df)

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        with m1:
            st.metric("Total Rows", f"{len(active_df):,}")
        with m2:
            st.metric("Total Columns", f"{len(active_df.columns)}")
        with m3:
            st.metric("Memory Usage", f"{schema_info['memory_usage_mb']:.1f} MB")
        with m4:
            st.metric("Reliability Score", f"{score}%", delta="Verified" if audit_report["is_valid"] else "Errors")
        with m5:
            st.metric("Confidence Tier", tier)
        with m6:
            st.metric("Missing Cells", f"{missing_info['overall_missing_pct']}%")

        # Display audit warnings or errors
        if audit_report["critical_errors"]:
            for err in audit_report["critical_errors"]:
                st.error(f"⛔ {err}")
        if audit_report["warnings"]:
            for warn in audit_report["warnings"]:
                st.warning(f"⚠️ {warn}")

        col_audit1, col_audit2 = st.columns(2)
        with col_audit1:
            with st.expander("🔍 Missing Values & Duplicate Records Audit", expanded=True):
                st.markdown(f"- **Total Missing Cells:** {missing_info['total_missing_cells']} ({missing_info['overall_missing_pct']}%)")
                st.markdown(f"- **Exact Duplicate Rows:** {dupes_info['total_duplicate_rows']} ({dupes_info['duplicate_pct']}%)")
                st.markdown(f"- **Duplicate Order IDs:** {dupes_info['id_duplicates']}")

                # Detail of columns with missing values
                cols_with_missing = {k: v for k, v in missing_info["column_missing"].items() if v["missing_count"] > 0}
                if cols_with_missing:
                    st.write("**Columns with Null Values:**")
                    st.json(cols_with_missing)
                else:
                    st.caption("✅ No null or missing values detected in any column.")

        with col_audit2:
            with st.expander("📅 Date Parsing & Financial Integrity Audit", expanded=True):
                if date_summary.get("has_date_column", False):
                    st.markdown(f"- **Date Range:** `{date_summary.get('min_date')}` to `{date_summary.get('max_date')}` ({date_summary.get('date_range_days')} days)")
                    st.markdown(f"- **Valid Parsed Dates:** {date_summary.get('valid_dates_count'):,} records")
                    st.markdown(f"- **Invalid Date Strings:** {date_summary.get('invalid_dates_count')}")
                else:
                    st.caption("ℹ️ No date column detected.")

                fc = audit_report.get("formula_check", {})
                st.markdown(f"- **Revenue Formula Mismatches:** {fc.get('revenue_mismatch_count', 0)}")
                st.markdown(f"- **Cost Formula Mismatches:** {fc.get('cost_mismatch_count', 0)}")
                st.markdown(f"- **Profit Formula Mismatches:** {fc.get('profit_mismatch_count', 0)}")

        with st.expander("📋 Column Details & Inferred Data Types", expanded=False):
            col_types_data = []
            for col in active_df.columns:
                col_types_data.append({
                    "Column Name": col,
                    "Data Type": str(active_df[col].dtype),
                    "Non-Null Count": int(active_df[col].notna().sum()),
                    "Unique Values": int(active_df[col].nunique())
                })
            st.dataframe(pd.DataFrame(col_types_data), use_container_width=True)

        with st.expander("📄 Data Preview (First 20 Rows)", expanded=True):
            st.dataframe(active_df.head(20), use_container_width=True)


def render_investigation_view(orchestrator: MultiAgentOrchestrator):
    """Render Section C: Business Investigation."""
    st.subheader("Business Investigation Hub")
    st.caption("Ask questions about revenue, profit declines, margin erosion, or regional performance.")

    active_df = st.session_state.get("dataset", None)
    if active_df is None or active_df.empty:
        st.warning("Please ensure a valid dataset is loaded before launching an investigation.")
        return

    active_source = st.session_state.get("dataset_source", "Synthetic Benchmark")
    st.info(f"📊 **Target Dataset for Multi-Agent Investigation:** `{active_source}` ({len(active_df):,} records)")

    inv_tab1, inv_tab2 = st.tabs([
        "🤖 Multi-Agent Deep Investigation",
        "💬 ChatGPT-Style AI Investigator"
    ])

    with inv_tab1:
        # Example question chips
        st.markdown("**Sample Business Questions:**")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📉 Why did our profits decrease & what actions should we take?"):
                st.session_state["question_input"] = "Why did our profits decrease, which products or regions contributed most to the decline, and what actions should we take?"
                st.rerun()
        with c2:
            if st.button("📍 Which regions are underperforming and why?"):
                st.session_state["question_input"] = "Which regions are underperforming in profit margin and what is driving the regional disparity?"
                st.rerun()
        with c3:
            if st.button("📦 What are our top and bottom performing products?"):
                st.session_state["question_input"] = "What are our top and bottom performing products by net profit and margin efficiency?"
                st.rerun()

        question = st.text_area(
            "Enter Your Business Question:",
            value=st.session_state.get("question_input", "Why did our profits decrease, which products or regions contributed most to the decline, and what actions should we take?"),
            height=90
        )

        if st.button("🚀 Start Multi-Agent Investigation", type="primary", use_container_width=True):
            st.session_state["investigation_running"] = True
            progress_bar = st.progress(0, text="Initializing Multi-Agent Orchestrator...")
            status_box = st.empty()

            def live_callback(agent_name: str, status: AgentStatus, record):
                status_box.info(f"Agent Active: **{agent_name}** | Status: **{status.value}** | {record.input_summary}")

            try:
                progress_bar.progress(15, text="1/6 Data Reliability Agent auditing dataset...")
                # Run investigation
                res = orchestrator.run_investigation(
                    question=question,
                    df=active_df,
                    status_callback=live_callback
                )
                progress_bar.progress(100, text="Investigation Completed Successfully!")
                st.session_state["investigation_result"] = res
                st.session_state["investigation_running"] = False
                status_box.empty()
                progress_bar.empty()

                if res.success:
                    st.success("Investigation complete! Verified evidence and actionable findings synthesized below.")
                else:
                    st.error(f"Investigation halted: {res.error}")

            except Exception as e:
                st.error(f"Execution Error: {str(e)}")
                st.session_state["investigation_running"] = False

        # If result exists in session state, render immediate summary cards
        res = st.session_state.get("investigation_result", None)
        if res and res.success and res.decision_report:
            st.markdown("---")
            st.markdown("### 🎯 Investigation Highlights")

            col_a, col_b = st.columns([3, 2])
            with col_a:
                st.info(f"**Primary Root Cause:**\n\n{res.findings.primary_driver}")
                st.markdown(f"**Executive Synthesis:**\n\n{res.decision_report.executive_summary}")
            with col_b:
                st.markdown("#### Prioritized Business Issues")
                for issue in res.decision_report.prioritized_issues:
                    st.markdown(f"- **#{issue.rank} {issue.title}** ({issue.severity}): {issue.estimated_impact}")

            st.markdown("#### 💡 Recommended Strategic Actions")
            for rec in res.decision_report.recommendations:
                with st.expander(f"📌 [{rec.id}] {rec.title} ({rec.target_area})", expanded=False):
                    st.markdown(f"**Action Plan:**\n{rec.action_plan}")
                    st.markdown(f"**Justification:** {rec.justification}")
                    st.markdown(f"**Expected Outcome:** `{rec.expected_outcome}`")
                    st.caption(f"Risks & Prerequisites: {rec.risk_and_prerequisites}")

    with inv_tab2:
        st.markdown("### 💬 Conversational AI Business Investigator")
        st.caption("Ask free-form business questions about your active dataset. Powered by the LLM client grounded in verified multi-agent facts.")

        if "chat_messages" not in st.session_state:
            st.session_state["chat_messages"] = [
                {
                    "role": "assistant",
                    "content": (
                        f"Hello! I am your AnalystOS AI Investigator. I'm connected to your active dataset: "
                        f"**{active_source}** ({len(active_df):,} records). "
                        f"Ask me anything about your revenue trajectory, margin compression, category contributions, or regional variances!"
                    )
                }
            ]

        # Display conversation messages
        for msg in st.session_state["chat_messages"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "badge" in msg:
                    st.caption(msg["badge"])

        # Chat input at bottom
        user_prompt = st.chat_input("Ask a question about your dataset (e.g. 'Why did profits decrease in H2?')...", key="chat_user_input")
        if user_prompt:
            st.session_state["chat_messages"].append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)

            with st.chat_message("assistant"):
                with st.spinner("AI Investigator analyzing active dataset and empirical findings..."):
                    from llm.investigator import AIInvestigator
                    investigator = AIInvestigator()
                    chat_res = investigator.chat(
                        message=user_prompt,
                        df=active_df,
                        orchestrator=orchestrator,
                        current_result=st.session_state.get("investigation_result", None),
                        chat_history=st.session_state["chat_messages"]
                    )
                    st.markdown(chat_res["response"])
                    badge_text = f"🤖 Model: {chat_res.get('provider', 'AnalystOS')} ({chat_res.get('model', 'engine')})"
                    st.caption(badge_text)

                    st.session_state["chat_messages"].append({
                        "role": "assistant",
                        "content": chat_res["response"],
                        "badge": badge_text
                    })


def render_analytics_dashboard_view(df: pd.DataFrame):
    """Render Section D: Analytics Dashboard."""
    st.subheader("Analytics Dashboard")
    st.caption("Interactive multi-dimensional financial and operational intelligence.")

    if df is None or df.empty:
        st.warning("No dataset loaded.")
        return

    # Sidebar / in-page filters
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        all_cats = ["All"] + sorted(list(df["Category"].dropna().unique())) if "Category" in df.columns else ["All"]
        selected_cat = st.selectbox("Filter by Category:", all_cats)
    with col_f2:
        all_regs = ["All"] + sorted(list(df["Region"].dropna().unique())) if "Region" in df.columns else ["All"]
        selected_reg = st.selectbox("Filter by Region:", all_regs)

    filtered_df = df.copy()
    if selected_cat != "All":
        filtered_df = filtered_df[filtered_df["Category"] == selected_cat]
    if selected_reg != "All":
        filtered_df = filtered_df[filtered_df["Region"] == selected_reg]

    monthly_df = calculate_monthly_trends(filtered_df)
    cat_df = analyze_category_performance(filtered_df)
    reg_df = analyze_regional_performance(filtered_df)
    prod_perf = analyze_product_performance(filtered_df, top_n=5)

    # Charts Grid
    st.plotly_chart(create_monthly_trend_chart(monthly_df), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(create_category_margin_chart(cat_df), use_container_width=True)
    with c2:
        st.plotly_chart(create_regional_chart(reg_df), use_container_width=True)

    st.plotly_chart(create_product_profit_chart(prod_perf), use_container_width=True)

    # Operational Anomalies & Divergences
    st.markdown("### ⚠️ Operational Anomalies & Divergence Flags")
    anomalies = detect_anomalies_and_changes(filtered_df)
    if anomalies:
        for anom in anomalies:
            sev_color = "#EF4444" if anom["severity"] == "CRITICAL" else ("#F59E0B" if anom["severity"] == "HIGH" else "#3B82F6")
            st.markdown(f"""
            <div style="border-left: 4px solid {sev_color}; background: #F8FAFC; padding: 0.8rem 1rem; margin-bottom: 0.6rem; border-radius: 4px;">
                <b style="color: {sev_color};">[{anom['severity']}] {anom['type']}</b>: {anom['subject']} — <b>{anom['metric']}</b> ({anom['value']})<br>
                <span style="font-size: 0.9rem; color: #475569;">{anom['description']}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No critical statistical anomalies detected in this filtered slice.")


def render_workflow_inspector_view(result: Optional[InvestigationResult]):
    """Render Section E: Multi-Agent Workflow Inspector."""
    st.subheader("Multi-Agent Workflow & Agent Output Inspector")
    st.caption("Inspect the execution state, inputs, outputs, and intermediate evidence across all six specialized agents.")

    # Agent roles definitions
    agents_info = [
        {"id": "reliability", "name": "Data Reliability Agent", "role": "Audits missing values, bounds, and formula integrity without modifying source records."},
        {"id": "planning", "name": "Planning Agent", "role": "Deconstructs business queries into measurable metrics, dimensions, and hypotheses."},
        {"id": "analytics", "name": "Analytics Execution Agent", "role": "Executes deterministic equations for KPIs, monthly trends, and segment metrics."},
        {"id": "investigation", "name": "Business Investigation Agent", "role": "Isolates primary drivers, category shifts, and synthesizes testable claims."},
        {"id": "critic", "name": "Critic / Verification Agent", "role": "Adversarially audits candidate claims against raw facts, rejecting unbacked statements."},
        {"id": "decision", "name": "Decision / Outcome Agent", "role": "Synthesizes verified findings into prioritized issues, actionable plans, and risks."},
    ]

    for a in agents_info:
        name = a["name"]
        rec = result.agent_records.get(name) if result and result.agent_records else None
        status = rec.status.value if rec else "IDLE"
        duration = rec.duration_ms if rec else 0.0
        summary = rec.output_summary if rec else "Not executed yet."
        render_agent_status_card(a["id"], name, a["role"], status, duration, summary)

    if not result or not result.success:
        st.info("Run an investigation in the Business Investigation tab to view detailed agent outputs.")
        return

    st.markdown("---")
    st.markdown("### 🔎 Granular Agent Output Inspector")

    tab_a1, tab_a4, tab_a3, tab_a2, tab_a5, tab_a6 = st.tabs([
        "Agent 1: Plan",
        "Agent 4: Reliability",
        "Agent 3: Analytics",
        "Agent 2: Investigation",
        "Agent 5: Critic Audit",
        "Agent 6: Decision"
    ])

    with tab_a1:
        if result.plan:
            st.markdown(f"**Objective:** {result.plan.objective}")
            st.markdown(f"**Required Metrics:** `{', '.join(result.plan.required_metrics)}`")
            st.markdown(f"**Required Dimensions:** `{', '.join(result.plan.required_dimensions)}`")
            st.markdown("**Analytical Tasks:**")
            for t in result.plan.analytical_tasks:
                st.markdown(f"- {t}")
            st.markdown("**Hypotheses to Test:**")
            for h in result.plan.hypotheses_to_test:
                st.markdown(f"- {h}")

    with tab_a4:
        if result.reliability_report:
            rel = result.reliability_report
            st.markdown(f"**Score:** `{rel.reliability_score}%` | **Tier:** `{rel.confidence_tier}` | **Records:** `{rel.total_records:,}`")
            st.json(rel.audit_summary)

    with tab_a3:
        if result.analytics_result:
            st.markdown("#### Executive KPIs")
            st.json(result.analytics_result.kpis)
            st.markdown("#### Monthly Trajectory Summary")
            st.dataframe(result.analytics_result.monthly_trends, use_container_width=True)

    with tab_a2:
        if result.findings:
            st.markdown(f"**Primary Driver:** {result.findings.primary_driver}")
            st.markdown("#### Candidate Claims Formulated for Critic:")
            for c in result.findings.candidate_claims:
                st.markdown(f"- `{c['claim_type']}`: {c['description']}")

    with tab_a5:
        if result.verification_report:
            vr = result.verification_report
            st.metric("Adversarial Verification Score", f"{vr.verification_score}%", f"{vr.passed_count} passed / {vr.failed_count} rejected")
            st.markdown("#### Mathematically Verified Claims:")
            for p in vr.passed_checks:
                st.success(f"✔ **{p.get('claim', '')}** — {p.get('evidence', '')}")
            if vr.failed_checks:
                st.markdown("#### Rejected Claims:")
                for f in vr.failed_checks:
                    st.error(f"✖ **{f.get('claim', '')}** — {f.get('reason', '')}")

    with tab_a6:
        if result.decision_report:
            st.markdown(f"**Executive Synthesis:**\n{result.decision_report.executive_summary}")
            st.markdown("#### Measured Facts vs Hypotheses:")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Measured Facts:**")
                for fact in result.decision_report.measured_facts:
                    st.markdown(f"- {fact}")
            with c2:
                st.markdown("**Strategic Hypotheses:**")
                for hyp in result.decision_report.hypotheses:
                    st.markdown(f"- {hyp}")


def render_final_report_view(result: Optional[InvestigationResult]):
    """Render Section F: Final Investigation Report."""
    st.subheader("Final Investigation Report")

    if not result or not result.success:
        st.warning("No completed investigation available. Please launch an investigation first.")
        return

    st.markdown(result.markdown_report)


def render_export_view(result: Optional[InvestigationResult], df: pd.DataFrame):
    """Render Section G: Export Center."""
    st.subheader("Export Center")
    st.caption("Download the final investigation report or export analytical data tables.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 📄 Investigation Report Downloads")
        if result and result.success and result.markdown_report:
            st.download_button(
                label="📥 Download Report as Markdown (.md)",
                data=result.markdown_report,
                file_name="AnalystOS_Investigation_Report.md",
                mime="text/markdown",
                use_container_width=True
            )
            st.download_button(
                label="📥 Download Report as Plain Text (.txt)",
                data=result.markdown_report,
                file_name="AnalystOS_Investigation_Report.txt",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.info("Run an investigation to generate the downloadable report.")

    with c2:
        st.markdown("### 📊 Analytical Data Tables Export")
        if df is not None and not df.empty:
            # Generate exports
            monthly_csv = calculate_monthly_trends(df).to_csv(index=False)
            cat_csv = analyze_category_performance(df).to_csv(index=False)
            reg_csv = analyze_regional_performance(df).to_csv(index=False)
            raw_csv = df.to_csv(index=False)

            st.download_button(
                label="📥 Export Monthly Trends (CSV)",
                data=monthly_csv,
                file_name="monthly_trends.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.download_button(
                label="📥 Export Category Performance (CSV)",
                data=cat_csv,
                file_name="category_performance.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.download_button(
                label="📥 Export Regional Performance (CSV)",
                data=reg_csv,
                file_name="regional_performance.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.download_button(
                label="📥 Export Full Active Dataset (CSV)",
                data=raw_csv,
                file_name="analyzed_sales_dataset.csv",
                mime="text/csv",
                use_container_width=True
            )
