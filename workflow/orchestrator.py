"""
Central Multi-Agent Orchestrator for AnalystOS.

Coordinates the end-to-end investigation pipeline across all six specialized agents:
1. Data Reliability Agent (Audit & Gatekeeping)
2. Planning Agent (Task Decomposition)
3. Analytics Execution Agent (Deterministic Computations)
4. Business Investigation Agent (Root-Cause Synthesis)
5. Critic / Verification Agent (Adversarial Claim Audit)
6. Decision / Outcome Agent (Strategic Action & Impact Prioritization)
"""

from __future__ import annotations
import time
from datetime import datetime
from typing import Callable, Dict, Optional
import pandas as pd

from agents.planning_agent import PlanningAgent
from agents.reliability_agent import DataReliabilityAgent
from agents.analytics_agent import AnalyticsExecutionAgent
from agents.investigation_agent import BusinessInvestigationAgent
from agents.critic_agent import CriticVerificationAgent
from agents.decision_agent import DecisionOutcomeAgent
from workflow.types import (
    AgentStatus,
    AgentExecutionRecord,
    InvestigationPlan,
    DataReliabilityReport,
    AnalyticsExecutionResult,
    InvestigationFindings,
    VerificationReport,
    DecisionReport,
    InvestigationResult,
)


class MultiAgentOrchestrator:
    """
    Coordinates agent communication, manages execution state, handles errors,
    and enforces verification gates between analytical stages.
    """

    def __init__(self):
        self.planning_agent = PlanningAgent()
        self.reliability_agent = DataReliabilityAgent()
        self.analytics_agent = AnalyticsExecutionAgent()
        self.investigation_agent = BusinessInvestigationAgent()
        self.critic_agent = CriticVerificationAgent()
        self.decision_agent = DecisionOutcomeAgent()

    def run_investigation(
        self,
        question: str,
        df: pd.DataFrame,
        status_callback: Optional[Callable[[str, AgentStatus, AgentExecutionRecord], None]] = None
    ) -> InvestigationResult:
        """
        Execute the full multi-agent investigation workflow.

        Parameters:
        - question: User's natural language business query.
        - df: Sales dataset (pandas DataFrame).
        - status_callback: Optional callback receiving (agent_name, status, record) for live UI updates.

        Returns:
        - InvestigationResult: Structured investigation outcome including intermediate outputs and final report.
        """
        start_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        records: Dict[str, AgentExecutionRecord] = {}

        def _update_record(agent_name: str, status: AgentStatus, in_summary: str = "", out_summary: str = "", err: str = None, duration: float = 0.0):
            rec = AgentExecutionRecord(
                agent_name=agent_name,
                status=status,
                start_time=datetime.now().strftime("%H:%M:%S"),
                duration_ms=round(duration * 1000, 2),
                input_summary=in_summary,
                output_summary=out_summary,
                error_message=err
            )
            records[agent_name] = rec
            if status_callback:
                status_callback(agent_name, status, rec)
            return rec

        # Stage 1: Data Reliability Audit
        t0 = time.time()
        agent_name = self.reliability_agent.name
        _update_record(agent_name, AgentStatus.RUNNING, in_summary=f"Audit {len(df) if df is not None else 0} records")
        
        try:
            rel_report: DataReliabilityReport = self.reliability_agent.assess_reliability(df)
            dur = time.time() - t0
            if not rel_report.is_valid:
                _update_record(
                    agent_name,
                    AgentStatus.FAILED,
                    in_summary=f"Audit {len(df)} records",
                    out_summary=f"Integrity check failed: {rel_report.critical_errors[0]}",
                    err="; ".join(rel_report.critical_errors),
                    duration=dur
                )
                return InvestigationResult(
                    question=question,
                    timestamp=start_timestamp,
                    success=False,
                    agent_records=records,
                    reliability_report=rel_report,
                    error=f"Data Reliability Gate Failed: {rel_report.critical_errors[0]}"
                )
            else:
                _update_record(
                    agent_name,
                    AgentStatus.COMPLETED,
                    in_summary=f"Audit {rel_report.total_records} records",
                    out_summary=f"Passed with {rel_report.reliability_score}% score ({rel_report.confidence_tier})",
                    duration=dur
                )
        except Exception as e:
            dur = time.time() - t0
            _update_record(agent_name, AgentStatus.FAILED, err=str(e), duration=dur)
            return InvestigationResult(
                question=question,
                timestamp=start_timestamp,
                success=False,
                agent_records=records,
                error=f"Exception in Data Reliability Agent: {str(e)}"
            )

        # Stage 2: Planning Agent
        t0 = time.time()
        agent_name = self.planning_agent.name
        _update_record(agent_name, AgentStatus.RUNNING, in_summary=question)
        try:
            plan: InvestigationPlan = self.planning_agent.plan(question)
            dur = time.time() - t0
            _update_record(
                agent_name,
                AgentStatus.COMPLETED,
                in_summary=question,
                out_summary=f"Formulated plan with {len(plan.analytical_tasks)} tasks & {len(plan.hypotheses_to_test)} hypotheses",
                duration=dur
            )
        except Exception as e:
            dur = time.time() - t0
            _update_record(agent_name, AgentStatus.FAILED, err=str(e), duration=dur)
            return InvestigationResult(
                question=question,
                timestamp=start_timestamp,
                success=False,
                agent_records=records,
                reliability_report=rel_report,
                error=f"Exception in Planning Agent: {str(e)}"
            )

        # Stage 3: Analytics Execution Agent
        t0 = time.time()
        agent_name = self.analytics_agent.name
        _update_record(agent_name, AgentStatus.RUNNING, in_summary=f"Execute tasks across {len(plan.analytical_tasks)} analytical dimensions")
        try:
            analytics_res: AnalyticsExecutionResult = self.analytics_agent.execute_analytics(df)
            dur = time.time() - t0
            kpis = analytics_res.kpis
            _update_record(
                agent_name,
                AgentStatus.COMPLETED,
                in_summary="Dataset calculation tools",
                out_summary=f"Computed KPIs (Rev: ${kpis['total_revenue']:,.2f}, Profit: ${kpis['total_profit']:,.2f}), {len(analytics_res.monthly_trends)} mo trends, {len(analytics_res.anomalies)} anomalies",
                duration=dur
            )
        except Exception as e:
            dur = time.time() - t0
            _update_record(agent_name, AgentStatus.FAILED, err=str(e), duration=dur)
            return InvestigationResult(
                question=question,
                timestamp=start_timestamp,
                success=False,
                agent_records=records,
                reliability_report=rel_report,
                plan=plan,
                error=f"Exception in Analytics Execution Agent: {str(e)}"
            )

        # Stage 4: Business Investigation Agent
        t0 = time.time()
        agent_name = self.investigation_agent.name
        _update_record(agent_name, AgentStatus.RUNNING, in_summary="Synthesize multi-dimensional analytics")
        try:
            findings: InvestigationFindings = self.investigation_agent.investigate(plan, analytics_res)
            dur = time.time() - t0
            _update_record(
                agent_name,
                AgentStatus.COMPLETED,
                in_summary="Analytics tables and anomalies",
                out_summary=f"Identified primary driver: '{findings.primary_driver[:60]}...' with {len(findings.candidate_claims)} testable claims",
                duration=dur
            )
        except Exception as e:
            dur = time.time() - t0
            _update_record(agent_name, AgentStatus.FAILED, err=str(e), duration=dur)
            return InvestigationResult(
                question=question,
                timestamp=start_timestamp,
                success=False,
                agent_records=records,
                reliability_report=rel_report,
                plan=plan,
                analytics_result=analytics_res,
                error=f"Exception in Business Investigation Agent: {str(e)}"
            )

        # Stage 5: Critic / Verification Agent
        t0 = time.time()
        agent_name = self.critic_agent.name
        _update_record(agent_name, AgentStatus.RUNNING, in_summary=f"Verify {len(findings.candidate_claims)} candidate claims")
        try:
            verification: VerificationReport = self.critic_agent.verify(df, findings, analytics_res)
            dur = time.time() - t0
            _update_record(
                agent_name,
                AgentStatus.COMPLETED,
                in_summary=f"{len(findings.candidate_claims)} claims to audit",
                out_summary=f"Audit complete: {verification.passed_count} passed, {verification.failed_count} rejected ({verification.verification_score}% score)",
                duration=dur
            )
        except Exception as e:
            dur = time.time() - t0
            _update_record(agent_name, AgentStatus.FAILED, err=str(e), duration=dur)
            return InvestigationResult(
                question=question,
                timestamp=start_timestamp,
                success=False,
                agent_records=records,
                reliability_report=rel_report,
                plan=plan,
                analytics_result=analytics_res,
                findings=findings,
                error=f"Exception in Critic / Verification Agent: {str(e)}"
            )

        # Stage 6: Decision / Outcome Agent
        t0 = time.time()
        agent_name = self.decision_agent.name
        _update_record(agent_name, AgentStatus.RUNNING, in_summary="Synthesize verified findings into decisions")
        try:
            decision: DecisionReport = self.decision_agent.decide(plan, analytics_res, findings, verification)
            dur = time.time() - t0
            _update_record(
                agent_name,
                AgentStatus.COMPLETED,
                in_summary="Verified claims & findings",
                out_summary=f"Formulated {len(decision.recommendations)} strategic recommendations and {len(decision.prioritized_issues)} prioritized issues",
                duration=dur
            )
        except Exception as e:
            dur = time.time() - t0
            _update_record(agent_name, AgentStatus.FAILED, err=str(e), duration=dur)
            return InvestigationResult(
                question=question,
                timestamp=start_timestamp,
                success=False,
                agent_records=records,
                reliability_report=rel_report,
                plan=plan,
                analytics_result=analytics_res,
                findings=findings,
                verification_report=verification,
                error=f"Exception in Decision / Outcome Agent: {str(e)}"
            )

        # Compile comprehensive Markdown Report
        markdown_rep = self._generate_markdown_report(
            question=question,
            timestamp=start_timestamp,
            plan=plan,
            reliability=rel_report,
            analytics=analytics_res,
            findings=findings,
            verification=verification,
            decision=decision
        )

        return InvestigationResult(
            question=question,
            timestamp=start_timestamp,
            success=True,
            agent_records=records,
            plan=plan,
            reliability_report=rel_report,
            analytics_result=analytics_res,
            findings=findings,
            verification_report=verification,
            decision_report=decision,
            markdown_report=markdown_rep
        )

    def _generate_markdown_report(
        self,
        question: str,
        timestamp: str,
        plan: InvestigationPlan,
        reliability: DataReliabilityReport,
        analytics: AnalyticsExecutionResult,
        findings: InvestigationFindings,
        verification: VerificationReport,
        decision: DecisionReport
    ) -> str:
        """
        Generate a cohesive, publication-quality business investigation report in Markdown format.
        """
        kpis = analytics.kpis
        cat_df = analytics.category_performance
        reg_df = analytics.regional_performance

        lines = [
            f"# AnalystOS — Business Investigation Report",
            f"**Generated:** {timestamp} | **Reliability Score:** {reliability.reliability_score}% ({reliability.confidence_tier}) | **Verification Score:** {verification.verification_score}%\n",
            f"## 1. Executive Summary",
            f"{decision.executive_summary}\n",
            f"**User Question:** `{question}`  ",
            f"**Primary Root Cause Driver:** {findings.primary_driver}\n",
            f"---",
            f"## 2. Core Business KPIs & Performance Baseline",
            f"- **Total Revenue:** ${kpis.get('total_revenue', 0.0):,.2f}",
            f"- **Total Net Profit:** ${kpis.get('total_profit', 0.0):,.2f}",
            f"- **Overall Profit Margin:** {kpis.get('profit_margin_pct', 0.0)}%",
            f"- **Total Orders:** {kpis.get('total_orders', 0):,}",
            f"- **Average Order Value (AOV):** ${kpis.get('average_order_value', 0.0):,.2f}",
            f"- **Average Profit Per Order:** ${kpis.get('average_profit_per_order', 0.0):,.2f}\n",
            f"---",
            f"## 3. Data Reliability Audit (Agent 4)",
            f"- **Integrity Status:** {'PASSED' if reliability.is_valid else 'FAILED'}",
            f"- **Records Inspected:** {reliability.total_records:,}",
            f"- **Confidence Tier:** {reliability.confidence_tier} ({reliability.reliability_score}/100)",
        ]

        if reliability.critical_errors:
            lines.append(f"- **Critical Errors:** {', '.join(reliability.critical_errors)}")
        if reliability.warnings:
            lines.append("- **Audit Warnings:**")
            for w in reliability.warnings:
                lines.append(f"  - {w}")

        lines.extend([
            f"\n---",
            f"## 4. Multi-Agent Empirical Findings (Agent 2 & Agent 3)",
            f"### Category Profitability Breakdown",
            f"| Category | Revenue ($) | Profit ($) | Profit Margin (%) | Profit Share (%) |",
            f"| :--- | :--- | :--- | :--- | :--- |"
        ])

        if not cat_df.empty:
            for _, r in cat_df.iterrows():
                lines.append(
                    f"| {r['Category']} | ${r['Revenue']:,.2f} | ${r['Profit']:,.2f} | "
                    f"{r['profit_margin_pct']}% | {r.get('profit_share_pct', 0.0)}% |"
                )

        lines.extend([
            f"\n### Regional Performance Breakdown",
            f"| Region | Revenue ($) | Profit ($) | Profit Margin (%) | AOV ($) |",
            f"| :--- | :--- | :--- | :--- | :--- |"
        ])

        if not reg_df.empty:
            for _, r in reg_df.iterrows():
                aov_val = f"${r.get('aov', 0.0):,.2f}" if "aov" in r else "N/A"
                lines.append(
                    f"| {r['Region']} | ${r['Revenue']:,.2f} | ${r['Profit']:,.2f} | "
                    f"{r['profit_margin_pct']}% | {aov_val} |"
                )

        lines.extend([
            f"\n---",
            f"## 5. Adversarial Claim Verification (Agent 5 Critic Report)",
            f"- **Claims Evaluated:** {verification.total_claims_checked}",
            f"- **Claims Mathematically Verified:** {verification.passed_count}",
            f"- **Claims Rejected:** {verification.failed_count}",
            f"- **Verification Pass Rate:** {verification.verification_score}%\n",
            f"**Verified Evidence Points:**"
        ])

        for c in verification.passed_checks:
            lines.append(f"- [PASSED] **{c.get('claim', '')}** — {c.get('evidence', '')}")

        if verification.failed_checks:
            lines.append("\n**Rejected Assertions:**")
            for f in verification.failed_checks:
                lines.append(f"- [REJECTED] **{f.get('claim', '')}** — {f.get('reason', '')}")

        lines.extend([
            f"\n---",
            f"## 6. Prioritized Business Issues & Strategic Recommendations (Agent 6)",
            f"### Prioritized Issues by Financial Severity"
        ])

        for issue in decision.prioritized_issues:
            lines.append(
                f"**#{issue.rank}. {issue.title}** [{issue.severity} Severity]\n"
                f"- **Financial Impact:** {issue.estimated_impact}\n"
                f"- **Root Cause:** {issue.root_cause}\n"
                f"- **Empirical Evidence:** {issue.evidence}\n"
            )

        lines.append("### Recommended Action Plans")
        for rec in decision.recommendations:
            lines.append(
                f"#### [{rec.id}] {rec.title}\n"
                f"- **Target Area:** {rec.target_area}\n"
                f"- **Action Plan:**\n{rec.action_plan}\n"
                f"- **Justification:** {rec.justification}\n"
                f"- **Expected Outcome:** {rec.expected_outcome}\n"
                f"- **Risks & Prerequisites:** {rec.risk_and_prerequisites}\n"
            )

        lines.extend([
            f"---",
            f"## 7. Measured Facts vs Hypotheses & Methodological Limitations",
            f"### Measured Empirical Facts"
        ])
        for fact in decision.measured_facts:
            lines.append(f"- {fact}")

        lines.append("\n### Strategic Hypotheses (Subject to Future Testing)")
        for hyp in decision.hypotheses:
            lines.append(f"- {hyp}")

        lines.append("\n### Methodological Limitations")
        for lim in decision.limitations:
            lines.append(f"- {lim}")

        lines.append("\n### Suggested Next Steps")
        for step in decision.suggested_next_steps:
            lines.append(f"- {step}")

        lines.append("\n---\n*Report generated by AnalystOS Multi-Agent AI Business Investigation System.*")

        return "\n".join(lines)
