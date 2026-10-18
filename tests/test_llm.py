"""
Automated tests for LLM client and AI Investigator.
"""

import pytest
import pandas as pd
from llm.client import LLMClient
from llm.investigator import AIInvestigator
from workflow.orchestrator import MultiAgentOrchestrator
from data.data_generator import generate_ecommerce_dataset


@pytest.fixture
def sample_dataset():
    return generate_ecommerce_dataset(num_records=2000, seed=42)


def test_llm_client_initialization_offline():
    # When no key is provided, should initialize in offline analytical mode
    client = LLMClient(api_key=None)
    assert client.provider in ["offline", "auto", "gemini"]
    res = client.generate(prompt="What are our top revenue drivers?")
    assert res["text"] is not None
    assert len(res["text"]) > 20
    assert "is_real_llm" in res


def test_llm_client_with_context():
    client = LLMClient(api_key=None)
    context = "- Total Revenue: $500,000\n- Net Profit: $150,000\n- Margin: 30%"
    res = client.generate(prompt="Summarize our financial performance", context=context)
    assert "$500,000" in res["text"] or "500,000" in res["text"]


def test_ai_investigator_chat_flow(sample_dataset):
    orchestrator = MultiAgentOrchestrator()
    investigator = AIInvestigator()
    chat_res = investigator.chat(
        message="Why did profits decline?",
        df=sample_dataset,
        orchestrator=orchestrator
    )
    assert "response" in chat_res
    assert len(chat_res["response"]) > 50
    assert "empirical_kpis" in chat_res
    assert chat_res["empirical_kpis"]["total_revenue"] > 0


def test_ai_investigator_empty_dataset():
    orchestrator = MultiAgentOrchestrator()
    investigator = AIInvestigator()
    chat_res = investigator.chat(
        message="What is our margin?",
        df=pd.DataFrame(),
        orchestrator=orchestrator
    )
    assert "No dataset is currently loaded" in chat_res["response"]
