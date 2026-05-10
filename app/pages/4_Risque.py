"""Page : analyse détaillée du risque.

Affiche les 7 métriques empiriques avec comparaison vs benchmark, la courbe
NAV, l'underwater chart (drawdown), la distribution des rendements, et le
Sharpe glissant.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.data_loader import format_date_fr, load_pipeline_state

st.set_page_config(
    page_title="Risque — BML",
    page_icon="📈",
    layout="wide",
)

state = load_pipeline_state()
pf_metrics = state.portfolio_metrics
bench_metrics = state.benchmark_metrics
pf_levels = state.portfolio_levels_series
bench_levels = state.benchmark_levels_series

pf_returns = pf_levels.pct_change().dropna()
bench_returns = bench_levels.pct_change().dropna()

# ---------- Header ----------

st.title("Analyse du risque")
st.caption(
    f"Métriques empiriques sur 3 ans glissants au {format_date_fr(state.today)}, "
    f"basées sur {len(pf_returns)} observations quotidiennes."
)

# ---------- Top 4 metric cards (vs benchmark) ----------

col1, col2, col3, col4 = st.columns(4)

with col1:
    delta_ret = pf_metrics.annual_return - bench_metrics.annual_return
    st.metric(
        "Rendement annualisé",
        f"{pf_metrics.annual_return:+.2%}",
        delta=f"{delta_ret:+.2%} vs 60/40",
    )

with col2:
    delta_sharpe = pf_metrics.sharpe_ratio - bench_metrics.sharpe_ratio
    st.metric(
        "Sharpe ratio",
        f"{pf_metrics.sharpe_ratio:+.2f}",
        delta=f"{delta_sharpe:+.2f} vs 60/40",
    )

with col3:
    delta_dd = pf_metrics.max_drawdown - bench_metrics.max_drawdown
    st.metric(
        "Max drawdown",
        f"{pf_metrics.max_drawdown:+.2%}",
        delta=f"{delta_dd:+.2%} vs 60/40",
        delta_color="inverse",
    )

with col4:
    if pf_metrics.beta is not None:
        st.metric(
            "Beta vs 60/40",
            f"{pf_metrics.beta:+.2f}",
            help="Sensibilité aux mouvements du benchmark. <1 = défensif, >1 = offensif.",
        )
    else:
        st.metric("Beta vs 60/40", "n/a")

st.divider()

# ---------- Detailed metrics table ----------

st.subheader("Comparaison détaillée des métriques")

beta_pf = (
    f"{pf_metrics.beta:+.2f}" if pf_metrics.beta is not None else "n/a"
)

metrics_table = pd.DataFrame(
    [
        ["Rendement annualisé", f"{pf_metrics.annual_return:+.2%}", f"{bench_metrics.annual_return:+.2%}"],
        ["Volatilité annualisée", f"{pf_metrics.annual_volatility:.2%}", f"{bench_metrics.annual_volatility:.2%}"],
        ["Sharpe ratio", f"{pf_metrics.sharpe_ratio:+.2f}", f"{bench_metrics.sharpe_ratio:+.2f}"],
        ["Max drawdown", f"{pf_metrics.max_drawdown:+.2%}", f"{bench_metrics.max_drawdown:+.2%}"],
        ["VaR 95% (journalière)", f"{pf_metrics.var_95:+.2%}", f"{bench_metrics.var_95:+.2%}"],
        ["CVaR 95% (journalière)", f"{pf_metrics.cvar_95:+.2%}", f"{bench_metrics.cvar_95:+.2%}"],
        ["Beta vs 60/40", beta_pf, "1.00"],
    ],
    columns=["Métrique", "Portefeuille", "Benchmark 60/40"],
)
st.dataframe(metrics_table, hide_index=True, use_container_width=True)

st.divider()

# ---------- NAV chart ----------

st.subheader("Évolution du NAV (base 100)")

fig_nav = go.Figure()
fig_nav.add_trace(
    go.Scatter(
        x=pf_levels.index,
        y=pf_levels.values,
        name="Portefeuille",
        line=dict(color="#3b82f6", width=2),
    )
)
fig_nav.add_trace(
    go.Scatter(
        x=bench_levels.index,
        y=bench_levels.values,
        name="Benchmark 60/40",
        line=dict(color="#9ca3af", width=2, dash="dot"),
    )
)
fig_nav.update_layout(
    yaxis_title="NAV (base 100)",
    xaxis_title=None,
    height=400,
    margin=dict(t=20, b=20, l=40, r=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    plot_bgcolor="white",
    hovermode="x unified",
)
fig_nav.update_xaxes(showgrid=False)
fig_nav.update_yaxes(showgrid=True, gridcolor="#f3f4f6")
st.plotly_chart(fig_nav, use_container_width=True)

st.divider()

# ---------- Underwater chart (drawdown) ----------

st.subheader("Drawdown timeline (underwater chart)")

cum_pf = (1.0 + pf_returns).cumprod()
running_max_pf = cum_pf.cummax()
drawdown_pf = (cum_pf / running_max_pf - 1.0) * 100

cum_bench = (1.0 + bench_returns).cumprod()
running_max_bench = cum_bench.cummax()
drawdown_bench = (cum_bench / running_max_bench - 1.0) * 100

fig_dd = go.Figure()
fig_dd.add_trace(
    go.Scatter(
        x=drawdown_pf.index,
        y=drawdown_pf.values,
        name="Portefeuille",
        fill="tozeroy",
        fillcolor="rgba(239, 68, 68, 0.15)",
        line=dict(color="#ef4444", width=1.5),
    )
)
fig_dd.add_trace(
    go.Scatter(
        x=drawdown_bench.index,
        y=drawdown_bench.values,
        name="Benchmark 60/40",
        line=dict(color="#9ca3af", width=1, dash="dot"),
    )
)
fig_dd.update_layout(
    yaxis_title="Drawdown (%)",
    xaxis_title=None,
    height=350,
    margin=dict(t=20, b=20, l=40, r=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    plot_bgcolor="white",
    hovermode="x unified",
)
fig_dd.update_xaxes(showgrid=False)
fig_dd.update_yaxes(showgrid=True, gridcolor="#f3f4f6")
st.plotly_chart(fig_dd, use_container_width=True)
st.caption(
    "L'underwater chart montre la chute en pourcentage par rapport au plus haut historique. "
    "Plus la zone est profonde et large, plus la perte a été sévère et persistante."
)

st.divider()

# ---------- Returns distribution + Rolling Sharpe ----------

col_dist, col_rolling = st.columns(2)

with col_dist:
    st.subheader("Distribution des rendements quotidiens")

    pf_returns_pct = pf_returns * 100

    fig_hist = go.Figure()
    fig_hist.add_trace(
        go.Histogram(
            x=pf_returns_pct,
            nbinsx=50,
            marker_color="#3b82f6",
            opacity=0.75,
            name="Rendements",
        )
    )
    fig_hist.add_vline(
        x=pf_metrics.var_95 * 100,
        line=dict(color="#f59e0b", width=2, dash="dash"),
        annotation_text=f"VaR 95% ({pf_metrics.var_95*100:+.2f}%)",
        annotation_position="top",
    )
    fig_hist.add_vline(
        x=pf_metrics.cvar_95 * 100,
        line=dict(color="#ef4444", width=2, dash="dash"),
        annotation_text=f"CVaR 95% ({pf_metrics.cvar_95*100:+.2f}%)",
        annotation_position="bottom",
    )
    fig_hist.update_layout(
        xaxis_title="Rendement quotidien (%)",
        yaxis_title="Fréquence",
        height=400,
        margin=dict(t=40, b=40, l=40, r=20),
        plot_bgcolor="white",
        showlegend=False,
    )
    fig_hist.update_xaxes(showgrid=False)
    fig_hist.update_yaxes(showgrid=True, gridcolor="#f3f4f6")
    st.plotly_chart(fig_hist, use_container_width=True)
    st.caption(
        "VaR 95% = 5e percentile (perte journalière dépassée 5% du temps). "
        "CVaR 95% = perte moyenne dans les 5% pires jours."
    )

with col_rolling:
    st.subheader("Sharpe glissant (fenêtre 63 jours)")

    window = 63  # ~3 months trading days
    risk_free_daily = 0.025 / 252.0

    rolling_mean = pf_returns.rolling(window).mean()
    rolling_std = pf_returns.rolling(window).std()
    rolling_sharpe = (rolling_mean - risk_free_daily) * 252.0 / (rolling_std * np.sqrt(252.0))

    rolling_mean_b = bench_returns.rolling(window).mean()
    rolling_std_b = bench_returns.rolling(window).std()
    rolling_sharpe_b = (rolling_mean_b - risk_free_daily) * 252.0 / (rolling_std_b * np.sqrt(252.0))

    fig_roll = go.Figure()
    fig_roll.add_trace(
        go.Scatter(
            x=rolling_sharpe.index,
            y=rolling_sharpe.values,
            name="Portefeuille",
            line=dict(color="#3b82f6", width=2),
        )
    )
    fig_roll.add_trace(
        go.Scatter(
            x=rolling_sharpe_b.index,
            y=rolling_sharpe_b.values,
            name="Benchmark 60/40",
            line=dict(color="#9ca3af", width=2, dash="dot"),
        )
    )
    fig_roll.add_hline(y=0, line=dict(color="#cccccc", width=1))
    fig_roll.add_hline(y=1, line=dict(color="#10b981", width=1, dash="dot"))
    fig_roll.update_layout(
        yaxis_title="Sharpe",
        xaxis_title=None,
        height=400,
        margin=dict(t=20, b=20, l=40, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white",
    )
    fig_roll.update_xaxes(showgrid=False)
    fig_roll.update_yaxes(showgrid=True, gridcolor="#f3f4f6")
    st.plotly_chart(fig_roll, use_container_width=True)
    st.caption(
        "Sharpe sur fenêtre glissante de 63 jours (~3 mois). "
        "Ligne verte pointillée à Sharpe = 1 (seuil de qualité standard)."
    )

st.divider()

# ---------- Methodology notes ----------

with st.expander("Notes méthodologiques sur le calcul des métriques"):
    st.markdown(
        """
- **Rendement annualisé** : composition annuelle des rendements quotidiens, base 252 jours ouvrés.
- **Volatilité annualisée** : écart-type des rendements quotidiens × √252.
- **Sharpe ratio** : (rendement annualisé − taux sans risque) / volatilité annualisée. Taux sans risque par défaut : 2.5 % (≈ EUR overnight).
- **Max drawdown** : pire chute peak-to-trough sur la période.
- **VaR 95%** : 5e percentile empirique des rendements quotidiens (non-paramétrique, sans hypothèse de normalité).
- **CVaR 95%** : moyenne des rendements en dessous de la VaR (Expected Shortfall, plus robuste pour le tail risk).
- **Beta** : `cov(rendements_pf, rendements_bench) / var(rendements_bench)`.

Toutes les métriques sont calculées sur la même fenêtre glissante de 3 ans, avec les mêmes prix journaliers Yahoo Finance.
        """
    )

st.divider()
st.markdown(
    "<div style='text-align: center; color: #888; font-size: 14px;'>"
    "Méthodologie complète dans le "
    "<a href='https://github.com/TTB10/bordeaux-multi-asset-lab/blob/main/docs/white_paper.md'>white paper</a> "
    "(section 4.5)."
    "</div>",
    unsafe_allow_html=True,
)