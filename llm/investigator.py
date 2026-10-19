"""
ChatGPT-style AI Investigator for AnalystOS.

Orchestrates conversational queries against the active dataset, grounding all
AI responses in mathematically verified multi-agent calculations.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import pandas as pd

from llm.client import LLMClient
from workflow.orchestrator import MultiAgentOrchestrator
from workflow.types import InvestigationResult
from tools.analytics_tools import calculate_kpis, calculate_monthly_trends, analyze_category_performance


class AIInvestigator:
    """
    Conversational AI business investigator that bridges natural language questions
    with deterministic multi-agent investigation evidence.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.client = llm_client or LLMClient()

    def chat(
        self,
        message: str,
        df: pd.DataFrame,
        orchestrator: MultiAgentOrchestrator,
        current_result: Optional[InvestigationResult] = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process a conversational user message, compute or retrieve empirical evidence,
        and generate a verified response.
        """
        if df is None or df.empty:
            return {
                "response": "No dataset is currently loaded. Please upload a dataset or load the benchmark dataset in the Data Workspace to begin our investigation.",
                "provider": "AnalystOS System",
                "model": "offline",
                "is_real_llm": False
            }

        # 1. Build empirical data context
        kpis = calculate_kpis(df)
        cat_df = analyze_category_performance(df)
        monthly_df = calculate_monthly_trends(df)

        context_lines = []
        if kpis.get("has_revenue"):
            context_lines.append(f"- Total Revenue: ${kpis.get('total_revenue', 0.0):,.2f}")
            context_lines.append(f"- Average Order Value: ${kpis.get('average_order_value', 0.0):,.2f}")
        else:
            context_lines.append("- Total Revenue: Unavailable (Revenue column not mapped)")

        if kpis.get("has_profit"):
            context_lines.append(f"- Total Net Profit: ${kpis.get('total_profit', 0.0):,.2f}")
            context_lines.append(f"- Overall Profit Margin: {kpis.get('profit_margin_pct', 0.0)}%")
        else:
            context_lines.append("- Total Net Profit: Unavailable (Profit/Cost columns not mapped)")

        context_lines.append(f"- Total Orders / Transactions: {kpis.get('total_orders', 0):,}")

        if not cat_df.empty:
            context_lines.append("\nCategory Breakdown:")
            for _, r in cat_df.head(4).iterrows():
                context_lines.append(
                    f"  * {r['Category']}: Revenue=${r['Revenue']:,.2f}, Profit=${r['Profit']:,.2f}, Margin={r['profit_margin_pct']}%"
                )

        # Include existing multi-agent investigation results if already computed
        if current_result and current_result.success:
            if current_result.findings:
                context_lines.append(f"\nPrimary Root Cause Driver:\n{current_result.findings.primary_driver}")
            if current_result.verification_report:
                vr = current_result.verification_report
                context_lines.append(f"\nAdversarial Verification Audit: {vr.passed_count} passed, {vr.failed_count} rejected.")
                for p in vr.passed_checks[:3]:
                    context_lines.append(f"  * [VERIFIED] {p.get('claim', '')}")
            if current_result.decision_report:
                context_lines.append("\nTop Prioritized Recommendations:")
                for rec in current_result.decision_report.recommendations[:2]:
                    context_lines.append(f"  * [{rec.id}] {rec.title}: {rec.expected_outcome}")

        empirical_context = "\n".join(context_lines)

        # 2. System instruction ensuring strict empirical grounding
        system_instruction = (
            "You are AnalystOS AI Investigator. Provide a concise, structured, and insightful answer to the user. "
            "Use the verified dataset metrics provided above. Never invent or hallucinate financial figures. "
            "Highlight specific numbers and explain the business rationale clearly."
        )

        gen_result = self.client.generate(
            prompt=message,
            system_instruction=system_instruction,
            context=empirical_context
        )

        return {
            "response": gen_result["text"],
            "provider": gen_result.get("provider", "AnalystOS"),
            "model": gen_result.get("model", "engine"),
            "is_real_llm": gen_result.get("is_real_llm", False),
            "empirical_kpis": kpis
        }
