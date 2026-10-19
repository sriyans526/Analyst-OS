"""
Unit tests for PDF report generation in AnalystOS.
"""

import pytest
import pandas as pd
from tools.ingest import get_synthetic_artifact
from workflow.orchestrator import MultiAgentOrchestrator
from reports.pdf_generator import (
    generate_investigation_report,
    generate_dashboard_report,
    _generate_pure_python_pdf_fallback
)


@pytest.fixture
def synthetic_data():
    return get_synthetic_artifact(num_records=2000, seed=42)


def test_generate_investigation_report_returns_valid_pdf(synthetic_data):
    orchestrator = MultiAgentOrchestrator()
    question = "Why did our profits decrease and what actions should we take?"
    inv_result = orchestrator.run_investigation(question, synthetic_data.dataframe)

    pdf_bytes = generate_investigation_report(inv_result, synthetic_data, question)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 200
    # Must start with standard PDF magic header
    assert pdf_bytes.startswith(b"%PDF-")
    # Must never be a renamed markdown or text string
    assert not pdf_bytes.startswith(b"# ")


def test_generate_dashboard_report_returns_valid_pdf(synthetic_data):
    kpis = {
        "total_revenue": 500000.0,
        "total_profit": 120000.0,
        "profit_margin_pct": 24.0,
        "total_orders": 3000,
        "average_order_value": 166.67
    }
    analytics_payload = {
        "kpis": kpis,
        "category_performance": pd.DataFrame({
            "Category": ["Electronics", "Furniture"],
            "Revenue": [300000.0, 200000.0],
            "Profit": [50000.0, 70000.0],
            "profit_margin_pct": [16.7, 35.0]
        })
    }
    pdf_bytes = generate_dashboard_report(analytics_payload, synthetic_data, filters={"Region": "South"})

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 200
    assert pdf_bytes.startswith(b"%PDF-")


def test_pure_python_pdf_fallback_structure():
    sections = [
        {"title": "Section 1", "body": "This is test line 1\nThis is test line 2"},
        {"title": "Section 2", "body": "Summary findings and data points."}
    ]
    raw_pdf = _generate_pure_python_pdf_fallback("Test Document Title", sections)

    assert isinstance(raw_pdf, bytes)
    assert raw_pdf.startswith(b"%PDF-1.4")
    assert b"%%EOF" in raw_pdf
    assert b"xref" in raw_pdf
    assert b"trailer" in raw_pdf
