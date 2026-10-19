"""
Unit tests for session state management and reset investigation logic in AnalystOS.
"""

import uuid
from unittest.mock import patch
import streamlit as st
from app import (
    reset_investigation,
    KEY_ACTIVE_ARTIFACT,
    KEY_CHAT_HISTORY,
    KEY_INVESTIGATION_RESULT,
    KEY_CURRENT_INV_ID,
    KEY_CHART_SPECS,
    KEY_REPORT_BYTES,
    KEY_LLM_API_KEY,
)
from tools.ingest import get_synthetic_artifact


def test_reset_investigation_clears_expected_keys():
    old_inv_id = str(uuid.uuid4())
    synth_artifact = get_synthetic_artifact(num_records=2000)

    mock_state = {
        KEY_ACTIVE_ARTIFACT: synth_artifact,
        "dataset": synth_artifact.dataframe,
        KEY_LLM_API_KEY: "test-key-12345",
        KEY_CURRENT_INV_ID: old_inv_id,
        KEY_CHAT_HISTORY: [{"role": "user", "content": "What was our margin?"}],
        KEY_INVESTIGATION_RESULT: "mock_result",
        KEY_CHART_SPECS: [{"type": "monthly_trend"}],
        KEY_REPORT_BYTES: b"%PDF-1.4",
    }

    with patch("app.st.session_state", mock_state):
        # Execute reset
        reset_investigation()

        # Verify cleared keys
        assert KEY_CHAT_HISTORY not in mock_state
        assert KEY_INVESTIGATION_RESULT not in mock_state
        assert KEY_CHART_SPECS not in mock_state
        assert KEY_REPORT_BYTES not in mock_state

        # Verify new investigation ID was generated
        assert KEY_CURRENT_INV_ID in mock_state
        assert mock_state[KEY_CURRENT_INV_ID] != old_inv_id

        # Verify preserved keys
        assert KEY_ACTIVE_ARTIFACT in mock_state
        assert mock_state[KEY_ACTIVE_ARTIFACT] == synth_artifact
        assert mock_state["dataset"] is not None
        assert mock_state[KEY_LLM_API_KEY] == "test-key-12345"
