# Known Issues

This document tracks known data quality issues that need attention before the
production go-live (July 2026). They do not block development but must be
resolved before the live track record begins.

## P1 - Critical (blocks go-live)

### Bulk-fetch data discrepancy on emerging market ETFs

**Affected tickers**: NDIA.L (iShares MSCI India), and likely others in the EM
universe.

**Symptom**: When fetched via `yfinance.download(...)` in bulk mode, the
returned price series differs materially from the per-ticker fetch via
`yfinance.Ticker(...).history()`.

**Example (NDIA.L, 3-year horizon)**:
- Per-ticker fetch: total return +23.2%, vol 16.1%
- Bulk fetch (current YFinanceProvider): total return -8.1%, vol 17.3%

**Hypothesis**: yfinance bulk download has known issues with calendar
alignment and split adjustments on certain emerging market or low-liquidity
listings.

**Mitigation plan**:
1. Refactor `YFinanceProvider` to expose two paths: `bulk` (current) and
   `per_ticker` (new).
2. Add an automatic fallback that detects suspicious data quality (e.g.,
   total return diverging from a sanity benchmark) and re-fetches per ticker.
3. Add a regression test that pins the expected return range for NDIA.L.

**Owner**: TTB10
**Target**: before first live letter (July 2026)