"""Visual styling utilities for the Streamlit dashboard.

Centralizes:
- A coherent color palette across all pages
- CSS injection for custom look beyond Streamlit defaults
- A common Plotly layout applier for consistent chart styling
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

# Primary brand colors
PRIMARY = "#1e3a8a"
PRIMARY_LIGHT = "#3b82f6"
ACCENT = "#0ea5e9"
TEXT_PRIMARY = "#0f172a"
TEXT_SECONDARY = "#475569"
TEXT_MUTED = "#94a3b8"

# Semantic colors
SUCCESS = "#10b981"
WARNING = "#f59e0b"
DANGER = "#ef4444"
NEUTRAL = "#9ca3af"

# Backgrounds
BG_PRIMARY = "#fafafa"
BG_CARD = "#ffffff"
BG_GRID = "#f1f5f9"

# Portfolio vs benchmark colors (used consistently across all charts)
COLOR_PORTFOLIO = PRIMARY
COLOR_BENCHMARK = TEXT_MUTED

# Regime colors (canonical source)
REGIME_COLORS = {
    "goldilocks": "#10b981",
    "reflation": "#f59e0b",
    "stagflation": "#ef4444",
    "disinflation_recession": "#3b82f6",
    "uncertain": "#6b7280",
}


CUSTOM_CSS = """
<style>
    /* Hide Streamlit branding and chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Main content padding */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 1300px;
    }
    
    /* Typography */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    h1 {
        font-weight: 700;
        letter-spacing: -0.025em;
        color: #0f172a;
        margin-bottom: 0.25rem;
    }
    
    h2, h3 {
        font-weight: 600;
        color: #1e293b;
        margin-top: 2rem;
        margin-bottom: 0.75rem;
    }
    
    /* Caption + subtitle */
    [data-testid="stCaptionContainer"] {
        color: #64748b;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }
    
    /* Metric cards - polished look */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 18px 22px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        transition: all 0.15s ease;
    }
    
    [data-testid="stMetric"]:hover {
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
        border-color: #cbd5e1;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0f172a;
        letter-spacing: -0.02em;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.78rem;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.85rem;
        font-weight: 500;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
        color: #475569;
        font-weight: 500;
    }
    
    /* Dividers */
    hr {
        border: none;
        border-top: 1px solid #e2e8f0;
        margin: 2.5rem 0 2rem 0;
    }
    
    /* Tables - cleaner look */
    .stDataFrame {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        overflow: hidden;
    }
    
    .stDataFrame thead tr th {
        background-color: #f8fafc !important;
        color: #475569 !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        font-size: 0.75rem !important;
        letter-spacing: 0.05em;
    }
    
    /* Plotly charts - subtle border */
    .js-plotly-plot {
        background-color: #ffffff;
        border-radius: 8px;
    }
    
    /* Info boxes */
    .stAlert {
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        border: 1px solid #e2e8f0;
        transition: all 0.15s ease;
    }
    
    .stButton > button:hover {
        border-color: #1e3a8a;
        box-shadow: 0 2px 4px rgba(30, 58, 138, 0.1);
    }
</style>
"""


def inject_custom_css() -> None:
    """Inject custom CSS at the top of a Streamlit page. Call once per page."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


PLOTLY_FONT = dict(
    family="Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    size=12,
    color=TEXT_PRIMARY,
)


def apply_pro_layout(
    fig: go.Figure,
    *,
    height: int | None = None,
    show_legend: bool = True,
    legend_position: str = "top",
    grid: bool = True,
) -> go.Figure:
    """Apply a consistent professional layout to a Plotly figure.

    Args:
        fig: The Plotly figure to style.
        height: Optional explicit height. Default is figure-dependent.
        show_legend: Whether to display the legend.
        legend_position: 'top' (horizontal above chart) or 'right' (vertical).
        grid: Whether to show a subtle horizontal grid on Y axis.

    Returns:
        The same figure for chaining convenience.
    """
    layout_updates: dict = dict(
        font=PLOTLY_FONT,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(t=30, b=40, l=50, r=20),
        hoverlabel=dict(
            bgcolor="#ffffff",
            font_size=12,
            font_family=PLOTLY_FONT["family"],
            bordercolor="#e2e8f0",
        ),
    )

    if height is not None:
        layout_updates["height"] = height

    if not show_legend:
        layout_updates["showlegend"] = False
    elif legend_position == "top":
        layout_updates["legend"] = dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0)",
            font=dict(size=11, color=TEXT_SECONDARY),
        )

    fig.update_layout(**layout_updates)

    fig.update_xaxes(
        showgrid=False,
        showline=True,
        linecolor=BG_GRID,
        linewidth=1,
        tickfont=dict(size=11, color=TEXT_SECONDARY),
        title_font=dict(size=12, color=TEXT_SECONDARY),
    )
    fig.update_yaxes(
        showgrid=grid,
        gridcolor=BG_GRID,
        gridwidth=1,
        showline=False,
        tickfont=dict(size=11, color=TEXT_SECONDARY),
        title_font=dict(size=12, color=TEXT_SECONDARY),
    )

    return fig