"""
Tools module for AnalystOS.

Provides deterministic data processing, validation, and analytics capabilities
designed for transparent multi-agent investigation.
"""

from .data_tools import (
    load_csv,
    read_csv_with_encoding_fallbacks,
    normalize_dataset_columns,
    inspect_schema,
    detect_missing_values,
    detect_duplicates,
    validate_and_parse_dates,
)
from .validation_tools import (
    validate_dataset_integrity,
    check_numeric_bounds,
    detect_outliers,
)
from .analytics_tools import (
    calculate_kpis,
    calculate_monthly_trends,
    analyze_category_performance,
    analyze_regional_performance,
    analyze_product_performance,
    analyze_customer_segments,
    detect_anomalies_and_changes,
    verify_claim,
)

__all__ = [
    "load_csv",
    "normalize_dataset_columns",
    "inspect_schema",
    "detect_missing_values",
    "detect_duplicates",
    "validate_and_parse_dates",
    "validate_dataset_integrity",
    "check_numeric_bounds",
    "detect_outliers",
    "calculate_kpis",
    "calculate_monthly_trends",
    "analyze_category_performance",
    "analyze_regional_performance",
    "analyze_product_performance",
    "analyze_customer_segments",
    "detect_anomalies_and_changes",
    "verify_claim",
]
