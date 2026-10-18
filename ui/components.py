"""
UI components and styling helpers for AnalystOS.
"""

import streamlit as st


def apply_custom_styles():
    """
    Inject professional CSS styling for a modern business intelligence dashboard.
    """
    st.markdown("""
        <style>
        /* Base typography & card styling */
        .main-header {
            font-size: 2.1rem;
            font-weight: 800;
            color: #1E293B;
            letter-spacing: -0.02em;
            margin-bottom: 0.2rem;
        }
        .sub-header {
            font-size: 1.05rem;
            color: #64748B;
            margin-bottom: 1.5rem;
        }
        .metric-card {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 1.1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: all 0.2s ease;
        }
        .metric-card:hover {
            box-shadow: 0 4px 6px rgba(0,0,0,0.07);
            border-color: #CBD5E1;
        }
        .metric-label {
            font-size: 0.82rem;
            text-transform: uppercase;
            font-weight: 700;
            color: #64748B;
            letter-spacing: 0.05em;
        }
        .metric-value {
            font-size: 1.7rem;
            font-weight: 800;
            color: #0F172A;
            margin-top: 0.3rem;
        }
        .metric-sub {
            font-size: 0.8rem;
            color: #10B981;
            font-weight: 600;
            margin-top: 0.2rem;
        }
        /* Agent badges */
        .badge-completed {
            background-color: #ECFDF5;
            color: #065F46;
            border: 1px solid #A7F3D0;
            padding: 3px 10px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
        }
        .badge-running {
            background-color: #EFF6FF;
            color: #1E40AF;
            border: 1px solid #BFDBFE;
            padding: 3px 10px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
        }
        .badge-failed {
            background-color: #FEF2F2;
            color: #991B1B;
            border: 1px solid #FECACA;
            padding: 3px 10px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
        }
        .badge-idle {
            background-color: #F8FAFC;
            color: #64748B;
            border: 1px solid #E2E8F0;
            padding: 3px 10px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .agent-container {
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 0.8rem;
            background: #FFFFFF;
        }
        </style>
    """, unsafe_allow_html=True)


def render_agent_status_badge(status_str: str) -> str:
    """Return HTML string for an agent's execution status badge."""
    s = (status_str or "IDLE").upper()
    if s == "COMPLETED":
        return '<span class="badge-completed">● COMPLETED</span>'
    elif s == "RUNNING":
        return '<span class="badge-running">⏳ RUNNING</span>'
    elif s == "FAILED":
        return '<span class="badge-failed">✖ FAILED</span>'
    else:
        return '<span class="badge-idle">○ IDLE</span>'


def render_agent_status_card(
    agent_id: str,
    name: str,
    role: str,
    status: str,
    duration_ms: float = 0.0,
    summary: str = ""
):
    """Render a card detailing an agent's real-time state and summary."""
    badge_html = render_agent_status_badge(status)
    dur_text = f"{duration_ms:.1f}ms" if duration_ms > 0 else "—"

    st.markdown(f"""
    <div class="agent-container">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong style="font-size: 1.05rem; color: #1E293B;">{name}</strong>
                <div style="font-size: 0.82rem; color: #64748B;">{role}</div>
            </div>
            <div>
                {badge_html}
            </div>
        </div>
        <div style="margin-top: 0.6rem; font-size: 0.85rem; color: #334155; border-top: 1px solid #F1F5F9; padding-top: 0.4rem;">
            <span>⏱️ <b>Duration:</b> {dur_text}</span> | <span>📋 <b>Output:</b> {summary or 'Awaiting execution...'}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
