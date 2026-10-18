"""
Data structures and communication schemas for AnalystOS multi-agent workflow.

Defines typed dataclasses for strict, verifiable inter-agent contracts.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import pandas as pd


class AgentStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class AgentExecutionRecord:
    agent_name: str
    status: AgentStatus = AgentStatus.IDLE
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_ms: float = 0.0
    input_summary: str = ""
    output_summary: str = ""
    error_message: Optional[str] = None


@dataclass
class InvestigationPlan:
    question: str
    objective: str
    required_metrics: List[str]
    required_dimensions: List[str]
    analytical_tasks: List[str]
    hypotheses_to_test: List[str]


@dataclass
class DataReliabilityReport:
    is_valid: bool
    reliability_score: float
    confidence_tier: str
    total_records: int
    critical_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    audit_summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyticsExecutionResult:
    kpis: Dict[str, Any]
    monthly_trends: pd.DataFrame
    category_performance: pd.DataFrame
    regional_performance: pd.DataFrame
    product_performance: Dict[str, pd.DataFrame]
    customer_segments: Dict[str, Any]
    anomalies: List[Dict[str, Any]]


@dataclass
class InvestigationFindings:
    primary_driver: str
    category_findings: List[Dict[str, Any]]
    regional_findings: List[Dict[str, Any]]
    temporal_findings: List[Dict[str, Any]]
    product_findings: List[Dict[str, Any]]
    candidate_claims: List[Dict[str, Any]]


@dataclass
class VerificationReport:
    total_claims_checked: int
    passed_count: int
    failed_count: int
    passed_checks: List[Dict[str, Any]]
    failed_checks: List[Dict[str, Any]]
    warnings: List[str]
    verification_score: float
    verified_claims: List[str]
    rejected_claims: List[str]


@dataclass
class PrioritizedIssue:
    rank: int
    title: str
    severity: str  # HIGH, MEDIUM, LOW
    estimated_impact: str
    root_cause: str
    evidence: str


@dataclass
class BusinessRecommendation:
    id: str
    title: str
    target_area: str
    action_plan: str
    justification: str
    expected_outcome: str
    supporting_metrics: List[str]
    risk_and_prerequisites: str


@dataclass
class DecisionReport:
    executive_summary: str
    prioritized_issues: List[PrioritizedIssue]
    recommendations: List[BusinessRecommendation]
    measured_facts: List[str]
    hypotheses: List[str]
    limitations: List[str]
    suggested_next_steps: List[str]


@dataclass
class InvestigationResult:
    question: str
    timestamp: str
    success: bool
    agent_records: Dict[str, AgentExecutionRecord]
    plan: Optional[InvestigationPlan] = None
    reliability_report: Optional[DataReliabilityReport] = None
    analytics_result: Optional[AnalyticsExecutionResult] = None
    findings: Optional[InvestigationFindings] = None
    verification_report: Optional[VerificationReport] = None
    decision_report: Optional[DecisionReport] = None
    markdown_report: str = ""
    error: Optional[str] = None
