"""Page : composition détaillée du portefeuille."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from components.data_loader import (
    INITIAL_CAPITAL,
    format_date_fr,
    load_pipeline_state,
)
from components.styling import apply_pro_layout, inject_custom_css

st.set_page_config(page_title="Portefeuille - BML", page_icon="💼", layout="wide")
inject_custom_css()

state = load_pipeline_state()
ps = state.portfolio_state

st.title("Portefeuille")
st.caption(f"Composition au {format_date_fr(state.today)}")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Capital initial", f"{INITIAL_CAPITAL:,.0f} €")
with col2:
    st.metric("Valeur totale", f"{ps.total_value:,.0f} €")
with col3:
    nav = ps.nav_per_share
    st.metric(
        "NAV par part",
        f"{nav:.2f}",
        delta=f"{(nav - 100):+.2f}",
        help="Indexée sur base 100 à l'inception.",
    )
with col4:
    st.metric("Positions", f"{len(ps.positions)}")

st.divider()

# ---------- Treemap ----------

st.subheader("Répartition par classe d'actifs")

position_data = []
for pos in ps.positions:
    position_data.append(
        {
            "Ticker": pos.asset.ticker,
            "Classe": pos.bucket.value.replace("_", " ").title(),
            "Nom": pos.asset.name,
            "Valeur": pos.market_value,
        }
    )

df_pos = pd.DataFrame(position_data)

treemap_palette = [
    "#1e3a8a", "#3b82f6", "#0ea5e9", "#06b6d4",
    "#10b981", "#f59e0b", "#f97316", "#8b5cf6",
    "#ec4899",
]

fig = px.treemap(
    df_pos,
    path=[px.Constant("Portefeuille"), "Classe", "Ticker"],
    values="Valeur",
    color="Classe",
    color_discrete_sequence=treemap_palette,
    hover_data={"Nom": True, "Valeur": ":,.0f"},
)
fig.update_traces(
    textinfo="label+percent parent",
    textfont_size=13,
    marker=dict(line=dict(color="#ffffff", width=2)),
)
apply_pro_layout(fig, height=520, show_legend=False, grid=False)
fig.update_layout(margin=dict(t=10, b=10, l=10, r=10))
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------- Positions detailed table ----------

st.subheader(f"Positions détaillées ({len(ps.positions)})")

pos_rows = []
for pos in ps.positions:
    pos_rows.append(
        {
            "Ticker": pos.asset.ticker,
            "Nom": pos.asset.name,
            "Classe": pos.bucket.value.replace("_", " ").title(),
            "Quantité": f"{pos.quantity:.2f}",
            "Prix": f"{pos.current_price:,.2f}",
            "Valeur (€)": f"{pos.market_value:,.0f}",
            "Poids": f"{pos.market_value / ps.total_value:.2%}",
            "TER": f"{pos.asset.ter:.2%}",
        }
    )

df_positions = pd.DataFrame(pos_rows).sort_values(
    "Valeur (€)", key=lambda x: x.str.replace(",", "").astype(float), ascending=False
)
st.dataframe(df_positions, hide_index=True, use_container_width=True)

if ps.cash > 0.01:
    st.info(
        f"Cash résiduel : {ps.cash:.2f} € "
        "(résiduel d'arrondi sur les fractional shares non investis)."
    )

st.divider()

# ---------- Bucket summary ----------

st.subheader("Synthèse par classe d'actifs")

bucket_dict: dict[str, dict] = {}
for pos in ps.positions:
    key = pos.bucket.value.replace("_", " ").title()
    if key not in bucket_dict:
        bucket_dict[key] = {"total_value": 0.0, "n_positions": 0, "tickers": []}
    bucket_dict[key]["total_value"] += pos.market_value
    bucket_dict[key]["n_positions"] += 1
    bucket_dict[key]["tickers"].append(pos.asset.ticker)

bucket_rows = []
for key, info in bucket_dict.items():
    bucket_rows.append(
        {
            "Classe d'actifs": key,
            "Positions": info["n_positions"],
            "Tickers": ", ".join(info["tickers"]),
            "Valeur (€)": f"{info['total_value']:,.0f}",
            "Poids": f"{info['total_value'] / ps.total_value:.1%}",
        }
    )

df_buckets = pd.DataFrame(bucket_rows).sort_values(
    "Valeur (€)", key=lambda x: x.str.replace(",", "").astype(float), ascending=False
)
st.dataframe(df_buckets, hide_index=True, use_container_width=True)

st.divider()
st.markdown(
    "<div style='text-align: center; color: #94a3b8; font-size: 13px; padding: 1rem 0;'>"
    "Le portefeuille est rebalancé mensuellement. Voir la "
    "<a href='https://github.com/TTB10/bordeaux-multi-asset-lab/blob/main/docs/technical_doc.md' style='color: #475569;'>documentation technique</a> "
    "pour le workflow opérationnel."
    "</div>",
    unsafe_allow_html=True,
)