"""
Agent 4: Data Reliability Agent for AnalystOS.

Responsibilities:
- Check missing values, duplicates, invalid dates, and schema conformity.
- Detect invalid quantities, negative prices, and anomalous costs.
- Validate internal calculation consistency (Revenue, Cost, Profit formulas).
- Never silently modify the original dataset.
- Report data quality issues and quantify analytical confidence.
"""

from __future__ import annotations
from typing import Any, Dict
import pandas as pd
from tools.data_tools import detect_missing_values, detect_duplicates, validate_and_parse_dates
from tools.validation_tools import validate_dataset_integrity
from workflow.types import DataReliabilityReport


class DataReliabilityAgent:
    """
    Independent data governance and quality verification agent.
    Acts as the defensive gatekeeper ensuring analytics are not run on corrupt data.
    """

    def __init__(self):
        self.name = "Data Reliability Agent"

    def assess_reliability(self, df: pd.DataFrame) -> DataReliabilityReport:
        """
        Conduct thorough, non-destructive audit of dataset integrity and reliability.
        """
        if df is None or df.empty:
            return DataReliabilityReport(
                is_valid=False,
                reliability_score=0.0,
                confidence_tier="INVALID",
                total_records=0,
                critical_errors=["Dataset is completely empty."],
                warnings=[],
                audit_summary={"error": "Empty dataset"}
            )

        # 1. Formula and bounds integrity audit
        integrity = validate_dataset_integrity(df)

        # 2. Missing value audit
        missing = detect_missing_values(df)

        # 3. Duplicate row and key audit
        duplicates = detect_duplicates(df)

        # 4. Date validation
        _, date_summary = validate_and_parse_dates(df)

        critical_errors = list(integrity.get("critical_errors", []))
        warnings = list(integrity.get("warnings", []))
        score = integrity.get("reliability_score", 100.0)

        # Evaluate missing values impact
        if missing["total_missing_cells"] > 0:
            if missing["overall_missing_pct"] > 5.0:
                critical_errors.append(
                    f"Elevated missingness: {missing['total_missing_cells']} cells "
                    f"({missing['overall_missing_pct']}%) are null."
                )
                score -= 15.0
            else:
                warnings.append(
                    f"Minor missingness: {missing['total_missing_cells']} cells "
                    f"({missing['overall_missing_pct']}%) are null."
                )
                score -= 5.0

        # Evaluate duplicate impact
        if duplicates["id_duplicates"] > 0:
            warnings.append(
                f"Found {duplicates['id_duplicates']} duplicate Order IDs. Transactions may be double-counted."
            )
            score -= 5.0

        # Evaluate date audit
        if not date_summary.get("has_date_column", False):
            critical_errors.append("Dataset lacks an 'Order Date' column. Temporal analysis cannot proceed.")
            score -= 20.0
        elif date_summary.get("invalid_dates_count", 0) > 0:
            warnings.append(
                f"Found {date_summary['invalid_dates_count']} unparseable date strings."
            )
            score -= 5.0

        score = max(0.0, round(score, 1))
        is_valid = len(critical_errors) == 0

        if score >= 85.0 and is_valid:
            tier = "HIGH CONFIDENCE"
        elif score >= 60.0:
            tier = "MEDIUM CONFIDENCE"
        else:
            tier = "POOR / COMPROMISED"

        audit_summary = {
            "record_count": len(df),
            "column_count": len(df.columns),
            "formula_check": integrity.get("formula_check", {}),
            "missing_check": missing,
            "duplicate_check": duplicates,
            "date_check": date_summary,
            "outliers": integrity.get("outlier_summary", {})
        }

        return DataReliabilityReport(
            is_valid=is_valid,
            reliability_score=score,
            confidence_tier=tier,
            total_records=len(df),
            critical_errors=critical_errors,
            warnings=warnings,
            audit_summary=audit_summary
        )
