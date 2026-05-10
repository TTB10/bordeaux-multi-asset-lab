"""Bordeaux Multi-Asset Lab — Home page (overview).

Run from project root:
    uv run streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the components/ folder importable
sys.path.insert(0, str(Path(__file__).parent))

import plotly.express as px
import streamlit as st

from components.data_loader import format_date_fr, load_pipeline_state, regime_color

st.set_page_config(
    page_title="Bordeaux Multi-Asset Lab",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Header ----------

st.title("Bordeaux Multi-Asset Lab")
st.caption(
    "Système d'allocation tactique multi-actifs guidé par le régime macroéconomique"
)

st.markdown(
    """
    Ce framework détecte le régime macroéconomique courant à partir de six indicateurs
    publics issus de la base FRED, en déduit une allocation cible parmi cinq régimes
    Bridgewater-style, et sélectionne automatiquement les ETFs UCITS les mieux notés
    sur un univers de 49. L'allocation est régularisée par la confidence du signal
    pour éviter les paris extrêmes sur des indicateurs faibles.
    """
)

# ---------- Load state ----------

state = load_pipeline_state()

# ---------- État du jour : 4 metric cards ----------

st.subheader(f"État du jour — {format_date_fr(state.today)}")

col1, col2, col3, col4 = st.columns(4)

with col1:
    regime_label = state.regime_signal.regime.value.replace("_", " ").title()
    st.metric(
        label="Régime détecté",
        value=regime_label,
    )

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
    st.metric(
        label="Sharpe ratio (3 ans)",
        value=f"{state.portfolio_metrics.sharpe_ratio:+.2f}",
        delta=f"{state.portfolio_metrics.sharpe_ratio - state.benchmark_metrics.sharpe_ratio:+.2f} vs 60/40",
    )

st.divider()

# ---------- Allocation pie + Risk table ----------

col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("Allocation cible par classe d'actifs")

    alloc_dict = state.target_allocation.as_dict()
    labels = [ac.value.replace("_", " ").title() for ac in alloc_dict]
    values = [w for w in alloc_dict.values()]

    fig = px.pie(
        names=labels,
        values=values,
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(
        showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10),
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Métriques de risque (3 ans)")

    metrics_data = [
        (
            "Rendement annualisé",
            f"{state.portfolio_metrics.annual_return:+.2%}",
            f"{state.benchmark_metrics.annual_return:+.2%}",
        ),
        (
            "Volatilité annualisée",
            f"{state.portfolio_metrics.annual_volatility:.2%}",
            f"{state.benchmark_metrics.annual_volatility:.2%}",
        ),
        (
            "Sharpe ratio",
            f"{state.portfolio_metrics.sharpe_ratio:+.2f}",
            f"{state.benchmark_metrics.sharpe_ratio:+.2f}",
        ),
        (
            "Max drawdown",
            f"{state.portfolio_metrics.max_drawdown:+.2%}",
            f"{state.benchmark_metrics.max_drawdown:+.2%}",
        ),
        (
            "VaR 95% (journalière)",
            f"{state.portfolio_metrics.var_95:+.2%}",
            f"{state.benchmark_metrics.var_95:+.2%}",
        ),
        (
            "Beta vs 60/40",
            f"{state.portfolio_metrics.beta:+.2f}"
            if state.portfolio_metrics.beta is not None
            else "n/a",
            "1.00",
        ),
    ]
    import pandas as pd

    df_metrics = pd.DataFrame(
        metrics_data, columns=["Métrique", "Portefeuille", "Benchmark 60/40"]
    )
    st.dataframe(df_metrics, hide_index=True, use_container_width=True)

st.divider()

# ---------- NAV chart ----------

st.subheader("Évolution simulée du NAV (base 100, 3 ans)")

import pandas as pd

nav_df = pd.DataFrame(
    {
        "Date": state.portfolio_levels_series.index,
        "Portefeuille": state.portfolio_levels_series.values,
        "Benchmark 60/40": state.benchmark_levels_series.values,
    }
).set_index("Date")

st.line_chart(nav_df, height=350)

# ---------- Footer ----------

st.divider()
st.caption(
    "Code source · "
    "[GitHub](https://github.com/TTB10/bordeaux-multi-asset-lab) · "
    "[White paper](https://github.com/TTB10/bordeaux-multi-asset-lab/blob/main/docs/white_paper.md) · "
    "[Documentation technique](https://github.com/TTB10/bordeaux-multi-asset-lab/blob/main/docs/technical_doc.md)"
)