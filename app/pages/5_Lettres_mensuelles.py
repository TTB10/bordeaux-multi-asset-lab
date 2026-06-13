"""Page Streamlit pour afficher les lettres mensuelles BML.

Version 2 : utilise des composants Streamlit natifs (st.metric, st.container)
au lieu de HTML custom pour garantir un rendu propre sur toutes versions.

Convention de fichiers :
- PDF : docs/letters/YYYY-MM_BML_letter.pdf
- Meta : docs/letters/YYYY-MM_BML_letter_meta.json
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st


# ============================================================================
# Configuration et helpers
# ============================================================================

LETTERS_DIR = Path(__file__).parents[2] / "docs" / "letters"


def load_letters() -> list[dict]:
    """Charge toutes les lettres disponibles, triées par date décroissante."""
    letters = []

    if not LETTERS_DIR.exists():
        return letters

    for meta_path in LETTERS_DIR.glob("*_meta.json"):
        try:
            with meta_path.open("r", encoding="utf-8") as f:
                meta = json.load(f)

            pdf_filename = meta_path.name.replace("_meta.json", ".pdf")
            pdf_path = meta_path.parent / pdf_filename

            if not pdf_path.exists():
                continue

            letters.append(
                {
                    "meta": meta,
                    "pdf_path": pdf_path,
                    "publication_date": meta.get("publication_date", ""),
                }
            )
        except (json.JSONDecodeError, KeyError):
            continue

    letters.sort(key=lambda x: x["publication_date"], reverse=True)
    return letters


def format_pct(value: float, with_sign: bool = True) -> str:
    """Formate un float en pourcentage."""
    sign = "+" if with_sign and value > 0 else ""
    return f"{sign}{value * 100:.2f}%"


def regime_label_fr(regime: str) -> str:
    """Retourne le label français d'un régime."""
    labels = {
        "Goldilocks": "Goldilocks",
        "Reflation": "Reflation",
        "Disinflation_Recession": "Désinflation Récession",
        "Stagflation": "Stagflation",
        "Uncertain": "Incertain",
    }
    return labels.get(regime, regime)


def regime_emoji(regime: str) -> str:
    """Retourne un emoji associé à un régime."""
    emojis = {
        "Goldilocks": "🟢",
        "Reflation": "🟡",
        "Disinflation_Recession": "🔵",
        "Stagflation": "🔴",
        "Uncertain": "⚪",
    }
    return emojis.get(regime, "⚪")


# ============================================================================
# CSS minimal pour le bandeau d'en-tête uniquement
# ============================================================================

HEADER_CSS = """
<style>
.letter-header {
    background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
    color: white;
    padding: 22px 26px;
    border-radius: 8px;
    margin-bottom: 18px;
}
.letter-header-flex {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
}
.letter-number {
    font-size: 11pt;
    opacity: 0.85;
    margin-bottom: 4px;
}
.letter-title {
    font-size: 22pt;
    font-weight: 700;
    margin: 0;
}
.letter-date-label {
    font-size: 10pt;
    opacity: 0.85;
}
.letter-date-value {
    font-size: 12pt;
    font-weight: 600;
}
.letter-tagline {
    font-style: italic;
    color: #1e3a8a;
    font-size: 13pt;
    padding: 10px 16px;
    border-left: 4px solid #3b82f6;
    background-color: #eff6ff;
    margin: 14px 0 18px 0;
    border-radius: 4px;
}
</style>
"""

# ============================================================================
# Affichage de la page
# ============================================================================

st.set_page_config(
    page_title="Lettres Mensuelles | Bordeaux Multi-Asset Lab",
    page_icon="📨",
    layout="wide",
)

st.markdown(HEADER_CSS, unsafe_allow_html=True)

st.title("📨 Lettres Mensuelles")

st.markdown(
    """
    Chaque mois, Bordeaux Multi-Asset Lab publie une lettre d'investissement
    présentant le régime macroéconomique détecté, l'allocation cible
    et la performance du portefeuille. Les lettres sont archivées et téléchargeables
    au format PDF.
    """
)

st.markdown("---")

letters = load_letters()

if not letters:
    st.info(
        "Aucune lettre publiée pour l'instant. "
        "La première édition paraîtra le 5 juillet 2026."
    )
else:
    plural = "s" if len(letters) > 1 else ""
    st.markdown(f"### {len(letters)} lettre{plural} publiée{plural}")
    st.markdown("")

    for idx, letter in enumerate(letters):
        meta = letter["meta"]
        pdf_path = letter["pdf_path"]

        regime = meta.get("regime", "Uncertain")
        regime_fr = regime_label_fr(regime)
        regime_em = regime_emoji(regime)

        # Bandeau d'en-tête bleu
        header_html = f"""
        <div class="letter-header">
            <div class="letter-header-flex">
                <div>
                    <div class="letter-number">Lettre N°{meta.get('number', '?')}</div>
                    <div class="letter-title">{meta.get('month_label', 'Mois inconnu')}</div>
                </div>
                <div style="text-align: right;">
                    <div class="letter-date-label">Publiée le</div>
                    <div class="letter-date-value">{meta.get('publication_date', '')}</div>
                </div>
            </div>
        </div>
        """
        st.markdown(header_html, unsafe_allow_html=True)

        # Tagline
        tagline = meta.get("tagline", "")
        if tagline:
            st.markdown(
                f'<div class="letter-tagline">« {tagline} »</div>',
                unsafe_allow_html=True,
            )

        # Métriques en composants Streamlit natifs (4 colonnes)
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            confidence = meta.get("regime_confidence", 0)
            st.metric(
                label="Régime du mois",
                value=f"{regime_em} {regime_fr}",
                delta=f"Confidence : {confidence * 100:.0f}%",
                delta_color="off",
            )

        with col2:
            perf_bml = meta.get("performance_3y_cumulative", 0)
            perf_bench = meta.get("performance_3y_benchmark", 0)
            spread = perf_bml - perf_bench
            st.metric(
                label="Performance 3 ans",
                value=format_pct(perf_bml),
                delta=f"vs 60/40 : {format_pct(spread)}",
                delta_color="normal" if spread > 0 else "inverse",
            )

        with col3:
            sharpe = meta.get("sharpe_3y", 0)
            st.metric(
                label="Ratio Sharpe",
                value=f"{sharpe:.2f}",
                delta="sur 3 ans glissants",
                delta_color="off",
            )

        with col4:
            vol = meta.get("volatility_3y", 0)
            st.metric(
                label="Volatilité",
                value=f"{vol * 100:.2f}%",
                delta="annualisée",
                delta_color="off",
            )

        # Message clé en st.info (composant natif)
        key_message = meta.get("key_message", "")
        if key_message:
            st.info(f"**Message clé :** {key_message}")

        # Bouton de téléchargement
        col_a, col_b, col_c = st.columns([1, 2, 1])
        with col_b:
            with pdf_path.open("rb") as f:
                pdf_bytes = f.read()
            st.download_button(
                label=f"📥 Télécharger la lettre — {meta.get('month_label', '')}",
                data=pdf_bytes,
                file_name=pdf_path.name,
                mime="application/pdf",
                use_container_width=True,
                key=f"download_{idx}_{meta.get('publication_date', '')}",
            )

        # Séparation entre les lettres
        if idx < len(letters) - 1:
            st.markdown("---")
        else:
            st.markdown("")

# Section méthodologique en bas de page
st.markdown("---")

with st.expander("À propos des lettres mensuelles"):
    st.markdown(
        """
        Les lettres mensuelles de Bordeaux Multi-Asset Lab sont publiées **le 5 de chaque mois**
        (ou le premier jour ouvré suivant). Elles documentent en transparence :

        - Le **régime macroéconomique détecté** et la confidence associée
        - Les **six indicateurs FRED** qui ont conduit à cette classification
        - L'**allocation cible** par classe d'actifs
        - La **performance simulée** sur 3 ans glissants vs benchmark 60/40
        - Un **commentaire qualitatif** sur l'environnement de marché

        Toutes les lettres sont archivées et restent téléchargeables sans limitation
        de durée. Le track record vivant qu'elles constituent permet de valider
        ou d'invalider la robustesse du framework au fil du temps.

        **Disclaimer** : ces lettres sont des documents pédagogiques. Elles ne constituent
        pas un conseil en investissement. Les performances simulées passées ne préjugent
        pas des performances futures.
        """
    )
