"""
Agent 1: Planning Agent for AnalystOS.

Responsibilities:
- Accept user's business question.
- Identify the core business objective and intent.
- Deconstruct the objective into specific analytical tasks.
- Determine required metrics, dimensions, and comparisons.
- Return a structured InvestigationPlan.
"""

from __future__ import annotations
import re
from typing import List
from workflow.types import InvestigationPlan


class PlanningAgent:
    """
    Deterministic analytical planning agent that translates natural language
    business queries into structured analytical workflows and hypotheses.
    """

    def __init__(self):
        self.name = "Planning Agent"

    def plan(self, question: str) -> InvestigationPlan:
        """
        Deconstruct a user's business question into an actionable investigation plan.
        """
        q_clean = (question or "").strip()
        q_lower = q_clean.lower()

        # Detect primary intent
        if any(w in q_lower for w in ["profit", "margin", "decline", "decrease", "drop", "loss"]):
            objective = "Diagnose the root causes of profit decline or margin compression across categories, regions, and periods."
        elif any(w in q_lower for w in ["region", "territory", "geography", "south", "west", "north", "east"]):
            objective = "Analyze geographic performance disparities and identify regional margin drags."
        elif any(w in q_lower for w in ["product", "item", "sku", "electronics", "furniture", "apparel"]):
            objective = "Evaluate product and category profitability, volume, and unit economics."
        else:
            objective = "Perform holistic multi-dimensional business performance and profitability diagnosis."

        # Determine required metrics
        metrics = ["Revenue", "Cost", "Profit", "Profit Margin (%)", "Order Count", "Average Order Value (AOV)"]
        if "unit" in q_lower or "price" in q_lower or "cost" in q_lower:
            metrics.extend(["Average Unit Price", "Average Unit Cost"])

        # Determine dimensions
        dimensions = ["Time Period (Month/Quarter)", "Product Category", "Product Name", "Region"]
        if "customer" in q_lower or "client" in q_lower:
            dimensions.append("Customer ID")

        # Determine analytical tasks
        tasks = [
            "1. Validate schema, numeric boundaries, and formula consistency via Data Reliability Agent.",
            "2. Compute enterprise baseline KPIs (Revenue, Cost, Profit, Profit Margin, AOV).",
            "3. Conduct time-series trend analysis (monthly aggregates, MoM revenue vs profit trajectory).",
            "4. Perform category-level margin and contribution analysis (identifying margin compression).",
            "5. Execute regional performance benchmarking (isolating low-margin territories).",
            "6. Audit product-level unit economics (pinpointing top profit drivers and loss-making SKUs).",
            "7. Detect operational anomalies (profitless growth periods, pricing/cost shifts).",
            "8. Subject all empirical findings to adversarial review by Critic/Verification Agent.",
            "9. Synthesize verified evidence into prioritized strategic recommendations via Decision Agent."
        ]

        # Hypotheses to empirically test
        hypotheses = [
            "H1: Enterprise profit decline is driven by margin compression (cost inflation or heavy discounting) rather than sales volume decline.",
            "H2: Profit erosion is concentrated in specific product categories (e.g. Electronics) rather than being uniform across all products.",
            "H3: Specific geographical regions (e.g. South) suffer from excessive promotional discounting or higher logistics costs, creating a margin drag.",
            "H4: Q4 holiday revenue expansion created 'profitless growth' where higher sales volume masked collapsing unit profitability."
        ]

        return InvestigationPlan(
            question=q_clean,
            objective=objective,
            required_metrics=metrics,
            required_dimensions=dimensions,
            analytical_tasks=tasks,
            hypotheses_to_test=hypotheses
        )
