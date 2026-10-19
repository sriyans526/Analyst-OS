"""
LLM Client for AnalystOS.

Supports real LLM providers (Google Gemini, OpenAI, Groq) via standard REST APIs,
with seamless fallback to deterministic reasoning when no API key is configured.
Reads keys from Streamlit secrets (st.secrets), environment variables (.env),
or runtime session configuration.
"""

from __future__ import annotations
import os
from typing import Any, Dict, Optional
import requests
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()


class LLMClient:
    """
    Unified client for calling LLMs with verified empirical grounding.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "auto")).lower()
        self.api_key = api_key or self._resolve_api_key()
        self.model = model
        self._detect_provider_and_model()

    def _resolve_api_key(self) -> Optional[str]:
        """Check Streamlit secrets, environment variables, or session state."""
        # 1. Try Streamlit secrets safely
        try:
            import streamlit as st
            if hasattr(st, "secrets"):
                if "GEMINI_API_KEY" in st.secrets:
                    return st.secrets["GEMINI_API_KEY"]
                if "OPENAI_API_KEY" in st.secrets:
                    return st.secrets["OPENAI_API_KEY"]
                if "GROQ_API_KEY" in st.secrets:
                    return st.secrets["GROQ_API_KEY"]
            if hasattr(st, "session_state") and "custom_llm_api_key" in st.session_state:
                if st.session_state["custom_llm_api_key"]:
                    return st.session_state["custom_llm_api_key"]
        except Exception:
            pass

        # 2. Try OS environment variables
        return (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("GROQ_API_KEY")
        )

    def _detect_provider_and_model(self):
        """Auto-detect provider based on available key or explicit setting."""
        if not self.api_key:
            self.provider = "offline"
            self.model = "deterministic-engine"
            return

        # Explicit provider override — honour it directly
        if self.provider == "gemini":
            self.model = self.model or "gemini-1.5-flash"
            return
        if self.provider == "groq":
            self.model = self.model or "llama-3.1-70b-versatile"
            return
        if self.provider == "openai":
            self.model = self.model or "gpt-4o-mini"
            return

        # Auto-detect: prefer env-var hints, then fall back by key prefix heuristics
        if os.getenv("GEMINI_API_KEY"):
            self.provider = "gemini"
            self.model = self.model or "gemini-1.5-flash"
        elif os.getenv("GROQ_API_KEY"):
            self.provider = "groq"
            self.model = self.model or "llama-3.1-70b-versatile"
        elif os.getenv("OPENAI_API_KEY"):
            self.provider = "openai"
            self.model = self.model or "gpt-4o-mini"
        else:
            # Key came from session_state or Streamlit secrets — detect by prefix
            key = self.api_key or ""
            if key.startswith("sk-") and "-" in key[3:8]:
                # OpenAI keys start with "sk-"
                self.provider = "openai"
                self.model = self.model or "gpt-4o-mini"
            elif key.startswith("gsk_"):
                # Groq keys start with "gsk_"
                self.provider = "groq"
                self.model = self.model or "llama-3.1-70b-versatile"
            else:
                # Default: treat as Gemini (Google AI Studio keys have no fixed prefix)
                self.provider = "gemini"
                self.model = self.model or "gemini-1.5-flash"

    @property
    def is_configured(self) -> bool:
        """Return True if a live cloud LLM key is configured."""
        return bool(self.api_key and self.provider != "offline")

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a response using the configured LLM or the deterministic engine fallback.
        """
        full_system = (
            "You are AnalystOS AI Investigator, an expert enterprise analytics and business intelligence assistant. "
            "You provide evidence-backed, mathematically verified diagnoses of revenue, profit, and operational performance. "
            "Always cite specific numbers, percentages, and category/regional trends from the provided verified evidence. "
            "Clearly distinguish measured facts from hypotheses."
        )
        if system_instruction:
            full_system = f"{full_system}\n\n{system_instruction}"

        if context:
            full_prompt = f"VERIFIED ANALYTICAL CONTEXT FROM ACTIVE DATASET:\n{context}\n\nUSER QUESTION / REQUEST:\n{prompt}"
        else:
            full_prompt = prompt

        if not self.is_configured:
            return {
                "text": self._offline_fallback(prompt, context),
                "provider": "AnalystOS Deterministic Engine",
                "model": "offline-analytical-mode",
                "is_real_llm": False
            }

        try:
            if self.provider == "gemini":
                return self._call_gemini(full_prompt, full_system)
            elif self.provider in ["openai", "groq"]:
                return self._call_openai_compatible(full_prompt, full_system)
            else:
                return {
                    "text": self._offline_fallback(prompt, context),
                    "provider": "AnalystOS Deterministic Engine",
                    "model": "offline-analytical-mode",
                    "is_real_llm": False
                }
        except Exception as e:
            # Graceful fallback on API failure or network issue
            fallback_text = self._offline_fallback(prompt, context)
            return {
                "text": f"{fallback_text}\n\n*(Note: Cloud LLM call encountered: {str(e)}. Switched to deterministic analytical engine.)*",
                "provider": f"{self.provider} (Fallback)",
                "model": self.model,
                "is_real_llm": False,
                "error": str(e)
            }

    def _call_gemini(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        """Call Google Gemini REST API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048
            }
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return {
            "text": text,
            "provider": "Google Gemini",
            "model": self.model,
            "is_real_llm": True
        }

    def _call_openai_compatible(self, prompt: str, system_instruction: str) -> Dict[str, Any]:
        """Call OpenAI or Groq endpoint."""
        if self.provider == "groq":
            endpoint = "https://api.groq.com/openai/v1/chat/completions"
        else:
            endpoint = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=25)
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return {
            "text": text,
            "provider": self.provider.title(),
            "model": self.model,
            "is_real_llm": True
        }

    def _offline_fallback(self, prompt: str, context: Optional[str]) -> str:
        """
        Produce a high-grade analytical synthesis when no cloud API key is present.
        """
        if context:
            return (
                f"### AnalystOS AI Investigation Intelligence\n\n"
                f"Based on verified empirical calculations from your active dataset:\n\n"
                f"{context}\n\n"
                f"**Recommendation Summary:**\n"
                f"To restore net profitability, execute minimum pricing floors, renegotiate component costs, "
                f"and rationalize territorial discounts as outlined in the multi-agent findings above."
            )
        else:
            return (
                f"I am ready to investigate your data. Please load a dataset and ask a question regarding "
                f"profit declines, category performance, regional margins, or product contribution."
            )
