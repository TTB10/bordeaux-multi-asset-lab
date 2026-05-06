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

## P3 - Documented (resolved with workaround)

### FRED DCOILBRENTEU endpoint unreliable

**Date observed**: 2026-05-06
**Symptom**: HTTP 500 Internal Server Error returned consistently by the
`DCOILBRENTEU` (Brent crude) endpoint, on multiple time windows. WTI
(`DCOILWTICO`) on the same provider returns 200 OK normally.

**Resolution**: switched OilMomentumIndicator to WTI. WTI is arguably
more relevant for US inflation analysis anyway since it is the domestic
benchmark. See `src/bml/regime/indicators/oil_momentum.py`.

**Future hardening (P2 before go-live)**:
- Add retry-with-backoff in FREDProvider for transient 5xx errors.
- Add local DuckDB cache of FRED series so a momentary outage does not
  prevent the regime detector from running.