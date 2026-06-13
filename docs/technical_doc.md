---
title: "Bordeaux Multi-Asset Lab"
subtitle: "Documentation technique"
author: "TTB10"
date: "Mai 2026"
geometry: margin=2cm
fontsize: 10pt
colorlinks: true
linkcolor: "blue"
urlcolor: "blue"
toc: true
toc-depth: 3
numbersections: true
---

\newpage

# À propos de cette documentation

Cette documentation est la référence technique du framework *Bordeaux Multi-Asset Lab*. Elle s'adresse aux développeurs Python intermédiaires qui souhaitent comprendre, utiliser, ou contribuer au code source.

Pour la **méthodologie financière** et la justification théorique des choix, consulter le [white paper](white_paper.md). Pour une **vue produit** du framework, consulter le [README](../README.md).

## Comment naviguer cette documentation

La documentation est organisée en quatre parties.

**Partie I — Démarrage rapide** : installation, configuration, première exécution. À lire en priorité si vous découvrez le projet.

**Partie II — Architecture** : vue d'ensemble du système, patterns transverses, conventions de code. À lire avant de plonger dans un module spécifique.

**Partie III — Référence des modules** : description détaillée de chaque module (`data`, `universe`, `regime`, `allocation`, `selection`, `risk`, `portfolio`), avec signatures de classes, exemples d'usage, et choix de design. À consulter ponctuellement selon le besoin.

**Partie IV — Opérations et contribution** : configuration, tests, workflow de contribution, troubleshooting. À lire avant de modifier le code ou de l'utiliser en condition réelle.

## Conventions

- Les **noms de modules** apparaissent en `monospace` (par exemple `regime`).
- Les **noms de classes** apparaissent en `MonospaceCamelCase` (par exemple `RegimeBasedTacticalStrategy`).
- Les blocs de code Python sont annotés du langage pour syntax highlighting.
- Les notes importantes sont signalées par **Note**, les avertissements par **Attention**, et les exemples par **Exemple**.

\newpage

# Partie I — Démarrage rapide

## Prérequis

Le framework requiert :

- **Python 3.12 ou supérieur**
- **uv** (gestionnaire de paquets et environnements virtuels). [Installation officielle](https://docs.astral.sh/uv/getting-started/installation/).
- **Git** pour cloner le dépôt
- Une **clé API FRED** (gratuite, demandable sur `https://fred.stlouisfed.org/docs/api/api_key.html`)

L'usage d'`uv` plutôt que `pip` ou `poetry` est intentionnel : `uv` est significativement plus rapide (typiquement 10-50x sur les opérations de résolution de dépendances), et son intégration avec PEP 723 simplifie la gestion des scripts standalone.

## Installation

```bash
git clone https://github.com/TTB10/bordeaux-multi-asset-lab.git
cd bordeaux-multi-asset-lab
uv sync --all-extras
```

La commande `uv sync` installe automatiquement les dépendances déclarées dans `pyproject.toml`, crée un environnement virtuel local dans `.venv/`, et configure les outils de développement (ruff, mypy, pytest).

Pour vérifier que l'installation est correcte :

```bash
uv run pytest
```

Tous les tests doivent passer (161 tests à la date de cette documentation).

## Configuration de la clé API FRED

Créer un fichier `.env` à la racine du projet :

```ini
FRED_API_KEY=votre_clé_ici
```

**Attention** : ce fichier est listé dans `.gitignore` et ne doit jamais être commité. Toute exposition de la clé API en clair sur GitHub doit être traitée comme une fuite de credential et la clé doit être révoquée immédiatement sur le portail FRED.

## Première exécution

Trois scripts de démonstration sont fournis dans le dossier `scripts/` :

| Script | Description |
|---|---|
| `demo_all_indicators.py` | Affiche les 6 indicateurs macro et le régime classifié |
| `demo_allocation.py` | Calcule l'allocation cible à partir du régime détecté |
| `demo_portfolio.py` | Pipeline complet : régime → allocation → sélection + métriques de risque |
| `demo_portfolio_simulation.py` | Initialise un portefeuille avec 100 000 € et le persiste sur disque |

**Exemple** : pour voir l'état actuel du système, exécuter :

```bash
uv run python scripts/demo_portfolio.py
```

Le script télécharge les prix Yahoo des 49 ETFs UCITS de l'univers, interroge FRED pour les 6 indicateurs macro, calcule le régime, dérive l'allocation cible, sélectionne les fonds par scoring composite, et calcule les 7 métriques de risque versus un benchmark 60/40. Durée typique : 60 à 90 secondes.

\newpage

# Partie II — Architecture

## Vue d'ensemble

Le framework est structuré en sept modules indépendants avec une responsabilité unique chacun. Le pipeline exécute ces modules en séquence linéaire.

```
+---------------+      +----------------+
| universe.yaml |      | .env           |
+---------------+      +----------------+
       |                       |
       v                       v
+---------------+      +----------------+
|   universe    |      |     data       |
|   loader      |      |   providers    |
+---------------+      +----------------+
       |                       |
       +-----------+-----------+
                   |
                   v
       +-------------------------+
       |  regime detector        |
       |  (6 indicators -> 5     |
       |   regimes + confidence) |
       +-------------------------+
                   |
                   v
       +-------------------------+
       |  allocation strategy    |
       |  (smoothing by          |
       |   confidence)           |
       +-------------------------+
                   |
                   v
       +-------------------------+
       |  selection strategy     |
       |  (top-N composite       |
       |   scoring)              |
       +-------------------------+
                   |
                   v
       +-------------------------+
       |  portfolio simulator    |
       |  (state + persistence)  |
       +-------------------------+
                   |
                   v
       +-------------------------+
       |  risk calculator        |
       |  (7 empirical metrics)  |
       +-------------------------+
```

## Patterns transverses

### Pattern Stratégie

Le pattern Stratégie est utilisé dans **quatre modules** pour découpler les abstractions des implémentations. Il prend toujours la même forme :

```python
from abc import ABC, abstractmethod

class XxxStrategy(ABC):
    @abstractmethod
    def operation(self, ...) -> ResultType:
        """Strategy interface."""

class ConcreteStrategyV1(XxxStrategy):
    def operation(self, ...) -> ResultType:
        # implementation
```

Les classes concrètes sont injectables via les constructeurs des classes appelantes. Cette architecture permet de substituer une implémentation sans modifier le code client.

**Liste des stratégies** :

| Module | ABC | Implémentation V1 |
|---|---|---|
| `regime` | `RegimeDetector` | `RuleBasedRegimeDetector` |
| `regime` | `DimensionAggregator` | `WeightedVoteAggregator` |
| `regime.indicators` | `MacroIndicator` | 6 implémentations concrètes |
| `allocation` | `AllocationStrategy` | `RegimeBasedTacticalStrategy` |
| `selection` | `SelectionStrategy` | `TopNPerBucketStrategy` |
| `selection` | `AssetScorer` | `CompositeScorer` |
| `risk` | `RiskCalculator` | `HistoricalRiskCalculator` |
| `data.providers` | `DataProvider` | `YFinanceProvider` |
| `data.providers` | `MacroDataProvider` | `FREDProvider` |

### Modèles Pydantic frozen

Tous les objets de domaine sont des `BaseModel` Pydantic avec `frozen=True` et `extra="forbid"`. Cette configuration garantit :

- **Immutabilité** : aucune mutation accidentelle d'un état partagé
- **Validation au constructeur** : les contraintes (types, ranges, formats) sont vérifiées immédiatement à l'instantiation
- **Sérialisation JSON gratuite** via `model_dump_json()` et `model_validate_json()`
- **Détection des fautes de frappe** : un attribut nommé incorrectement lève une `ValidationError` plutôt que d'être silencieusement ajouté

**Exemple** :

```python
from pydantic import BaseModel, ConfigDict, Field

class Asset(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    ticker: str
    isin: str = Field(min_length=12, max_length=12)
    name: str
    asset_class: AssetClass
    region: Region
    currency: str = Field(min_length=3, max_length=3)
    ter: float = Field(ge=0.0, le=0.05)
```

Toute tentative de créer un `Asset` avec un ISIN de longueur incorrecte, un currency code de longueur autre que 3, ou un TER hors de [0, 5%] lève immédiatement une exception.

### Conventions de code

Le projet respecte les conventions Python modernes :

- **Type hints partout** : tous les paramètres et valeurs de retour sont typés. Le mode strict de mypy est activé.
- **Imports explicites** : pas de `from module import *`. Les imports relatifs sont évités.
- **Docstrings Google-style** : sections `Args`, `Returns`, `Raises`, `Example`.
- **Nommage** : `snake_case` pour fonctions et variables, `PascalCase` pour classes, `UPPER_SNAKE_CASE` pour constantes de module.
- **Formatage automatique** : `ruff format` avant chaque commit.

\newpage

# Partie III — Référence des modules

## Module `data`

### Responsabilité

Acquisition des données externes :

- Prix d'actifs depuis Yahoo Finance
- Séries macroéconomiques depuis la base FRED de la Réserve fédérale de Saint-Louis

Les providers sont conçus pour être robustes aux pannes transitoires des API externes via un mécanisme de retry-and-backoff.

### Structure

```
src/bml/data/
├── __init__.py
├── prices.py              # PriceLoader: orchestration de fetch d'univers
└── providers/
    ├── __init__.py
    ├── base.py            # DataProvider ABC
    ├── macro_base.py      # MacroDataProvider ABC
    ├── yfinance_provider.py
    └── fred_provider.py
```

### Classes principales

#### `DataProvider` (ABC)

Interface pour les providers de prix d'actifs.

```python
from abc import ABC, abstractmethod
from datetime import date
import pandas as pd

class DataProvider(ABC):
    @abstractmethod
    def fetch_prices(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> pd.DataFrame:
        """Fetch close prices for multiple tickers.
        
        Returns:
            DataFrame indexed by date, one column per ticker. Missing
            data is represented as NaN.
        """
```

#### `YFinanceProvider`

Implémentation pour Yahoo Finance, basée sur la bibliothèque `yfinance`.

```python
class YFinanceProvider(DataProvider):
    def __init__(self, max_workers: int = 4) -> None:
        self._max_workers = max_workers
    
    def fetch_prices(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> pd.DataFrame:
        # Bulk fetch via yfinance with fallback per-ticker
```

**Détails d'implémentation** :

- Utilise un fetch en bulk par défaut pour la performance
- Fallback automatique sur fetch ticker-par-ticker en cas d'erreur du bulk
- Gère les tickers avec des suffixes d'exchange (`.L`, `.AS`, `.DE`) sans configuration spéciale
- Filtre automatiquement les colonnes 'Adj Close' pour ne retourner que 'Close'

**Limites connues** :

- Le bulk fetch peut produire des écarts d'environ 1 % par rapport au fetch individuel pour certains tickers (NDIA.L observé). Documenté dans `docs/known_issues.md`.
- Pas de retry automatique : Yahoo Finance est généralement stable, et les erreurs résiduelles sont rares en pratique.

#### `MacroDataProvider` (ABC)

Interface pour les providers de séries macroéconomiques.

```python
class MacroDataProvider(ABC):
    @abstractmethod
    def fetch_series(
        self,
        series_id: str,
        start: date,
        end: date,
    ) -> pd.Series:
        """Fetch a single time series.
        
        Returns:
            Series indexed by date.
        
        Raises:
            MacroDataProviderError: If the request fails after retries.
        """
```

#### `FREDProvider`

Implémentation pour la base FRED, avec retry-and-backoff.

```python
class FREDProvider(MacroDataProvider):
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF_BASE_SECONDS = 1.0
    RETRYABLE_HTTP_CODES = (500, 502, 503, 504)
    
    def __init__(
        self,
        api_key: str | None = None,
        client: Any | None = None,
        max_retries: int | None = None,
        backoff_base_seconds: float | None = None,
    ) -> None:
        ...
```

**Comportement** :

- Si `api_key` est `None`, lit la variable d'environnement `FRED_API_KEY` (avec `python-dotenv`)
- Distingue erreurs récupérables (HTTP 5xx, ValueError contenant "Internal Server Error") et fatales (HTTP 4xx, ValueError parsing)
- Retry jusqu'à `max_retries` fois avec backoff exponentiel : 1s, 2s, 4s par défaut
- Le paramètre `client` permet d'injecter un mock pour les tests unitaires

**Exemple** :

```python
from datetime import date
from bml.data.providers import FREDProvider

provider = FREDProvider()  # lit FRED_API_KEY depuis .env
series = provider.fetch_series("T10Y3M", date(2020, 1, 1), date(2026, 5, 1))
print(series.tail())
```

#### `PriceLoader`

Orchestrateur qui fetch les prix d'un univers complet.

```python
class PriceLoader:
    def __init__(self, provider: DataProvider) -> None:
        self._provider = provider
    
    def fetch_universe(
        self,
        universe: Universe,
        start: date,
        end: date,
    ) -> PriceFetchResult:
        """Fetch prices for all assets in the universe."""
```

`PriceFetchResult` contient :

- `prices: pd.DataFrame` — les prix obtenus, indexés par date
- `successful: list[str]` — tickers fetched avec succès
- `failed: dict[str, str]` — tickers en échec avec leur message d'erreur

\newpage

## Module `universe`

### Responsabilité

Représentation de l'univers d'investissement (49 ETFs UCITS européens) chargé depuis un fichier YAML versionné.

### Structure

```
src/bml/universe/
├── __init__.py
├── asset.py        # Asset (Pydantic), AssetClass enum, Region enum
├── universe.py     # Universe class
└── loader.py       # UniverseLoader
```

### Classes principales

#### `AssetClass`

```python
from enum import StrEnum

class AssetClass(StrEnum):
    EQUITY_DM = "equity_developed_markets"
    EQUITY_EM = "equity_emerging_markets"
    GOVERNMENT_BOND = "government_bond"
    CREDIT_IG = "credit_investment_grade"
    CREDIT_HY = "credit_high_yield"
    CONVERTIBLE_BOND = "convertible_bond"
    GOLD = "gold"
    SILVER = "silver"
    COMMODITY = "broad_commodity"
    REAL_ESTATE = "real_estate"
    HEDGED = "hedged"
    CASH = "cash"
    INFLATION_PROTECTED = "inflation_protected"
```

**Note** : `StrEnum` (introduit en Python 3.11) permet de comparer des valeurs avec des strings directement et d'avoir des sérialisations JSON naturelles.

#### `Region`

```python
class Region(StrEnum):
    GLOBAL = "global"
    US = "us"
    EUROPE = "europe"
    UK = "uk"
    JAPAN = "japan"
    EMERGING = "emerging"
```

#### `Asset`

```python
class Asset(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    ticker: str
    isin: str = Field(min_length=12, max_length=12)
    name: str
    asset_class: AssetClass
    region: Region
    currency: str = Field(min_length=3, max_length=3)
    ter: float = Field(ge=0.0, le=0.05)
```

La contrainte `min_length=12, max_length=12` sur l'ISIN respecte la norme ISO 6166. La contrainte sur le TER limite les frais à 5 % maximum (au-delà, c'est probablement une erreur de saisie).

#### `Universe`

```python
class Universe:
    def __init__(self, assets: list[Asset]) -> None:
        self._assets = assets
        self._validate_no_duplicates()
    
    def __len__(self) -> int:
        return len(self._assets)
    
    @property
    def assets(self) -> list[Asset]:
        return list(self._assets)
    
    def by_class(self, asset_class: AssetClass) -> "Universe":
        """Return a sub-universe filtered by asset class."""
        return Universe([a for a in self._assets if a.asset_class == asset_class])
    
    def by_region(self, region: Region) -> "Universe":
        """Return a sub-universe filtered by region."""
        return Universe([a for a in self._assets if a.region == region])
    
    def get_by_ticker(self, ticker: str) -> Asset | None:
        for a in self._assets:
            if a.ticker == ticker:
                return a
        return None
```

#### `UniverseLoader`

```python
class UniverseLoader:
    DEFAULT_PATH = "src/bml/config/universe.yaml"
    
    @staticmethod
    def load(path: str | Path | None = None) -> Universe:
        """Load the universe from a YAML file.
        
        The YAML must have a top-level 'assets' key with a list of dicts.
        Each dict is validated through the Asset model.
        """
```

**Format du YAML** :

```yaml
assets:
  - ticker: "CSPX.L"
    isin: "IE00B5BMR087"
    name: "iShares Core S&P 500 UCITS"
    asset_class: "equity_developed_markets"
    region: "us"
    currency: "USD"
    ter: 0.0007
  
  - ticker: "IGLN.L"
    isin: "IE00B4ND3602"
    name: "iShares Physical Gold ETC"
    asset_class: "gold"
    region: "global"
    currency: "USD"
    ter: 0.0025
  
  # ... 47 autres
```

\newpage

## Module `regime`

### Responsabilité

Pipeline complet de détection de régime macroéconomique :

1. Calcul de 6 indicateurs avec normalisation z-score
2. Agrégation par dimension (Croissance, Inflation) avec vote pondéré par confidence
3. Classification du régime parmi 5 états

### Structure

```
src/bml/regime/
├── __init__.py
├── enums.py              # Direction, MacroDimension, Regime
├── models.py             # IndicatorReading, DimensionalSignal, RegimeSignal
├── _scoring.py           # compute_zscore_signal helper
├── aggregators.py        # DimensionAggregator + WeightedVoteAggregator
├── detector.py           # RegimeDetector + RuleBasedRegimeDetector
└── indicators/
    ├── __init__.py
    ├── base.py           # MacroIndicator ABC
    ├── yield_curve.py
    ├── industrial_production.py
    ├── jobless_claims.py
    ├── inflation_breakeven.py
    ├── core_cpi.py
    └── oil_momentum.py
```

### Modèles de données

#### `Direction`

```python
class Direction(StrEnum):
    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"
```

#### `MacroDimension`

```python
class MacroDimension(StrEnum):
    GROWTH = "growth"
    INFLATION = "inflation"
```

#### `Regime`

```python
class Regime(StrEnum):
    GOLDILOCKS = "goldilocks"
    REFLATION = "reflation"
    DISINFLATION_RECESSION = "disinflation_recession"
    STAGFLATION = "stagflation"
    UNCERTAIN = "uncertain"
    
    @staticmethod
    def from_directions(growth: Direction, inflation: Direction) -> "Regime":
        if growth == Direction.UP and inflation == Direction.DOWN:
            return Regime.GOLDILOCKS
        if growth == Direction.UP and inflation == Direction.UP:
            return Regime.REFLATION
        if growth == Direction.DOWN and inflation == Direction.DOWN:
            return Regime.DISINFLATION_RECESSION
        if growth == Direction.DOWN and inflation == Direction.UP:
            return Regime.STAGFLATION
        return Regime.UNCERTAIN
```

#### `IndicatorReading`

```python
class IndicatorReading(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    indicator_name: str
    dimension: MacroDimension
    as_of: date
    value: float                    # raw value (e.g. 0.74 for yield curve at +0.74%)
    z_score: float | None = None    # z-score over 5y window
    direction: Direction
    confidence: float = Field(ge=0.0, le=1.0)
```

#### `DimensionalSignal`

```python
class DimensionalSignal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    dimension: MacroDimension
    as_of: date
    direction: Direction
    score: float = Field(ge=-1.0, le=1.0)   # weighted aggregate
    confidence: float = Field(ge=0.0, le=1.0)
    contributing_readings: list[IndicatorReading]
```

#### `RegimeSignal`

```python
class RegimeSignal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    as_of: date
    regime: Regime
    growth_signal: DimensionalSignal
    inflation_signal: DimensionalSignal
    confidence: float = Field(ge=0.0, le=1.0)
```

### Indicateurs

Tous les indicateurs implémentent l'interface `MacroIndicator` :

```python
class MacroIndicator(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @property
    @abstractmethod
    def dimension(self) -> MacroDimension: ...
    
    @abstractmethod
    def fetch_history(self, end: date) -> pd.Series: ...
    
    @abstractmethod
    def read(self, as_of: date) -> IndicatorReading: ...
```

**Exemple d'implémentation : `YieldCurveIndicator`**

```python
class YieldCurveIndicator(MacroIndicator):
    SERIES_ID = "T10Y3M"
    LOOKBACK_YEARS = 5
    HISTORY_YEARS = 30
    
    def __init__(self, provider: MacroDataProvider) -> None:
        self._provider = provider
    
    @property
    def name(self) -> str:
        return "yield_curve_10y3m"
    
    @property
    def dimension(self) -> MacroDimension:
        return MacroDimension.GROWTH
    
    def fetch_history(self, end: date) -> pd.Series:
        start = date(end.year - self.HISTORY_YEARS, end.month, end.day)
        return self._provider.fetch_series(self.SERIES_ID, start, end)
    
    def read(self, as_of: date) -> IndicatorReading:
        raw = self.fetch_history(as_of).dropna()
        if raw.empty:
            raise ValueError(f"No data for {self.SERIES_ID}")
        
        signal = compute_zscore_signal(
            raw,
            as_of=as_of,
            lookback_years=self.LOOKBACK_YEARS,
            min_observations=60,
        )
        
        return IndicatorReading(
            indicator_name=self.name,
            dimension=self.dimension,
            as_of=as_of,
            value=signal.current_value,
            z_score=signal.z_score,
            direction=signal.direction,
            confidence=signal.confidence,
        )
```

Les autres indicateurs suivent le même pattern, avec des transformations spécifiques :

| Indicateur | Transformation pré-zscore | Sign inversé ? |
|---|---|:---:|
| `YieldCurveIndicator` | aucune | non |
| `IndustrialProductionIndicator` | YoY % change | non |
| `JoblessClaimsIndicator` | rolling 4-week mean | **oui** (claims up = growth down) |
| `InflationBreakevenIndicator` | aucune | non |
| `CoreCPIIndicator` | YoY % change | non |
| `OilMomentumIndicator` | 6-month % change | non |

### Helper de scoring

```python
def compute_zscore_signal(
    series: pd.Series,
    as_of: date,
    lookback_years: int = 5,
    min_observations: int = 60,
    direction_threshold: float = 0.5,
    invert_sign: bool = False,
) -> ZScoreSignal:
    """Compute z-score, direction, and confidence for a series at as_of.
    
    Args:
        series: Time series (must be sorted ascending).
        as_of: Reference date.
        lookback_years: Window for computing mean/std (default 5).
        min_observations: Minimum data points required.
        direction_threshold: Z-score threshold for UP/DOWN (default 0.5).
        invert_sign: If True, flip the direction (used for jobless claims).
    
    Returns:
        ZScoreSignal NamedTuple with current_value, z_score, direction, confidence.
    """
```

### Aggregator

```python
class WeightedVoteAggregator(DimensionAggregator):
    def __init__(self, score_threshold: float = 0.3) -> None:
        if not 0.0 <= score_threshold <= 1.0:
            raise ValueError("score_threshold must be in [0, 1]")
        self._threshold = score_threshold
    
    def aggregate(
        self,
        readings: list[IndicatorReading],
        dimension: MacroDimension,
        as_of: date,
    ) -> DimensionalSignal:
        # ... (see source for full implementation)
```

**Algorithme** :

1. Vérifier que toutes les readings sont de la même dimension
2. Calculer le score pondéré : `sum(direction_sign * confidence) / sum(confidence)`
3. Déterminer la direction : `score > threshold → UP`, `score < -threshold → DOWN`, sinon `NEUTRAL`
4. Calculer la confidence agrégée : `|score| × mean(individual_confidences)`

### Detector

```python
class RuleBasedRegimeDetector(RegimeDetector):
    def __init__(
        self,
        indicators: list[MacroIndicator],
        aggregator: DimensionAggregator | None = None,
    ) -> None:
        if not indicators:
            raise ValueError("at least one indicator required")
        self._indicators = list(indicators)
        self._aggregator = aggregator or WeightedVoteAggregator()
    
    def detect(self, as_of: date) -> RegimeSignal:
        # ... (full pipeline: read indicators -> aggregate -> classify)
```

**Comportement** :

- Si un indicateur lève une exception, il est loggé comme warning et ignoré (non bloquant)
- Si aucun indicateur n'a réussi pour une dimension, lève `RuntimeError`
- La confidence du régime est `min(growth_confidence, inflation_confidence)` (conservateur)

**Exemple complet** :

```python
from datetime import date
from dotenv import load_dotenv

from bml.data.providers import FREDProvider
from bml.regime import RuleBasedRegimeDetector
from bml.regime.indicators import (
    CoreCPIIndicator,
    IndustrialProductionIndicator,
    InflationBreakevenIndicator,
    JoblessClaimsIndicator,
    OilMomentumIndicator,
    YieldCurveIndicator,
)

load_dotenv()
fred = FREDProvider()

detector = RuleBasedRegimeDetector(
    indicators=[
        YieldCurveIndicator(fred),
        IndustrialProductionIndicator(fred),
        JoblessClaimsIndicator(fred),
        InflationBreakevenIndicator(fred),
        CoreCPIIndicator(fred),
        OilMomentumIndicator(fred),
    ]
)

signal = detector.detect(as_of=date.today())
print(f"Regime: {signal.regime.value} (confidence {signal.confidence:.0%})")
```

\newpage

## Module `allocation`

### Responsabilité

Transformer un `RegimeSignal` en une `TargetAllocation` (poids cibles par classe d'actifs), avec smoothing par confidence.

### Structure

```
src/bml/allocation/
├── __init__.py
├── models.py        # BucketWeight, TargetAllocation
├── tilts.py         # NEUTRAL_TILT + 4 regime tilts
└── strategy.py      # AllocationStrategy + RegimeBasedTacticalStrategy
```

### Modèles

#### `BucketWeight`

```python
class BucketWeight(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    asset_class: AssetClass
    weight: float = Field(ge=0.0, le=1.0)
```

#### `TargetAllocation`

```python
class TargetAllocation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    as_of: date
    buckets: list[BucketWeight] = Field(min_length=1)
    regime_label: str | None = None
    
    @model_validator(mode="after")
    def _check_unique_buckets(self) -> "TargetAllocation":
        # No duplicate AssetClass
    
    @model_validator(mode="after")
    def _check_weights_sum_to_one(self) -> "TargetAllocation":
        # Weights must sum to 1.0 within tolerance
    
    def weight_of(self, asset_class: AssetClass) -> float: ...
    def as_dict(self) -> dict[AssetClass, float]: ...
```

### Tables de tilts

Les tilts sont définis dans `tilts.py` comme des dictionnaires. Chacun somme à 1.0 par construction.

```python
NEUTRAL_TILT: dict[AssetClass, float] = {
    AssetClass.EQUITY_DM: 0.40,
    AssetClass.EQUITY_EM: 0.10,
    AssetClass.GOVERNMENT_BOND: 0.20,
    AssetClass.CREDIT_IG: 0.10,
    AssetClass.CREDIT_HY: 0.05,
    AssetClass.GOLD: 0.05,
    AssetClass.COMMODITY: 0.00,
    AssetClass.REAL_ESTATE: 0.05,
    AssetClass.CASH: 0.05,
}

GOLDILOCKS_TILT: dict[AssetClass, float] = {...}
REFLATION_TILT: dict[AssetClass, float] = {...}
DISINFLATION_RECESSION_TILT: dict[AssetClass, float] = {...}
STAGFLATION_TILT: dict[AssetClass, float] = {...}

DEFAULT_REGIME_TILTS: dict[Regime, dict[AssetClass, float]] = {
    Regime.GOLDILOCKS: GOLDILOCKS_TILT,
    Regime.REFLATION: REFLATION_TILT,
    Regime.DISINFLATION_RECESSION: DISINFLATION_RECESSION_TILT,
    Regime.STAGFLATION: STAGFLATION_TILT,
}
```

### Stratégie

```python
class RegimeBasedTacticalStrategy(AllocationStrategy):
    def __init__(
        self,
        regime_tilts: dict[Regime, dict[AssetClass, float]] | None = None,
        neutral_tilt: dict[AssetClass, float] | None = None,
    ) -> None:
        self._tilts = regime_tilts if regime_tilts is not None else DEFAULT_REGIME_TILTS
        self._neutral = neutral_tilt if neutral_tilt is not None else NEUTRAL_TILT
        self._validate_tilts()  # ensure each tilt sums to 1.0
    
    def compute(self, signal: RegimeSignal) -> TargetAllocation:
        if signal.regime == Regime.UNCERTAIN or signal.regime not in self._tilts:
            return self._build(self._neutral, signal.as_of, signal.regime.value)
        
        target = self._tilts[signal.regime]
        smoothed = self._interpolate(self._neutral, target, signal.confidence)
        return self._build(smoothed, signal.as_of, signal.regime.value)
    
    @staticmethod
    def _interpolate(neutral, target, confidence):
        all_classes = set(neutral) | set(target)
        return {
            ac: round(
                (1.0 - confidence) * neutral.get(ac, 0.0)
                + confidence * target.get(ac, 0.0),
                6,
            )
            for ac in all_classes
        }
```

**Exemple d'usage** :

```python
from bml.allocation import RegimeBasedTacticalStrategy

strategy = RegimeBasedTacticalStrategy()
target = strategy.compute(signal)

print(f"Régime: {target.regime_label}")
for bucket in target.buckets:
    print(f"  {bucket.asset_class.value}: {bucket.weight:.1%}")
```

### Personnalisation des tilts

L'injection de tilts personnalisés se fait via le constructeur :

```python
custom_tilts = {
    Regime.GOLDILOCKS: {
        AssetClass.EQUITY_DM: 0.55,
        AssetClass.GOVERNMENT_BOND: 0.20,
        # ... must sum to 1.0
    },
    # ... other regimes
}

custom_neutral = {
    AssetClass.EQUITY_DM: 0.45,
    # ...
}

strategy = RegimeBasedTacticalStrategy(
    regime_tilts=custom_tilts,
    neutral_tilt=custom_neutral,
)
```

Le constructeur valide que chaque table somme à 1.0 et lève `ValueError` sinon.

\newpage

## Module `selection`

### Responsabilité

Convertir une `TargetAllocation` (poids par classe d'actifs) en un `Portfolio` (poids par fond ETF concret), via scoring composite.

### Structure

```
src/bml/selection/
├── __init__.py
├── models.py        # PortfolioPosition, Portfolio
├── scorer.py        # AssetScorer + CompositeScorer
└── strategy.py      # SelectionStrategy + TopNPerBucketStrategy
```

### Modèles

#### `PortfolioPosition`

```python
class PortfolioPosition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    asset: Asset
    weight: float = Field(ge=0.0, le=1.0)
    bucket: AssetClass    # for traceability
    score: float          # composite score from selection
```

#### `Portfolio`

```python
class Portfolio(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    as_of: date
    positions: list[PortfolioPosition] = Field(min_length=1)
    target_allocation: TargetAllocation
    notes: list[str] = Field(default_factory=list)
    
    def total_weight_in(self, asset_class: AssetClass) -> float: ...
    def positions_in(self, asset_class: AssetClass) -> list[PortfolioPosition]: ...
    def as_dict(self) -> dict[str, float]: ...
```

### Scorer

```python
class AssetScorer(ABC):
    @abstractmethod
    def metrics(self, prices: pd.Series, asset: Asset) -> dict[str, float]:
        """Compute raw metrics. Higher = better convention."""

class CompositeScorer(AssetScorer):
    MIN_OBS = 60  # ~3 months
    
    def metrics(self, prices: pd.Series, asset: Asset) -> dict[str, float]:
        clean = prices.dropna()
        if len(clean) < self.MIN_OBS:
            return {"sharpe": 0.0, "neg_drawdown": 0.0, "neg_ter": -asset.ter}
        
        returns = clean.pct_change().dropna()
        sharpe = returns.mean() * 252.0 / (returns.std() * np.sqrt(252.0))
        
        cum = (1.0 + returns).cumprod()
        max_dd = (cum / cum.cummax() - 1.0).min()
        
        return {
            "sharpe": float(sharpe),
            "neg_drawdown": -abs(float(max_dd)),
            "neg_ter": -asset.ter,
        }
```

### Stratégie

```python
class TopNPerBucketStrategy(SelectionStrategy):
    DEFAULT_METRIC_WEIGHTS: ClassVar[dict[str, float]] = {
        "sharpe": 0.60,
        "neg_drawdown": 0.25,
        "neg_ter": 0.15,
    }
    
    def __init__(
        self,
        scorer: AssetScorer | None = None,
        n_per_bucket: int = 2,
        metric_weights: dict[str, float] | None = None,
    ) -> None:
        if n_per_bucket < 1:
            raise ValueError("n_per_bucket must be >= 1")
        self._scorer = scorer or CompositeScorer()
        self._n = n_per_bucket
        self._weights = metric_weights or dict(self.DEFAULT_METRIC_WEIGHTS)
    
    def select(
        self,
        target: TargetAllocation,
        universe: Universe,
        prices: pd.DataFrame,
    ) -> Portfolio:
        # 1. Detect missing buckets, reroute weight to cash
        # 2. For each remaining bucket: score candidates, take top N, equal-weight
        # 3. Renormalise final weights to sum exactly to 1.0
```

**Algorithme détaillé** :

1. **Filtrage** : pour chaque classe d'actifs allouée à plus de 0 %, sélectionner les ETFs candidats (présents dans l'univers et avec données de prix suffisantes — au moins 60 jours)

2. **Reroute si poche vide** : si une poche n'a aucun candidat, son poids est ajouté au cash et un avertissement est loggé

3. **Scoring** : pour chaque candidat, calculer les métriques brutes via `_scorer.metrics()`

4. **Z-normalisation** : au sein de chaque peer group (= ensemble des candidats d'une même classe d'actifs), normaliser chaque métrique en z-score

5. **Combinaison pondérée** : `score = 0.6 × z_sharpe + 0.25 × z_neg_drawdown + 0.15 × z_neg_ter`

6. **Top-N** : sélectionner les `n_per_bucket` candidats au plus haut score

7. **Équipondération intra-poche** : `weight_per_asset = bucket_target_weight / N_chosen`

8. **Renormalisation finale** : ajuster pour absorber les éventuelles dérives flottantes, en ajoutant le résiduel à la dernière position

**Exemple** :

```python
from bml.selection import TopNPerBucketStrategy
from bml.universe import UniverseLoader
from bml.data import PriceLoader
from bml.data.providers import YFinanceProvider

universe = UniverseLoader.load()
prices = PriceLoader(YFinanceProvider()).fetch_universe(
    universe, date(2023, 1, 1), date(2026, 5, 1)
).prices

strategy = TopNPerBucketStrategy(n_per_bucket=2)
portfolio = strategy.select(target_allocation, universe, prices)

for pos in portfolio.positions:
    print(f"  {pos.asset.ticker}: {pos.weight:.2%} (score {pos.score:+.2f})")
```

\newpage

## Module `risk`

### Responsabilité

Calcul de 7 métriques empiriques (sans hypothèse paramétrique) à partir d'une série de prix.

### Structure

```
src/bml/risk/
├── __init__.py
├── models.py        # RiskMetrics
├── calculator.py    # RiskCalculator + HistoricalRiskCalculator
└── utils.py         # portfolio_returns + portfolio_levels helpers
```

### Modèle

```python
class RiskMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    as_of: date
    horizon_days: int = Field(ge=0)
    
    annual_return: float
    annual_volatility: float = Field(ge=0.0)
    sharpe_ratio: float
    max_drawdown: float = Field(le=0.0)
    var_95: float
    cvar_95: float
    beta: float | None = None
    
    def summary(self) -> str:
        # Human-readable one-liner for logs
```

### Calculator

```python
class HistoricalRiskCalculator(RiskCalculator):
    DEFAULT_RISK_FREE_RATE = 0.025  # 2.5% annual ~ EUR overnight
    DEFAULT_VAR_ALPHA = 0.05  # 95% confidence
    MIN_OBSERVATIONS = 30
    
    def __init__(
        self,
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
        var_alpha: float = DEFAULT_VAR_ALPHA,
    ) -> None: ...
    
    def compute(
        self,
        prices: pd.Series,
        benchmark_prices: pd.Series | None = None,
        as_of: date | None = None,
    ) -> RiskMetrics:
        # Compute all 7 metrics. If benchmark_prices is None, beta is None.
```

**Détails** :

- **Annual return** : `(prod(1+r) ** (252/T)) - 1` où T est le nombre d'observations
- **Annual volatility** : `std(r) * sqrt(252)`
- **Sharpe** : `(annual_return - risk_free) / annual_volatility`
- **Max drawdown** : `min(cumulative / running_max - 1)`
- **VaR 95** : `quantile(returns, 0.05)`
- **CVaR 95** : `mean(returns[returns <= var])`
- **Beta** : `cov(asset, bench) / var(bench)`, calculé seulement si `benchmark_prices` fourni

### Utilities

```python
def portfolio_returns(
    prices: pd.DataFrame,
    weights: dict[str, float],
) -> pd.Series:
    """Compute time series of portfolio returns assuming daily rebalancing
    to constant target weights. Tickers absent from prices are skipped.
    Weights are renormalised to sum to 1.
    """

def portfolio_levels(returns: pd.Series, base: float = 100.0) -> pd.Series:
    """Convert returns back into normalised price levels."""
```

**Exemple complet** :

```python
from bml.risk import HistoricalRiskCalculator, portfolio_returns, portfolio_levels

# Compute portfolio time series
weights = {"CSPX.L": 0.6, "IB01.L": 0.4}
pf_returns = portfolio_returns(prices, weights)
pf_levels = portfolio_levels(pf_returns)

# Compute metrics
benchmark_returns = portfolio_returns(prices, BENCHMARK_60_40)
benchmark_levels = portfolio_levels(benchmark_returns)

calc = HistoricalRiskCalculator(risk_free_rate=0.025)
metrics = calc.compute(pf_levels, benchmark_prices=benchmark_levels)

print(metrics.summary())
# return=+25.67%  vol=7.18%  sharpe=+3.23  maxDD=-5.48%  ...
```

\newpage

## Module `portfolio`

### Responsabilité

Maintien de l'état temporel du portefeuille avec persistance JSON. Permet l'initialisation, la mise à jour des valuations, et le rebalancement.

### Structure

```
src/bml/portfolio/
├── __init__.py
├── models.py        # Position, Transaction, PortfolioState
└── simulator.py     # PortfolioSimulator
```

### Modèles

#### `TransactionType`

```python
class TransactionType(StrEnum):
    BUY = "buy"
    SELL = "sell"
    REBALANCE = "rebalance"
```

#### `Position`

```python
class Position(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    asset: Asset
    quantity: float = Field(ge=0.0)
    cost_basis: float = Field(gt=0.0)
    current_price: float = Field(gt=0.0)
    bucket: AssetClass
    
    @property
    def market_value(self) -> float: ...
    @property
    def unrealized_pnl(self) -> float: ...
    @property
    def unrealized_pnl_pct(self) -> float: ...
```

#### `Transaction`

```python
class Transaction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    as_of: date
    ticker: str
    quantity: float          # positive = buy, negative = sell
    price: float = Field(gt=0.0)
    transaction_type: TransactionType
    
    @property
    def notional(self) -> float:
        return self.quantity * self.price
```

#### `PortfolioState`

```python
class PortfolioState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    as_of: date
    inception_date: date
    inception_value: float = Field(gt=0.0)
    positions: list[Position] = Field(default_factory=list)
    cash: float = Field(ge=0.0)
    transactions: list[Transaction] = Field(default_factory=list)
    
    @property
    def total_value(self) -> float: ...
    @property
    def invested_value(self) -> float: ...
    @property
    def nav_per_share(self) -> float:
        return 100.0 * self.total_value / self.inception_value
    
    @property
    def total_return(self) -> float:
        return self.total_value / self.inception_value - 1.0
    
    def position_for(self, ticker: str) -> Position | None: ...
    def weight_of(self, ticker: str) -> float: ...
    def total_weight_in(self, asset_class: AssetClass) -> float: ...
```

### Simulator

```python
class PortfolioSimulator:
    """Stateless lifecycle operations. All methods static."""
    
    @staticmethod
    def initialize(
        target: Portfolio,
        prices: pd.DataFrame,
        capital: float,
        as_of: date,
    ) -> PortfolioState: ...
    
    @staticmethod
    def update_valuations(
        state: PortfolioState,
        prices: pd.DataFrame,
        as_of: date,
    ) -> PortfolioState: ...
    
    @staticmethod
    def rebalance(
        state: PortfolioState,
        target: Portfolio,
        prices: pd.DataFrame,
        as_of: date,
    ) -> PortfolioState: ...
    
    @staticmethod
    def save(state: PortfolioState, path: str | Path) -> None: ...
    
    @staticmethod
    def load(path: str | Path) -> PortfolioState: ...
    
    @staticmethod
    def period_return(start: PortfolioState, end: PortfolioState) -> float: ...
```

### Workflow opérationnel

**Initialisation** (par exemple le 5 juillet 2026) :

```python
from bml.portfolio import PortfolioSimulator

state = PortfolioSimulator.initialize(
    target=portfolio,           # output of TopNPerBucketStrategy
    prices=price_result.prices,
    capital=100_000.0,
    as_of=date(2026, 7, 5),
)
PortfolioSimulator.save(state, "data/portfolios/portfolio_latest.json")
```

**Rebalancement mensuel** (par exemple le 5 août 2026) :

```python
# 1. Load previous state
prev_state = PortfolioSimulator.load("data/portfolios/portfolio_latest.json")

# 2. Detect new regime, compute new target
new_signal = detector.detect(as_of=date(2026, 8, 5))
new_target_alloc = allocation_strategy.compute(new_signal)
new_portfolio = selection_strategy.select(new_target_alloc, universe, prices)

# 3. Rebalance
new_state = PortfolioSimulator.rebalance(
    state=prev_state,
    target=new_portfolio,
    prices=prices,
    as_of=date(2026, 8, 5),
)

# 4. Compute month return
monthly_return = PortfolioSimulator.period_return(prev_state, new_state)
print(f"August return: {monthly_return:+.2%}")

# 5. Save new state
PortfolioSimulator.save(new_state, "data/portfolios/portfolio_latest.json")
```

### Choix de design

**Statelessness** : `PortfolioSimulator` n'a aucun attribut d'instance. Toutes ses méthodes sont statiques et opèrent sur un `PortfolioState` immutable, retournant un nouveau `PortfolioState`. Cette propriété facilite les tests et raisonnements sur le code.

**Cost basis pondérée** : lors d'un rebalancement qui augmente une position existante, le cost basis est mis à jour selon une moyenne pondérée :

```
new_cost_basis = (old_qty × old_cost_basis + new_qty × new_price) / total_qty
```

Lors d'une réduction, le cost basis n'est pas modifié.

**Fractional shares** : autorisées en V1 pour simplifier. Dans la pratique, la plupart des brokers modernes (Interactive Brokers, Trade Republic, Lightyear) supportent les fractional shares.

**Pas de coûts de transaction** : explicitement absents en V1. À ajouter en V2.

\newpage

# Partie IV — Opérations et contribution

## Configuration

### Fichier `.env`

À créer à la racine, listé dans `.gitignore` :

```ini
FRED_API_KEY=votre_clé_fred_ici
```

### Fichier `pyproject.toml`

Configuration des outils de développement (extrait des sections pertinentes) :

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "C4", "RUF", "UP"]

[tool.mypy]
strict = true
python_version = "3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=src/bml --cov-report=term-missing"
```

### Fichier `src/bml/config/universe.yaml`

Structure attendue : un objet root avec une clé `assets` contenant une liste de dicts. Chaque dict est validé via le modèle `Asset`. Voir Annexe A du white paper pour la liste complète.

## Tests

### Lancer les tests

```bash
uv run pytest                              # tous les tests
uv run pytest tests/test_regime/           # un sous-dossier
uv run pytest -k "weighted"                # tests dont le nom contient "weighted"
uv run pytest -v                           # mode verbose
uv run pytest --cov=src/bml --cov-report=html   # avec rapport HTML
```

### Structure des tests

Les tests sont organisés par module, avec un fichier par module ou sous-module :

```
tests/
├── test_aggregator_and_detector.py
├── test_allocation.py
├── test_fred_provider.py
├── test_growth_indicators.py
├── test_inflation_indicators.py
├── test_loader.py                # universe loader
├── test_portfolio.py
├── test_regime_models.py
├── test_risk.py
├── test_selection.py
├── test_universe.py
└── test_yield_curve.py
```

### Conventions de tests

- **AAA pattern** : Arrange, Act, Assert. Chaque test prépare ses données, exécute l'opération, puis vérifie le résultat.
- **Mocking minimal** : on mock uniquement les frontières externes (FRED, Yahoo). Le reste des modules est testé en intégration locale.
- **Données synthétiques déterministes** : éviter les seeds aléatoires non maîtrisés. Préférer des données construites avec des paramètres tellement séparés que le test reste robuste à tout seed.
- **Un test = une assertion logique** : si plusieurs aspects sont à vérifier, écrire plusieurs tests.

### Écrire un nouveau test

```python
# tests/test_my_feature.py
from datetime import date
import pytest
from bml.regime import ...

class TestMyFeature:
    def test_specific_behavior(self) -> None:
        # Arrange
        input_data = ...
        
        # Act
        result = my_function(input_data)
        
        # Assert
        assert result.field == expected_value
    
    def test_edge_case_raises(self) -> None:
        with pytest.raises(ValueError, match="specific error message"):
            my_function(invalid_input)
```

## Workflow de contribution

### Conventions de commits

Le projet suit la convention [Conventional Commits](https://www.conventionalcommits.org) :

- `feat(<module>)`: nouvelle fonctionnalité
- `fix(<module>)`: correction de bug
- `chore`: maintenance (refactoring, dépendances, configuration)
- `docs`: documentation
- `test`: ajout ou modification de tests
- `style`: formatage uniquement (sans changement de comportement)

**Exemple** : `feat(regime): add inflation breakeven indicator`

Les messages de commit doivent décrire **ce que** le commit change, et le corps du message peut détailler **pourquoi**.

### Ajouter un nouveau module

Pour ajouter un huitième module (par exemple `attribution`) :

1. **Créer la structure** :
   ```
   src/bml/attribution/
   ├── __init__.py
   ├── models.py
   └── ...
   ```

2. **Définir les modèles** dans `models.py` (Pydantic frozen, comme les autres modules)

3. **Créer une ABC + au moins une implémentation V1** suivant le pattern Stratégie

4. **Écrire les tests** dans `tests/test_attribution.py`

5. **Exporter publiquement** dans `__init__.py`

6. **Lancer les vérifications** :
   ```bash
   uv run ruff check --fix .
   uv run ruff format .
   uv run mypy src tests
   uv run pytest
   ```

7. **Commit en `feat(attribution): ...`**

### Ajouter un nouvel indicateur macro

C'est le cas d'extension le plus fréquent. Procédure :

1. **Créer le fichier** `src/bml/regime/indicators/my_new_indicator.py` :

```python
from datetime import date
import pandas as pd

from bml.data.providers.macro_base import MacroDataProvider
from bml.regime._scoring import compute_zscore_signal
from bml.regime.enums import MacroDimension
from bml.regime.indicators.base import MacroIndicator
from bml.regime.models import IndicatorReading


class MyNewIndicator(MacroIndicator):
    SERIES_ID = "FRED_CODE"
    LOOKBACK_YEARS = 5
    HISTORY_YEARS = 30
    
    def __init__(self, provider: MacroDataProvider) -> None:
        self._provider = provider
    
    @property
    def name(self) -> str:
        return "my_new_indicator"
    
    @property
    def dimension(self) -> MacroDimension:
        return MacroDimension.GROWTH  # or INFLATION
    
    def fetch_history(self, end: date) -> pd.Series:
        start = date(end.year - self.HISTORY_YEARS, end.month, end.day)
        return self._provider.fetch_series(self.SERIES_ID, start, end)
    
    def read(self, as_of: date) -> IndicatorReading:
        raw = self.fetch_history(as_of).dropna()
        if raw.empty:
            raise ValueError(f"No data for {self.SERIES_ID}")
        
        # Apply transformation if needed (YoY %, momentum, MA, etc.)
        # transformed = raw.pct_change(periods=12).dropna() * 100
        
        signal = compute_zscore_signal(
            raw,  # or transformed
            as_of=as_of,
            lookback_years=self.LOOKBACK_YEARS,
            min_observations=60,
        )
        
        return IndicatorReading(
            indicator_name=self.name,
            dimension=self.dimension,
            as_of=as_of,
            value=signal.current_value,
            z_score=signal.z_score,
            direction=signal.direction,
            confidence=signal.confidence,
        )
```

2. **Exporter dans** `src/bml/regime/indicators/__init__.py` :

```python
from bml.regime.indicators.my_new_indicator import MyNewIndicator

__all__ = [
    # ... existing
    "MyNewIndicator",
]
```

3. **Ajouter des tests** dans `tests/test_growth_indicators.py` ou `tests/test_inflation_indicators.py`

4. **Inclure dans le détecteur** :

```python
detector = RuleBasedRegimeDetector(
    indicators=[
        # ... existing
        MyNewIndicator(fred),
    ]
)
```

## Workflow opérationnel mensuel

Le 5 de chaque mois (à partir du 5 juillet 2026), exécuter :

```bash
cd ~/Projets/bordeaux-multi-asset-lab
git pull
uv run python scripts/monthly_rebalance.py  # à créer en V2 Polish
```

Ce script (à créer) doit :

1. Charger l'état précédent depuis `data/portfolios/portfolio_latest.json`
2. Mettre à jour les valuations à la date du jour
3. Détecter le nouveau régime, calculer la nouvelle allocation, sélectionner les fonds
4. Rebalancer le portefeuille
5. Calculer la performance écoulée
6. Générer une lettre mensuelle (template Markdown)
7. Sauvegarder le nouvel état

Cette automatisation est en cours d'implémentation et fait partie du périmètre du polish pré-go-live.

## Troubleshooting

### Erreur : `MacroDataProviderError: FRED request failed for ... after 3 attempts`

**Cause** : la série FRED demandée renvoie des erreurs HTTP 5xx persistantes.

**Solutions** :

1. Vérifier le statut FRED sur `https://fred.stlouisfed.org/`. Une maintenance ponctuelle peut causer ces erreurs.
2. Réessayer dans 5-10 minutes. Le retry-and-backoff intégré gère les pannes courtes (< 30 secondes).
3. Si le problème persiste plus de quelques heures, basculer temporairement vers une série alternative (par exemple `DCOILBRENTEU` → `DCOILWTICO` comme dans `docs/known_issues.md`).

### Erreur : `pydantic_core.ValidationError: String should have at most 12 characters`

**Cause** : un ISIN invalide a été fourni à un constructeur `Asset`.

**Solution** : vérifier que l'ISIN respecte la norme ISO 6166 (exactement 12 caractères : 2 lettres pays + 9 alphanumériques + 1 chiffre). Pour les ISINs de test, utiliser des chaînes de 12 caractères respectant ce format.

### Erreur : `RuntimeError: No readings available for dimension MacroDimension.GROWTH`

**Cause** : tous les indicateurs de la dimension Croissance ont échoué (typiquement panne FRED multiple).

**Solution** : vérifier les logs WARNING. Si l'on souhaite continuer malgré tout, on peut implémenter un détecteur custom qui retourne une dimension NEUTRAL en l'absence d'indicateurs (modification de `RuleBasedRegimeDetector._validate_readings`).

### Avertissement Git : `LF will be replaced by CRLF`

**Cause** : différence de convention de fin de ligne entre Linux (LF) et Windows (CRLF).

**Solution** : c'est un avertissement bénin sur Windows. Pour le supprimer :

```bash
git config --global core.autocrlf true
```

### Tests flaky basés sur des données aléatoires

**Cause** : utilisation de paramètres de simulation trop proches qui rendent le ranking sensible au seed.

**Solution** : élargir les paramètres pour que le ranking attendu soit robuste à toute graine aléatoire. Voir le test `TestTopNPerBucketStrategy.test_top_n_picks_best_assets` qui a été corrigé suivant ce principe.

\newpage

# Annexe — Glossaire

**ABC (Abstract Base Class)** : classe Python abstraite définissant une interface que les sous-classes doivent implémenter.

**Backoff exponentiel** : stratégie de retry où le délai entre tentatives double à chaque échec (1s, 2s, 4s, ...).

**Confidence smoothing** : mécanisme d'interpolation linéaire entre une allocation neutre et une allocation cible, pondérée par un score de confiance dans le signal.

**CRLF / LF** : conventions de fin de ligne. CRLF est la convention Windows (`\r\n`), LF la convention Unix/Mac (`\n`).

**ETF (Exchange-Traded Fund)** : fonds coté en bourse, acheté et vendu comme une action.

**Fractional shares** : possibilité de détenir une quantité non-entière de parts d'un fonds (par exemple 12.7 parts).

**ISIN (International Securities Identification Number)** : code à 12 caractères identifiant un titre financier de manière unique au niveau mondial.

**JSON** : format de sérialisation textuel utilisé pour la persistance du `PortfolioState`.

**mypy strict mode** : mode de vérification statique de types le plus rigoureux de mypy. Toute valeur non typée est traitée comme une erreur.

**Pattern Stratégie** : design pattern où une famille d'algorithmes interchangeables est encapsulée derrière une interface commune.

**Pydantic** : bibliothèque Python de validation de données via type hints. Frozen models = immutables.

**Retry-and-backoff** : pattern de robustesse où une opération qui échoue est réessayée plusieurs fois avec un délai croissant.

**ruff** : outil de linting et de formatage Python ultra-rapide, alternatif à flake8 + black + isort.

**Sharpe ratio** : rendement excédentaire par unité de volatilité.

**Smoothing** : voir Confidence smoothing.

**TER (Total Expense Ratio)** : frais courants annuels d'un fonds.

**UCITS** : cadre réglementaire européen pour les fonds collectifs ouverts au grand public.

**uv** : gestionnaire de paquets Python développé par Astral, alternatif à pip + venv. Significativement plus rapide.

**VaR / CVaR** : mesures de risque réglementaires UCITS. La CVaR (Expected Shortfall) est plus robuste que la VaR.

**Yahoo Finance API** : utilisée via la bibliothèque Python `yfinance` pour récupérer les prix d'ETFs.

**Z-score** : statistique standardisée définie comme (valeur - moyenne) / écart-type.

---

*Document maintenu en parallèle de l'évolution du code. Dernière mise à jour : mai 2026.*
