"""
Workflow and orchestration module for AnalystOS.
"""

from .types import (
    AgentStatus,
    AgentExecutionRecord,
    InvestigationPlan,
    DataReliabilityReport,
    AnalyticsExecutionResult,
    InvestigationFindings,
    VerificationReport,
    PrioritizedIssue,
    BusinessRecommendation,
    DecisionReport,
    InvestigationResult,
)

__all__ = [
    "MultiAgentOrchestrator",
    "AgentStatus",
    "AgentExecutionRecord",
    "InvestigationPlan",
    "DataReliabilityReport",
    "AnalyticsExecutionResult",
    "InvestigationFindings",
    "VerificationReport",
    "PrioritizedIssue",
    "BusinessRecommendation",
    "DecisionReport",
    "InvestigationResult",
]


def __getattr__(name: str):
    if name == "MultiAgentOrchestrator":
        from .orchestrator import MultiAgentOrchestrator
        return MultiAgentOrchestrator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
