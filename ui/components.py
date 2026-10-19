"""
UI components and styling helpers for AnalystOS.

Clean, professional enterprise styling without emojis.
"""

from __future__ import annotations
import streamlit as st


def apply_custom_styles():
    """
    Inject professional CSS styling for a modern enterprise business intelligence platform.
    Uses clean typography, card containers, and neutral corporate color palettes.
    """
    st.markdown("""
        <style>
        /* Base typography & containers */
        .main-header {
            font-size: 1.85rem;
            font-weight: 700;
            color: #0F172A;
            letter-spacing: -0.02em;
            margin-bottom: 0.25rem;
        }
        .sub-header {
            font-size: 1.0rem;
            color: #475569;
            margin-bottom: 1.25rem;
        }
        .metric-card {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 1.0rem;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
            transition: all 0.15s ease;
        }
        .metric-card:hover {
            box-shadow: 0 3px 6px rgba(0,0,0,0.06);
            border-color: #CBD5E1;
        }
        .metric-label {
            font-size: 0.78rem;
            text-transform: uppercase;
            font-weight: 600;
            color: #64748B;
            letter-spacing: 0.04em;
        }
        .metric-value {
            font-size: 1.6rem;
            font-weight: 700;
            color: #0F172A;
            margin-top: 0.25rem;
        }
        .metric-sub {
            font-size: 0.78rem;
            color: #059669;
            font-weight: 500;
            margin-top: 0.2rem;
        }
        /* Status Badges */
        .badge-completed {
            background-color: #ECFDF5;
            color: #065F46;
            border: 1px solid #A7F3D0;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.72rem;
            font-weight: 600;
        }
        .badge-running {
            background-color: #EFF6FF;
            color: #1E40AF;
            border: 1px solid #BFDBFE;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.72rem;
            font-weight: 600;
        }
        .badge-failed {
            background-color: #FEF2F2;
            color: #991B1B;
            border: 1px solid #FECACA;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.72rem;
            font-weight: 600;
        }
        .badge-idle {
            background-color: #F8FAFC;
            color: #64748B;
            border: 1px solid #E2E8F0;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.72rem;
            font-weight: 500;
        }
        .agent-container {
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            padding: 0.9rem;
            margin-bottom: 0.7rem;
            background: #FFFFFF;
        }
        .banner-container {
            background-color: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-left: 4px solid #2563EB;
            padding: 0.65rem 1rem;
            border-radius: 6px;
            margin-bottom: 1.2rem;
            font-size: 0.88rem;
            color: #1E293B;
        }
        </style>
    """, unsafe_allow_html=True)


def render_agent_status_badge(status_str: str) -> str:
    """Return clean HTML string for an agent's execution status badge (no emojis)."""
    s = (status_str or "IDLE").upper()
    if s == "COMPLETED":
        return '<span class="badge-completed">[COMPLETED]</span>'
    elif s == "RUNNING":
        return '<span class="badge-running">[RUNNING]</span>'
    elif s == "FAILED":
        return '<span class="badge-failed">[FAILED]</span>'
    else:
        return '<span class="badge-idle">[IDLE]</span>'


def render_agent_status_card(
    agent_id: str,
    name: str,
    role: str,
    status: str,
    duration_ms: float = 0.0,
    summary: str = ""
):
    """Render a card detailing an agent's real-time state and summary (no emojis)."""
    badge_html = render_agent_status_badge(status)
    dur_text = f"{duration_ms:.1f}ms" if duration_ms > 0 else "-"

    st.markdown(f"""
    <div class="agent-container">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong style="font-size: 1.0rem; color: #0F172A;">{name}</strong>
                <div style="font-size: 0.80rem; color: #64748B;">{role}</div>
            </div>
            <div>
                {badge_html}
            </div>
        </div>
        <div style="margin-top: 0.5rem; font-size: 0.82rem; color: #334155; border-top: 1px solid #F1F5F9; padding-top: 0.35rem;">
            <span><b>Duration:</b> {dur_text}</span> &nbsp;|&nbsp; <span><b>Output:</b> {summary or 'Awaiting execution...'}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
