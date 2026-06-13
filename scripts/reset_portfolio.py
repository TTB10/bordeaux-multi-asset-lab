"""Script de reset sécurisé du portefeuille.

Usage:
    # Voir ce qui va se passer sans rien modifier :
    python scripts/reset_portfolio.py

    # Reset effectif (avec backup automatique) :
    python scripts/reset_portfolio.py --confirm

Le script :
    1. Vérifie que portfolio_latest.json existe
    2. Affiche les infos de l'état actuel (date inception, NAV, positions)
    3. Demande confirmation explicite
    4. Crée un backup horodaté
    5. Supprime portfolio_latest.json

À la prochaine ouverture de l'app Streamlit, un nouveau portefeuille sera
automatiquement initialisé avec les prix du jour, comme première fois.
"""

from __future__ import annotations

import argparse
import sys

from bml.portfolio.persistence import (
    DEFAULT_PORTFOLIO_PATH,
    backup_portfolio_state,
    load_portfolio_state,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reset le portefeuille (avec backup automatique)."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirme le reset. Sans ce flag, le script est en mode 'dry-run'.",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("RESET PORTEFEUILLE - Bordeaux Multi-Asset Lab")
    print("=" * 70)

    # Étape 1 : vérifier que le fichier existe
    if not DEFAULT_PORTFOLIO_PATH.exists():
        print(f"\n[INFO] Aucun portefeuille à reset.")
        print(f"       Le fichier {DEFAULT_PORTFOLIO_PATH} n'existe pas.")
        print(f"       Un nouveau portefeuille sera créé au prochain lancement.")
        return 0

    # Étape 2 : charger l'état actuel pour info
    state = load_portfolio_state()
    if state is None:
        print(f"\n[ERREUR] Impossible de lire l'état actuel.")
        return 1

    print(f"\nÉtat actuel du portefeuille :")
    print(f"  - Inception      : {state.inception_date}")
    print(f"  - Date d'arrêté  : {state.as_of}")
    print(f"  - Capital init.  : {state.inception_value:,.0f} €")
    print(f"  - Valeur totale  : {state.total_value:,.0f} €")
    print(f"  - NAV par part   : {state.nav_per_share:.2f}")
    print(f"  - Cash résiduel  : {state.cash:,.2f} €")
    print(f"  - Positions      : {len(state.positions)}")

    # Étape 3 : mode dry-run vs confirm
    if not args.confirm:
        print(f"\n[DRY-RUN] Mode simulation. Aucune modification effectuée.")
        print(f"\nPour exécuter le reset réel :")
        print(f"  python scripts/reset_portfolio.py --confirm")
        return 0

    # Étape 4 : backup
    print(f"\n[ACTION] Création du backup...")
    backup_path = backup_portfolio_state()
    if backup_path is None:
        print(f"  [ERREUR] Backup échoué.")
        return 1
    print(f"  Backup créé : {backup_path}")

    # Étape 5 : suppression
    print(f"\n[ACTION] Suppression du portefeuille actuel...")
    DEFAULT_PORTFOLIO_PATH.unlink()
    print(f"  Fichier supprimé : {DEFAULT_PORTFOLIO_PATH}")

    print(f"\n[OK] Reset effectué.")
    print(f"     Au prochain lancement de Streamlit, un nouveau portefeuille")
    print(f"     sera initialisé avec les prix du jour.")
    print(f"     Le backup reste disponible pour restauration si besoin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
