"""
Automated tests for central MultiAgentOrchestrator and end-to-end pipeline execution.
"""

import io
import pytest
import pandas as pd
from workflow.orchestrator import MultiAgentOrchestrator
from workflow.types import AgentStatus
from tools.data_tools import load_csv
from data.data_generator import generate_ecommerce_dataset


@pytest.fixture
def clean_dataset():
    return generate_ecommerce_dataset(num_records=2100, seed=42)


def test_orchestrator_end_to_end_success(clean_dataset):
    orchestrator = MultiAgentOrchestrator()
    question = "Why did our profits decrease, which products or regions contributed most to the decline, and what actions should we take?"

    callback_events = []
    def callback(name, status, record):
        callback_events.append((name, status))

    result = orchestrator.run_investigation(question, clean_dataset, status_callback=callback)

    assert result.success is True
    assert result.question == question
    assert result.plan is not None
    assert result.reliability_report is not None
    assert result.analytics_result is not None
    assert result.findings is not None
    assert result.verification_report is not None
    assert result.decision_report is not None
    assert len(result.markdown_report) > 200

    # Verify all 6 agents completed
    expected_agents = [
        "Data Reliability Agent",
        "Planning Agent",
        "Analytics Execution Agent",
        "Business Investigation Agent",
        "Critic / Verification Agent",
        "Decision / Outcome Agent"
    ]
    for agent_name in expected_agents:
        assert agent_name in result.agent_records
        assert result.agent_records[agent_name].status == AgentStatus.COMPLETED
        assert result.agent_records[agent_name].duration_ms >= 0

    assert len(callback_events) > 0


def test_orchestrator_with_uploaded_custom_csv():
    """
    Verify that an uploaded custom CSV with its own unique figures
    is the exact data analyzed and cited by the agents.
    """
    custom_csv = (
        "Order ID,Order Date,Product ID,Product Name,Category,Quantity,Unit Price,Unit Cost,Revenue,Cost,Profit,Region\n"
        "ORD-C01,2023-03-01,P1,Custom Solar Power Bank,Electronics,10,100.0,60.0,1000.0,600.0,400.0,North\n"
        "ORD-C02,2023-04-01,P2,Custom Standing Desk,Furniture,5,200.0,120.0,1000.0,600.0,400.0,South\n"
        "ORD-C03,2023-05-01,P1,Custom Solar Power Bank,Electronics,8,90.0,70.0,720.0,560.0,160.0,East\n"
    )
    buffer = io.StringIO(custom_csv)
    uploaded_df = load_csv(buffer, auto_normalize=True)

    orchestrator = MultiAgentOrchestrator()
    result = orchestrator.run_investigation("Analyze custom uploaded sales", uploaded_df)

    assert result.success is True
    # Verify calculated totals match the uploaded dataset exactly
    expected_total_rev = 2720.0  # 1000 + 1000 + 720
    expected_total_profit = 960.0  # 400 + 400 + 160
    assert result.analytics_result.kpis["total_revenue"] == expected_total_rev
    assert result.analytics_result.kpis["total_profit"] == expected_total_profit
    # Verify the report cites the exact uploaded revenue
    assert "$2,720.00" in result.markdown_report


def test_orchestrator_stops_on_corrupt_data():
    orchestrator = MultiAgentOrchestrator()
    # Create corrupted dataset with formula mismatch
    corrupt_df = pd.DataFrame({
        "Order ID": ["ORD-1"],
        "Order Date": ["2023-01-01"],
        "Product ID": ["P1"],
        "Product Name": ["Item"],
        "Category": ["Electronics"],
        "Quantity": [1],
        "Unit Price": [10.0],
        "Unit Cost": [5.0],
        "Revenue": [9999.0],  # blatant mismatch
        "Cost": [5.0],
        "Profit": [10.0],
    })

    result = orchestrator.run_investigation("Analyze this data", corrupt_df)

    assert result.success is False
    assert "Data Reliability Gate Failed" in result.error
    assert result.agent_records["Data Reliability Agent"].status == AgentStatus.FAILED
    # Downstream agents should not have run
    assert "Planning Agent" not in result.agent_records
    assert result.decision_report is None


def test_orchestrator_stops_on_empty_dataset():
    orchestrator = MultiAgentOrchestrator()
    result = orchestrator.run_investigation("Analyze this", pd.DataFrame())

    assert result.success is False
    assert "Data Reliability Gate Failed" in result.error
