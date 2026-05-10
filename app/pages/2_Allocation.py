"""Page : décomposition de l'allocation tactique."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from bml.allocation.tilts import DEFAULT_REGIME_TILTS, NEUTRAL_TILT
from components.data_loader import format_date_fr, load_pipeline_state, regime_color
from components.styling import (
    NEUTRAL,
    PRIMARY,
    apply_pro_layout,
    inject_custom_css,
)

st.set_page_config(page_title="Allocation - BML", page_icon="⚖️", layout="wide")
inject_custom_css()

state = load_pipeline_state()
signal = state.regime_signal
target = state.target_allocation

st.title("Allocation tactique")
st.caption(f"Allocation cible au {format_date_fr(state.today)}")

regime_value = signal.regime.value
regime_label = regime_value.replace("_", " ").title()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Régime détecté", regime_label)
with col2:
    st.metric("Confidence", f"{signal.confidence:.0%}")
with col3:
    if regime_value == "uncertain":
        st.metric(
            "Mode",
            "Allocation neutre",
            help="En régime Incertain, le système retourne directement l'allocation neutre.",
        )
    else:
        st.metric(
            "Smoothing",
            f"{(1 - signal.confidence):.0%} neutre + {signal.confidence:.0%} régime",
        )

st.divider()

# ---------- Bar chart comparison ----------

st.subheader("Décomposition de l'allocation")

if regime_value != "uncertain" and signal.regime in DEFAULT_REGIME_TILTS:
    regime_tilt = DEFAULT_REGIME_TILTS[signal.regime]
    show_regime_column = True
else:
    regime_tilt = NEUTRAL_TILT
    show_regime_column = False

all_classes = sorted(
    set(NEUTRAL_TILT.keys()) | set(target.as_dict().keys()) | set(regime_tilt.keys()),
    key=lambda ac: ac.value,
)

class_labels = [ac.value.replace("_", " ").title() for ac in all_classes]
neutre_values = [NEUTRAL_TILT.get(ac, 0.0) * 100 for ac in all_classes]
regime_values = [regime_tilt.get(ac, 0.0) * 100 for ac in all_classes]
final_values = [target.weight_of(ac) * 100 for ac in all_classes]

fig = go.Figure()
fig.add_trace(
    go.Bar(
        name="Neutre 60/40",
        x=class_labels,
        y=neutre_values,
        marker_color=NEUTRAL,
        marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Neutre : %{y:.1f}%<extra></extra>",
    )
)
if show_regime_column:
    fig.add_trace(
        go.Bar(
            name=f"Cible {regime_label} (confidence 100%)",
            x=class_labels,
            y=regime_values,
            marker_color=regime_color(regime_value),
            marker_line_width=0,
            hovertemplate="<b>%{x}</b><br>Cible régime : %{y:.1f}%<extra></extra>",
        )
    )
fig.add_trace(
    go.Bar(
        name="Allocation finale (smoothée)",
        x=class_labels,
        y=final_values,
        marker_color=PRIMARY,
        marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Finale : %{y:.1f}%<extra></extra>",
    )
)
fig.update_layout(barmode="group", yaxis_title="Poids (%)")
fig.update_xaxes(tickangle=-30)
apply_pro_layout(fig, height=460)
st.plotly_chart(fig, use_container_width=True)

# ---------- Deltas table ----------

st.subheader("Écarts vs allocation neutre")

display_data = []
for ac in all_classes:
    neutral_w = NEUTRAL_TILT.get(ac, 0.0)
    final_w = target.weight_of(ac)
    delta = final_w - neutral_w
    display_data.append(
        {
            "Classe d'actifs": ac.value.replace("_", " ").title(),
            "Poids neutre": f"{neutral_w:.1%}",
            "Poids final": f"{final_w:.1%}",
            "Écart": f"{delta:+.2%}",
        }
    )

df_deltas = pd.DataFrame(display_data)


def color_delta(val: str) -> str:
    if val in ("+0.00%", "-0.00%"):
        return "color: #94a3b8;"
    if val.startswith("+"):
        return "color: #10b981; font-weight: 700;"
    if val.startswith("-"):
        return "color: #ef4444; font-weight: 700;"
    return ""


styled = df_deltas.style.map(color_delta, subset=["Écart"])
st.dataframe(styled, hide_index=True, use_container_width=True)

st.divider()

st.subheader("Mécanisme de smoothing par confidence")

if regime_value == "uncertain":
    st.info(
        "**Régime Incertain** : les indicateurs macroéconomiques ne convergent pas "
        "vers un diagnostic clair. Le système court-circuite le mécanisme de smoothing "
        "et retourne directement l'allocation neutre, en attendant un signal plus tranché."
    )
else:
    st.markdown(
        f"""
L'allocation finale est calculée par interpolation linéaire :

`allocation_finale = neutre + confidence × (tilt_régime - neutre)`

Cette formule garantit trois propriétés :

- **Stabilité aux signaux faibles** : si la confidence tend vers 0, l'allocation reste alignée sur le neutre.
- **Linéarité** : changement progressif de la confidence implique changement progressif de l'allocation.
- **Préservation de la sommabilité** : neutre + tilt cible somment à 100%, donc allocation finale somme à 100%.

**Au {format_date_fr(state.today)}**, la confidence sur le régime **{regime_label}** est de **{signal.confidence:.0%}**, plaçant l'allocation finale à **{signal.confidence:.0%}** du chemin entre le neutre et le tilt cible.
        """
    )

st.divider()
st.markdown(
    "<div style='text-align: center; color: #94a3b8; font-size: 13px; padding: 1rem 0;'>"
    "Méthodologie détaillée dans le "
    "<a href='https://github.com/TTB10/bordeaux-multi-asset-lab/blob/main/docs/white_paper.md' style='color: #475569;'>white paper</a> "
    "(section 4.3)."
    "</div>",
    unsafe_allow_html=True,
)