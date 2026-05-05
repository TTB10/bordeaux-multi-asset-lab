# Bordeaux Multi-Asset Lab

> Active multi-asset portfolio management framework with macro regime detection and AI co-pilot.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**Bordeaux Multi-Asset Lab (BML)** is an open-source research project that simulates the workflow of a small active asset manager. It combines a quantitative macro regime detection engine, a tactical asset allocation framework, a fund/ETF selection layer, and an AI co-pilot to assist with research and investor reporting.

The portfolio runs **live** with a publicly verifiable track record and monthly investor letters published on LinkedIn.

## Why this project

Most retail portfolio tools are static (a backtest run once) or opaque (a black box producing buy/sell signals). BML is built around three principles:

- **Transparent methodology** — every model, signal, and allocation rule is documented and reproducible.
- **Live track record** — performance is timestamped, public, and out-of-sample.
- **AI as a co-pilot, not a black box** — large language models assist with research synthesis and reporting, but every investment decision remains rule-based and auditable.

## Architecture

The project is organized as a Python package (`bml`) with eight domain modules:
src/bml/
├── data/         # Data ingestion (market, macro, fund universe)
├── universe/     # Investable universe modeling
├── regime/       # Macro regime detection (rule-based, HMM, clustering)
├── allocation/   # Tactical asset allocation strategies
├── selection/    # Fund and ETF scoring and selection
├── risk/         # VaR, ES, stress tests, risk attribution
├── attribution/  # Performance attribution (Brinson-Fachler)
├── portfolio/    # Portfolio state, transactions, rebalancing
├── ai/           # LLM-based research co-pilot
└── reporting/    # Monthly letters and PDF generation

A Streamlit application (`app/`) exposes the framework through an interactive dashboard, and a research write-up (`docs/whitepaper/`) documents the methodology.

## Getting started

```bash
# Clone the repo
git clone https://github.com/TTB10/bordeaux-multi-asset-lab.git
cd bordeaux-multi-asset-lab

# Install dependencies (uv)
uv sync

# Run the dashboard
uv run streamlit run app/main.py
```

## Project status

Currently in active development.

- [ ] Data layer (Yahoo Finance, FRED, ECB)
- [ ] Investable universe (~80 UCITS ETFs)
- [ ] Macro regime engine v1 (rule-based)
- [ ] Tactical allocation engine
- [ ] Fund selection scoring
- [ ] Risk engine
- [ ] Performance attribution
- [ ] AI co-pilot
- [ ] First live monthly letter

## License

MIT — see [LICENSE](LICENSE).

## About

Built by [TTB10](https://github.com/TTB10), M1 IREF student at Université de Bordeaux, as a research project on quantitative multi-asset portfolio management.
