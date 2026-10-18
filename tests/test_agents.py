"""
Automated tests for all six individual agents in AnalystOS.
"""

import pytest
import pandas as pd
from agents.planning_agent import PlanningAgent
from agents.reliability_agent import DataReliabilityAgent
from agents.analytics_agent import AnalyticsExecutionAgent
from agents.investigation_agent import BusinessInvestigationAgent
from agents.critic_agent import CriticVerificationAgent
from agents.decision_agent import DecisionOutcomeAgent
from data.data_generator import generate_ecommerce_dataset


@pytest.fixture
def test_dataset():
    return generate_ecommerce_dataset(num_records=2200, seed=42)


def test_planning_agent():
    agent = PlanningAgent()
    plan = agent.plan("Why did our profits decrease in Electronics and what actions should we take?")
    assert plan.question is not None
    assert "profit" in plan.objective.lower() or "margin" in plan.objective.lower()
    assert "Revenue" in plan.required_metrics
    assert "Profit Margin (%)" in plan.required_metrics
    assert len(plan.analytical_tasks) >= 5
    assert len(plan.hypotheses_to_test) >= 2


def test_reliability_agent_valid(test_dataset):
    agent = DataReliabilityAgent()
    report = agent.assess_reliability(test_dataset)
    assert report.is_valid is True
    assert report.reliability_score >= 85.0
    assert report.confidence_tier == "HIGH CONFIDENCE"
    assert len(report.critical_errors) == 0


def test_reliability_agent_invalid():
    agent = DataReliabilityAgent()
    empty_df = pd.DataFrame()
    report = agent.assess_reliability(empty_df)
    assert report.is_valid is False
    assert report.reliability_score == 0.0
    assert len(report.critical_errors) > 0


def test_analytics_agent(test_dataset):
    agent = AnalyticsExecutionAgent()
    result = agent.execute_analytics(test_dataset)
    assert result.kpis["total_revenue"] > 0
    assert result.kpis["total_profit"] > 0
    assert not result.monthly_trends.empty
    assert not result.category_performance.empty
    assert not result.regional_performance.empty
    assert "top_profit" in result.product_performance
    assert result.customer_segments["total_customers"] > 0


def test_investigation_agent(test_dataset):
    plan_agent = PlanningAgent()
    plan = plan_agent.plan("Why did profits decrease?")
    analytics_agent = AnalyticsExecutionAgent()
    analytics_res = analytics_agent.execute_analytics(test_dataset)

    investigation_agent = BusinessInvestigationAgent()
    findings = investigation_agent.investigate(plan, analytics_res)

    assert findings.primary_driver is not None
    assert len(findings.category_findings) > 0
    assert len(findings.regional_findings) > 0
    assert len(findings.candidate_claims) >= 2


def test_critic_agent(test_dataset):
    plan_agent = PlanningAgent()
    plan = plan_agent.plan("Why did profits drop?")
    analytics_agent = AnalyticsExecutionAgent()
    analytics_res = analytics_agent.execute_analytics(test_dataset)
    investigation_agent = BusinessInvestigationAgent()
    findings = investigation_agent.investigate(plan, analytics_res)

    critic = CriticVerificationAgent()
    v_report = critic.verify(test_dataset, findings, analytics_res)

    assert v_report.total_claims_checked > 0
    assert v_report.passed_count > 0
    assert v_report.verification_score > 70.0
    assert len(v_report.verified_claims) > 0


def test_decision_agent(test_dataset):
    plan_agent = PlanningAgent()
    plan = plan_agent.plan("What actions should we take to restore profitability?")
    analytics_agent = AnalyticsExecutionAgent()
    analytics_res = analytics_agent.execute_analytics(test_dataset)
    investigation_agent = BusinessInvestigationAgent()
    findings = investigation_agent.investigate(plan, analytics_res)
    critic = CriticVerificationAgent()
    v_report = critic.verify(test_dataset, findings, analytics_res)

    decision_agent = DecisionOutcomeAgent()
    decision = decision_agent.decide(plan, analytics_res, findings, v_report)

    assert len(decision.executive_summary) > 50
    assert len(decision.prioritized_issues) >= 2
    assert len(decision.recommendations) >= 2
    assert len(decision.measured_facts) >= 3
    assert len(decision.hypotheses) >= 1
    assert len(decision.limitations) >= 1
    assert len(decision.suggested_next_steps) >= 1
