"""Page : analyse détaillée du régime macroéconomique.

Affiche les 6 indicateurs avec leurs lectures, l'agrégation par dimension,
et la classification dans le framework 2x2 Bridgewater.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.data_loader import format_date_fr, load_pipeline_state, regime_color

st.set_page_config(
    page_title="Régime macro — BML",
    page_icon="📊",
    layout="wide",
)

state = load_pipeline_state()
signal = state.regime_signal

# ---------- Header ----------

st.title("Régime macroéconomique")
st.caption(
    f"Diagnostic au {format_date_fr(state.today)} "
    f"sur la base de 6 indicateurs FRED z-normalisés sur fenêtre glissante de 5 ans."
)

# ---------- Régime card ----------

regime_value = signal.regime.value
color = regime_color(regime_value)
regime_label = regime_value.replace("_", " ").title()

st.markdown(
    f"""
    <div style="
        background-color: {color}20;
        border-left: 5px solid {color};
        padding: 16px 20px;
        border-radius: 4px;
        margin: 12px 0;
    ">
        <div style="font-size: 13px; color: #666; text-transform: uppercase; letter-spacing: 1px;">
            Régime détecté
        </div>
        <div style="font-size: 28px; font-weight: bold; color: {color}; margin-top: 4px;">
            {regime_label}
        </div>
        <div style="font-size: 14px; color: #555; margin-top: 8px;">
            Confidence : <strong>{signal.confidence:.0%}</strong>
            ({"min" if signal.growth_signal.confidence > signal.inflation_signal.confidence else "min"}
            de Croissance {signal.growth_signal.confidence:.0%} et Inflation {signal.inflation_signal.confidence:.0%})
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ---------- Tableau des 6 indicateurs ----------

st.subheader("Lectures des indicateurs")

all_readings = (
    list(signal.growth_signal.contributing_readings)
    + list(signal.inflation_signal.contributing_readings)
)

readings_data = []
for r in all_readings:
    z = f"{r.z_score:+.2f}" if r.z_score is not None else "n/a"
    readings_data.append(
        {
            "Dimension": r.dimension.value.title(),
            "Indicateur": r.indicator_name,
            "Valeur": f"{r.value:+.2f}",
            "Z-score (5 ans)": z,
            "Direction": r.direction.value.upper(),
            "Confidence": f"{r.confidence:.0%}",
        }
    )

df_readings = pd.DataFrame(readings_data)


def color_direction(val: str) -> str:
    if val == "UP":
        return "color: #10b981; font-weight: bold;"
    if val == "DOWN":
        return "color: #ef4444; font-weight: bold;"
    return "color: #6b7280; font-weight: bold;"


styled = df_readings.style.map(color_direction, subset=["Direction"])
st.dataframe(styled, hide_index=True, use_container_width=True)

st.divider()

# ---------- Radar chart ----------

col_radar, col_2x2 = st.columns(2)

with col_radar:
    st.subheader("Z-scores des indicateurs")

    categories = [r.indicator_name for r in all_readings]
    z_values = [r.z_score if r.z_score is not None else 0.0 for r in all_readings]

    # Close the loop for the radar
    categories_closed = categories + [categories[0]]
    z_values_closed = z_values + [z_values[0]]

    fig_radar = go.Figure()
    fig_radar.add_trace(
        go.Scatterpolar(
            r=z_values_closed,
            theta=categories_closed,
            fill="toself",
            fillcolor="rgba(59, 130, 246, 0.25)",
            line=dict(color="#3b82f6", width=2),
            name="Z-scores",
        )
    )
    # Reference line at z=0
    fig_radar.add_trace(
        go.Scatterpolar(
            r=[0] * len(categories_closed),
            theta=categories_closed,
            line=dict(color="#9ca3af", width=1, dash="dot"),
            name="Moyenne 5 ans",
            hoverinfo="skip",
        )
    )
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[-3.5, 3.5])),
        showlegend=False,
        height=400,
        margin=dict(t=20, b=20, l=20, r=20),
    )
    st.plotly_chart(fig_radar, use_container_width=True)
    st.caption(
        "Une valeur positive (négative) signifie que l'indicateur est au-dessus "
        "(en-dessous) de sa moyenne 5 ans glissants. Le seuil de direction est ±0.5σ."
    )

with col_2x2:
    st.subheader("Framework 2x2")

    growth_dir = signal.growth_signal.direction.value
    inflation_dir = signal.inflation_signal.direction.value

    fig_2x2 = go.Figure()

    # Background quadrants with regime labels
    quadrants = [
        # (x_range, y_range, regime_label, regime_value)
        ((0, 1), (0, 1), "Disinfl. Récession", "disinflation_recession"),
        ((1, 2), (0, 1), "Stagflation", "stagflation"),
        ((0, 1), (1, 2), "Goldilocks", "goldilocks"),
        ((1, 2), (1, 2), "Reflation", "reflation"),
    ]

    current_regime = signal.regime.value
    for (x_rng, y_rng, label, regime_v) in quadrants:
        is_current = regime_v == current_regime
        opacity = 0.4 if is_current else 0.08
        c = regime_color(regime_v)
        fig_2x2.add_shape(
            type="rect",
            x0=x_rng[0],
            y0=y_rng[0],
            x1=x_rng[1],
            y1=y_rng[1],
            fillcolor=c,
            opacity=opacity,
            line=dict(color="#cccccc", width=1),
        )
        fig_2x2.add_annotation(
            x=(x_rng[0] + x_rng[1]) / 2,
            y=(y_rng[0] + y_rng[1]) / 2,
            text=f"<b>{label}</b>",
            showarrow=False,
            font=dict(size=13, color=c if is_current else "#888"),
        )

    # Marker for the current point (based on direction scores)
    x_pos = (
        1.5
        if inflation_dir == "up"
        else 0.5
        if inflation_dir == "down"
        else 1.0
    )
    y_pos = (
        1.5 if growth_dir == "up" else 0.5 if growth_dir == "down" else 1.0
    )

    fig_2x2.add_trace(
        go.Scatter(
            x=[x_pos],
            y=[y_pos],
            mode="markers",
            marker=dict(size=18, color="#1f2937", line=dict(width=2, color="white")),
            hovertext=f"Position courante : {regime_label}",
            hoverinfo="text",
            showlegend=False,
        )
    )

    fig_2x2.update_xaxes(
        range=[0, 2],
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        title="Inflation →",
    )
    fig_2x2.update_yaxes(
        range=[0, 2],
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        title="Croissance →",
    )
    fig_2x2.update_layout(
        height=400,
        margin=dict(t=20, b=40, l=40, r=20),
        plot_bgcolor="white",
    )
    st.plotly_chart(fig_2x2, use_container_width=True)
    st.caption(
        "Les axes représentent les directions des deux dimensions macro. "
        "La position du marqueur reflète la classification courante."
    )

st.divider()

# ---------- Détail par dimension ----------

st.subheader("Détail par dimension")

col_g, col_i = st.columns(2)

for col, dim_signal, label in [
    (col_g, signal.growth_signal, "Croissance"),
    (col_i, signal.inflation_signal, "Inflation"),
]:
    with col:
        st.markdown(f"### {label}")
        st.metric(
            label="Direction",
            value=dim_signal.direction.value.upper(),
            delta=f"score {dim_signal.score:+.2f}",
            delta_color="off",
        )
        st.metric(
            label="Confidence agrégée",
            value=f"{dim_signal.confidence:.0%}",
            help=(
                "Confidence = |score| × moyenne(confidences individuelles). "
                "Pénalise à la fois la divergence directionnelle et la faiblesse "
                "des signaux individuels."
            ),
        )

        with st.expander(f"Indicateurs contribuant à la dimension {label}"):
            for r in dim_signal.contributing_readings:
                z = f"{r.z_score:+.2f}" if r.z_score is not None else "n/a"
                st.write(
                    f"**{r.indicator_name}** — valeur {r.value:+.2f}, "
                    f"z = {z}, direction **{r.direction.value.upper()}**, "
                    f"confidence {r.confidence:.0%}"
                )

st.divider()

st.caption(
    "Méthodologie détaillée dans le "
    "[white paper](https://github.com/TTB10/bordeaux-multi-asset-lab/blob/main/docs/white_paper.md) "
    "(sections 4.2 et suivantes)."
)