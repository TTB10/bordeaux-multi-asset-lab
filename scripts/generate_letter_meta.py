"""Helper interactif pour générer le fichier meta.json d'une nouvelle lettre BML.

Usage :
    python scripts/generate_letter_meta.py

Le script demande les valeurs nécessaires en interactif puis écrit le fichier
dans docs/letters/YYYY-MM_BML_letter_meta.json.

Convention : à utiliser une fois que tu as généré le PDF de la lettre, juste
avant de la pousser sur GitHub.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path


LETTERS_DIR = Path(__file__).resolve().parents[1] / "docs" / "letters"


REGIME_CHOICES = {
    "1": "Goldilocks",
    "2": "Reflation",
    "3": "Disinflation_Recession",
    "4": "Stagflation",
    "5": "Uncertain",
}


def prompt_float(label: str, example: str = "") -> float:
    """Demande un float à l'utilisateur."""
    while True:
        suffix = f" (ex: {example})" if example else ""
        raw = input(f"{label}{suffix} : ").strip().replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            print("  Valeur invalide, recommencez.")


def prompt_int(label: str, example: str = "") -> int:
    """Demande un int à l'utilisateur."""
    while True:
        suffix = f" (ex: {example})" if example else ""
        raw = input(f"{label}{suffix} : ").strip()
        try:
            return int(raw)
        except ValueError:
            print("  Valeur invalide, recommencez.")


def prompt_str(label: str, example: str = "") -> str:
    """Demande une string à l'utilisateur."""
    suffix = f" (ex: {example})" if example else ""
    return input(f"{label}{suffix} : ").strip()


def prompt_regime() -> str:
    """Demande le régime à l'utilisateur."""
    print("\nRégimes disponibles :")
    for key, name in REGIME_CHOICES.items():
        print(f"  {key} = {name}")
    while True:
        choice = input("Régime (1-5) : ").strip()
        if choice in REGIME_CHOICES:
            return REGIME_CHOICES[choice]
        print("  Choix invalide, entrez 1, 2, 3, 4 ou 5.")


def main() -> None:
    print("\n" + "=" * 60)
    print("Génération du fichier meta.json — Lettre Mensuelle BML")
    print("=" * 60 + "\n")

    # Identité de la lettre
    number = prompt_int("Numéro de la lettre", "1")
    year = prompt_int("Année", "2026")
    month = prompt_int("Mois (1-12)", "7")

    # Construction des labels
    publication_date = f"{year:04d}-{month:02d}-05"
    month_names_fr = {
        1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
        5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
        9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre",
    }
    month_label = f"{month_names_fr[month]} {year}"
    print(f"\n→ Date de publication : {publication_date}")
    print(f"→ Label du mois : {month_label}")

    # Contenu éditorial
    print("\n--- Contenu éditorial ---")
    tagline = prompt_str("Tagline (entre guillemets internes au PDF)")
    key_message = prompt_str("Message clé (1-2 phrases)")

    # Régime et indicateurs
    print("\n--- Régime macro ---")
    regime = prompt_regime()
    regime_confidence = prompt_float("Confidence du régime (0.00 à 1.00)", "0.06")

    # Performance
    print("\n--- Performance ---")
    perf_cumul = prompt_float("Performance cumulée 3 ans BML (0.2584 = +25.84%)", "0.2584")
    perf_bench = prompt_float("Performance cumulée 3 ans Benchmark", "0.2137")
    sharpe = prompt_float("Ratio de Sharpe 3 ans", "3.26")
    vol = prompt_float("Volatilité annualisée 3 ans (0.0715 = 7.15%)", "0.0715")
    mdd = prompt_float("Max Drawdown 3 ans (négatif, -0.0548 = -5.48%)", "-0.0548")

    # Construction du dict final
    meta = {
        "number": number,
        "month_label": month_label,
        "publication_date": publication_date,
        "tagline": tagline,
        "regime": regime,
        "regime_confidence": regime_confidence,
        "performance_3y_cumulative": perf_cumul,
        "performance_3y_benchmark": perf_bench,
        "sharpe_3y": sharpe,
        "volatility_3y": vol,
        "max_drawdown_3y": mdd,
        "key_message": key_message,
    }

    # Écriture du fichier
    filename = f"{year:04d}-{month:02d}_BML_letter_meta.json"
    out_path = LETTERS_DIR / filename

    LETTERS_DIR.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Fichier généré : {out_path}")
    print("\nN'oublie pas de :")
    print(f"  1. Pousser aussi le PDF associé : docs/letters/{year:04d}-{month:02d}_BML_letter.pdf")
    print(f"  2. git add docs/letters/{year:04d}-{month:02d}_BML_letter*")
    print("  3. git commit -m 'docs: add monthly letter {month_label}'")
    print("  4. git push origin main")


if __name__ == "__main__":
    main()
