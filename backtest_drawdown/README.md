# Backtest: Buying Large US Stocks After a 50/60/70% Drop

**Strategy:** when a stock in the point-in-time top 300 US companies by market cap falls 50%, 60% or 70% below its 52-week high, buy at the next day's open and hold for one year. Signal dates run from 2015 to 2025. The benchmark is the S&P 500, measured with SPY including dividends.

Full tables are in [`REPORT_TABLES.md`](REPORT_TABLES.md). Every trade is listed in `results/trades.csv`.

## Headline results

| | 50% drop | 60% drop | 70% drop |
|---|---|---|---|
| Trades | 191 | 84 | 34 |
| Average 1-yr return | 52.4% | 67.5% | 81.2% |
| Median 1-yr return | 42.9% | 60.7% | 65.2% |
| Win rate | 70.7% | 70.2% | 70.6% |
| Average max drawdown during hold | -39.9% | -44.9% | -43.8% |
| Worst max drawdown during hold | -98.0% (CVNA) | -97.7% (CVNA) | -72.2% |
| S&P 500 over the same windows, average | 29.6% | 29.7% | 26.3% |
| Average excess vs S&P 500 | +22.8% | +37.8% | +54.9% |
| Trades that beat the S&P 500 | 58% | 63% | 71% |
| **Portfolio CAGR** (S&P 500: 13.4%) | 10.3% | 8.8% | -0.3% |
| **Portfolio max drawdown** (S&P 500: -33.7%) | -68.4% | -75.0% | -78.9% |

What the numbers show:

1. **Per trade, deeper drops did better.** Returns, median and excess over the S&P 500 all rise from 50% to 60% to 70%. The win rate stays at about 70% for all three.
2. **The average is driven by a few clustered years.** Most of the excess comes from entries in March 2020 (COVID) and in 2016. Entries in 2015, 2021, 2022 and 2023 were flat or lost against the index. See the entry-year tables.
3. **As a real portfolio, it underperformed the S&P 500 with 2-3x the drawdown.** Signals are rare and bunched together. Capital sits in one or two stocks for long stretches (for example GME in 2021, or OXY alone in early March 2020 before the crash). In other periods it sits idle. Each trade starting from a fresh $1 is not a portfolio you could have run.

## Method

- **Universe (point-in-time):** every stock in the S&P 500 at any time from 2014 to 2025, plus current members and about 80 large non-index US stocks. That is 850 tickers, of which 691 have Yahoo data. Each month, the 300 largest by market cap at the previous month-end are eligible. Monthly membership is in `results/monthly_top300.csv`.
- **Market cap:** the share count reported at that time (Yahoo `get_shares_full`, split-normalized) times the split-adjusted close. Share data mostly starts in late 2015, so earlier dates use the first reported count, backfilled at most 400 days.
- **Signal:** the adjusted close crosses at or below (1 - X) times its trailing 252-day high. It needs 252 days of history and only counts on the day of crossing. Only one open position is allowed per stock per threshold.
- **Entry and exit:** entry at the next day's open, adjusted for dividends. Exit at the close of the first trading day at least 365 days later. Returns include dividends.
- **Benchmark:** SPY total return over the exact same window as each trade.
- **Max drawdown:** for each trade, the peak-to-trough fall from the entry price during the hold. For the portfolio, an equal-weight mix of all open trades, holding 0%-return cash when none are open.
- **Exits after 2025:** entries from 2025 exit in 2026, using prices up to 2026-11-02. Two MSTR trades from Nov 2025 are still short of a full year and are marked at their latest price (`FullYear=False`).

## Limitations

- **Delisted stocks are only partly included.** Renamed companies are covered under their current tickers (for example ANTM→ELV, FB→META, FLT→CPAY). But 158 historical S&P 500 tickers that were acquired or went bankrupt have no price data on Yahoo (CELG, TWTR, ATVI, PXD, and others). Among them, **SVB (SIVB) and First Republic (FRC)** almost certainly would have triggered a trade and then gone to about -100% in 2023. Walgreens (WBA) probably triggered too. Each missing -100% trade lowers the average by about 0.8 points at 50%, 2 points at 60% and 5 points at 70%. Results are therefore **biased upward**. Fixing this properly needs a survivorship-free source with an API key, such as Norgate, CRSP, Sharadar, EODHD or Tiingo.
- **Some real index members are missing because their Yahoo tickers now point at other instruments.** Old Paramount (PARA) and Smurfit Westrock (SW) are examples. They are excluded by a liquidity filter that drops tickers with median volume under 10,000 shares a day.
- **Share counts can be noisy.** Companies near the #300 cutoff can be mis-ranked slightly. The giants are not affected.
- **No trading costs or slippage are included.** Gap risk is real: buying at the open after a crash can be far from the signal close.

## Reproduce

```
python fetch.py sp500_ticker_start_end.csv sp500_wikipedia.html cache/   # data (not committed)
python backtest.py cache/ results/
python report.py
```
