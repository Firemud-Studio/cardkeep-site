# US Top-300 Stocks: Daily History 2015–2025

Daily price history from 2015-01-02 to 2025-12-31 for the 300 largest US companies by market cap. There is one CSV per ticker in `data/`.

- **Source:** Yahoo Finance, via `yfinance`.
- **Columns:** `Date, Open, High, Low, Close, Adj Close, Volume, Dividends, Stock Split`.
  - `Open/High/Low/Close` are split-adjusted but not dividend-adjusted.
  - `Adj Close` is adjusted for both splits and dividends.
  - `Volume` is split-adjusted.
- **Ranking:** by market cap at download time (Nov 2026). Rank, name, market cap, row count and date range for each stock are in `tickers.csv`.
- **Universe:** S&P 500 constituents plus a list of large US-listed companies outside the index (see `SUPPLEMENT` in `download.py`). Only one share class is kept per company (GOOGL, FOXA, NWSA, BRK-B).
- **Late listings:** companies that listed after 2015 (for example PLTR, UBER, GEV) start on their first trading day.
- **Skipped:** tickers with no data in 2015–2025, such as 2026 spin-offs (HONA, VYLR) and delisted KVUE. The next-largest stock fills each gap.
- **Survivorship bias:** the list is today's largest companies, not the largest of each year.

To regenerate: `python download.py <saved Wikipedia "List of S&P 500 companies" HTML> [out_dir]`
