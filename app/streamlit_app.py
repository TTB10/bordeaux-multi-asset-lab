"""Bordeaux Multi-Asset Lab - Home page (overview).

Run from project root:
    uv run streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.data_loader import format_date_fr, load_pipeline_state
from components.styling import (
    COLOR_BENCHMARK,
    COLOR_PORTFOLIO,
    apply_pro_layout,
    inject_custom_css,
)

st.set_page_config(
    page_title="Bordeaux Multi-Asset Lab",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_custom_css()

# ---------- Header ----------

st.markdown(
    """
    <div style="
        padding: 28px 32px;
        background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
        border: 1px solid #e2e8f0;
        border-left: 4px solid #1e3a8a;
        border-radius: 10px;
        margin-bottom: 28px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    ">
        <div style="
            display: inline-block;
            background-color: #1e3a8a;
            color: white;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            padding: 4px 10px;
            border-radius: 4px;
            margin-bottom: 14px;
        ">
            Bordeaux Multi-Asset Lab
        </div>
        <h1 style="
            font-size: 34px;
            font-weight: 700;
            letter-spacing: -0.025em;
            color: #0f172a;
            margin: 0 0 8px 0;
            line-height: 1.2;
        ">
            Système d'allocation tactique multi-actifs
        </h1>
        <div style="
            font-size: 17px;
            color: #475569;
            font-weight: 400;
            margin-bottom: 18px;
        ">
            Guidé par le régime macroéconomique · Univers UCITS · Discipline systématique
        </div>
        <div style="
            font-size: 14px;
            color: #475569;
            line-height: 1.65;
            max-width: 900px;
        ">
            Ce framework détecte le régime macroéconomique courant à partir de six indicateurs
            publics issus de la base FRED, en déduit une allocation cible parmi cinq régimes
            Bridgewater-style, et sélectionne automatiquement les ETFs UCITS les mieux notés
            sur un univers de 49. L'allocation est régularisée par la confidence du signal
            pour éviter les paris extrêmes sur des indicateurs faibles.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

state = load_pipeline_state()

# ---------- État du jour : 4 metric cards ----------

st.subheader(f"État du jour — {format_date_fr(state.today)}")

col1, col2, col3, col4 = st.columns(4)

with col1:
    regime_label = state.regime_signal.regime.value.replace("_", " ").title()
    st.metric(label="Régime détecté", value=regime_label)

with col2:
    st.metric(
        label="Confidence",
        value=f"{state.regime_signal.confidence:.0%}",
        help=(
            "Confidence du régime = min(confidence Croissance, confidence Inflation). "
            "Une confidence faible signifie que les indicateurs sont contradictoires "
            "et que le système refuse de classifier."
        ),
    )

with col3:
    nav = state.portfolio_state.nav_per_share
    st.metric(
        label="NAV par part",
        value=f"{nav:.2f}",
        help="Indexée sur base 100 à l'inception du portefeuille.",
    )

with col4:
    delta_sharpe = (
        state.portfolio_metrics.sharpe_ratio - state.benchmark_metrics.sharpe_ratio
    )
    st.metric(
        label="Sharpe ratio (3 ans)",
        value=f"{state.portfolio_metrics.sharpe_ratio:+.2f}",
        delta=f"{delta_sharpe:+.2f} vs 60/40",
    )

st.divider()

# ---------- Allocation pie + Risk table ----------

col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("Allocation cible par classe d'actifs")

    alloc_dict = state.target_allocation.as_dict()
    labels = [ac.value.replace("_", " ").title() for ac in alloc_dict]
    values = [w for w in alloc_dict.values()]

    pie_palette = [
        "#1e3a8a", "#3b82f6", "#0ea5e9", "#06b6d4",
        "#10b981", "#f59e0b", "#f97316", "#8b5cf6",
        "#ec4899",
    ]

    fig = px.pie(
        names=labels,
        values=values,
        hole=0.55,
        color_discrete_sequence=pie_palette,
    )
    fig.update_traces(
        textposition="outside",
        textinfo="percent+label",
        textfont_size=11,
        marker=dict(line=dict(color="#ffffff", width=2)),
    )
    apply_pro_layout(fig, height=420, show_legend=False, grid=False)
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Métriques de risque (3 ans)")

    pf = state.portfolio_metrics
    bench = state.benchmark_metrics
    beta_pf = f"{pf.beta:+.2f}" if pf.beta is not None else "n/a"

    metrics_data = [
        ("Rendement annualisé", f"{pf.annual_return:+.2%}", f"{bench.annual_return:+.2%}"),
        ("Volatilité annualisée", f"{pf.annual_volatility:.2%}", f"{bench.annual_volatility:.2%}"),
        ("Sharpe ratio", f"{pf.sharpe_ratio:+.2f}", f"{bench.sharpe_ratio:+.2f}"),
        ("Max drawdown", f"{pf.max_drawdown:+.2%}", f"{bench.max_drawdown:+.2%}"),
        ("VaR 95% (journalière)", f"{pf.var_95:+.2%}", f"{bench.var_95:+.2%}"),
        ("Beta vs 60/40", beta_pf, "1.00"),
    ]

    df_metrics = pd.DataFrame(
        metrics_data, columns=["Métrique", "Portefeuille", "Benchmark 60/40"]
    )
    st.dataframe(df_metrics, hide_index=True, use_container_width=True)

st.divider()

# ---------- NAV chart ----------

st.subheader("Évolution simulée du NAV (base 100)")

fig_nav = go.Figure()
fig_nav.add_trace(
    go.Scatter(
        x=state.portfolio_levels_series.index,
        y=state.portfolio_levels_series.values,
        name="Portefeuille",
        line=dict(color=COLOR_PORTFOLIO, width=2.5),
        hovertemplate="<b>Portefeuille</b><br>%{x|%d %b %Y}<br>NAV : %{y:.2f}<extra></extra>",
    )
)
fig_nav.add_trace(
    go.Scatter(
        x=state.benchmark_levels_series.index,
        y=state.benchmark_levels_series.values,
        name="Benchmark 60/40",
        line=dict(color=COLOR_BENCHMARK, width=2, dash="dot"),
        hovertemplate="<b>Benchmark 60/40</b><br>%{x|%d %b %Y}<br>NAV : %{y:.2f}<extra></extra>",
    )
)
apply_pro_layout(fig_nav, height=380)
fig_nav.update_layout(yaxis_title="NAV (base 100)", hovermode="x unified")
st.plotly_chart(fig_nav, use_container_width=True)

# ---------- Footer ----------

st.divider()
st.markdown(
    "<div style='text-align: center; color: #94a3b8; font-size: 13px; padding: 1rem 0;'>"
    "Code source · "
    "<a href='https://github.com/TTB10/bordeaux-multi-asset-lab' style='color: #475569;'>GitHub</a> · "
    "<a href='https://github.com/TTB10/bordeaux-multi-asset-lab/blob/main/docs/white_paper.md' style='color: #475569;'>White paper</a> · "
    "<a href='https://github.com/TTB10/bordeaux-multi-asset-lab/blob/main/docs/technical_doc.md' style='color: #475569;'>Documentation technique</a>"
    "</div>",
    unsafe_allow_html=True,
)