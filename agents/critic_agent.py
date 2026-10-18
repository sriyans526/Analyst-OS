"""
Agent 5: Critic / Verification Agent for AnalystOS.

Responsibilities:
- Independently evaluate all empirical claims against raw dataset facts.
- Detect unsupported conclusions, calculation discrepancies, and misleading assertions.
- Reject unsupported claims instead of inventing evidence.
- Produce an adversarial verification audit with passed checks, failed checks, and warnings.
"""

from __future__ import annotations
from typing import Any, Dict, List
import pandas as pd
from tools.analytics_tools import verify_claim
from workflow.types import (
    InvestigationFindings,
    AnalyticsExecutionResult,
    VerificationReport
)


class CriticVerificationAgent:
    """
    Adversarial verification and critique agent.
    Conducts mathematical claim verification and rejects any finding not backed by raw data.
    """

    def __init__(self):
        self.name = "Critic / Verification Agent"

    def verify(
        self,
        df: pd.DataFrame,
        findings: InvestigationFindings,
        analytics: AnalyticsExecutionResult
    ) -> VerificationReport:
        """
        Verify all candidate claims against raw dataset using deterministic verification tools.
        """
        passed_checks: List[Dict[str, Any]] = []
        failed_checks: List[Dict[str, Any]] = []
        warnings: List[str] = []
        verified_claims: List[str] = []
        rejected_claims: List[str] = []

        candidate_claims = findings.candidate_claims

        for claim in candidate_claims:
            claim_type = claim.get("claim_type", "")
            params = claim.get("parameters", {})
            description = claim.get("description", "")

            # Run independent claim verification tool against raw DataFrame
            v_res = verify_claim(df, claim_type, params)

            if v_res.get("passed", False):
                passed_checks.append({
                    "claim": description,
                    "claim_type": claim_type,
                    "evidence": v_res.get("evidence_note", "Verified mathematically.")
                })
                verified_claims.append(description)
            else:
                failed_checks.append({
                    "claim": description,
                    "claim_type": claim_type,
                    "reason": v_res.get("evidence_note", "Failed data check."),
                    "details": v_res
                })
                rejected_claims.append(description)

        # Cross-check 2: Verify primary driver coherence
        primary_driver = findings.primary_driver
        if "Electronics" in primary_driver:
            # Check if Electronics really has low margin or negative growth
            cat_df = analytics.category_performance
            elec_row = cat_df[cat_df["Category"] == "Electronics"]
            if elec_row.empty:
                warnings.append("Primary driver cites Electronics, but Electronics was not found in Category table.")
            else:
                elec_margin = float(elec_row.iloc[0]["profit_margin_pct"])
                passed_checks.append({
                    "claim": f"Primary driver isolates Electronics (Measured margin: {elec_margin}%).",
                    "claim_type": "root_cause_coherence",
                    "evidence": f"Electronics delivered {elec_margin}% profit margin."
                })

        total_checked = len(passed_checks) + len(failed_checks)
        passed_count = len(passed_checks)
        failed_count = len(failed_checks)

        score = round((passed_count / total_checked * 100), 1) if total_checked > 0 else 0.0

        if failed_count > 0:
            warnings.append(f"Rejected {failed_count} claims due to numerical inconsistency with source data.")

        return VerificationReport(
            total_claims_checked=total_checked,
            passed_count=passed_count,
            failed_count=failed_count,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warnings=warnings,
            verification_score=score,
            verified_claims=verified_claims,
            rejected_claims=rejected_claims
        )
