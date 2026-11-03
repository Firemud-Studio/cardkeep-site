# US Sector ETF Drawdown Strategy: Backtest and Daily Signals

This is a reproducible Python system. It monitors the 11 US equity sectors through ETFs and buys a sector after a large drawdown from its 52-week high. It supports staged entries and recovery confirmation, and runs a multi-position portfolio that recycles capital. Positions are held for 1–3 years, several exit rules are compared, and the system produces daily signals.

Results: [`results/REPORT.md`](results/REPORT.md). All prices are real Yahoo Finance data from 1998-12-22 to 2026-11-02. No price is invented or filled.

## Quick start (Linux)

```bash
cd sector_etf_strategy
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

python -m sector_dd update          # download/incrementally update data/*.parquet
python -m sector_dd validate        # check split/dividend conventions -> results/validation.csv
python -m sector_dd grid            # 1,764 configurations, about 1.5 min on 4 cores -> results/grid_results.csv
python -m sector_dd report          # -> results/REPORT.md (+ detail_*.csv)
python -m sector_dd backtest --threshold-kind fixed --threshold-value 0.4 \
       --entry E_sma200 --exit hold2y --max-positions 5
python -m sector_dd signals         # update data, then write signals/<date>.md/.json
python -m pytest -q tests
```

Daily cron job, running after the US close (the server clock is in UTC):

```
30 22 * * 1-5  cd /path/to/sector_etf_strategy && .venv/bin/python -m sector_dd signals >> logs/cron.log 2>&1
```

All parameters live in [`config.toml`](config.toml).

## Layout

| File | Purpose |
|---|---|
| `sector_dd/universe.py` | ETF universe, priority order, selection rationale, a-priori sector thresholds |
| `sector_dd/data.py` | yfinance download, Parquet storage, incremental update with re-base detection, missing-day log |
| `sector_dd/validate.py` | adjustment checks: splits, dividend factors, total-return reconciliation |
| `sector_dd/panel.py` | point-in-time features: 252d high, drawdown, SMA50/200, dollar volume, dynamic thresholds |
| `sector_dd/strategy.py` | thresholds, entry modes A–E plus staged, exits, portfolio parameters |
| `sector_dd/engine.py` | daily event-driven portfolio simulator |
| `sector_dd/experiments.py`, `report.py` | parameter grid, IS/OOS split, Markdown report |
| `sector_dd/signals.py` | daily monitor and next-open orders |
| `tests/` | lookahead, staging, capital and accounting tests |

## 1. ETF universe

Only one ETF per sector is ever held. At each date the engine trades the first ETF in priority order that is *eligible on that date*. Eligibility needs at least 252 days of history and a 63-day median dollar volume of at least $10M. Both are computed from real historical prices, so they are point-in-time.

The table shows inception year and the latest 63-day median dollar volume from the stored data:

| Sector | Primary | Secondary | Backup |
|---|---|---|---|
| Technology | XLK (1998, $1,325M/day) | VGT (2004, $420M/day) | IYW (2000, $128M/day) |
| Financials | XLF (1998, $1,713M/day) | VFH (2004, $71M/day) | IYF (2000, $29M/day) |
| Energy | XLE (1998, $1,847M/day) | VDE (2004, $87M/day) | IYE (2000, $50M/day) |
| Health Care | XLV (1998, $1,321M/day) | VHT (2004, $64M/day) | IYH (2000, $32M/day) |
| Industrials | XLI (1998, $1,229M/day) | VIS (2004, $30M/day) | IYJ (2000, $10M/day) |
| Consumer Discretionary | XLY (1998, $678M/day) | VCR (2004, $18M/day) | IYC (2000, $8M/day) |
| Consumer Staples | XLP (1998, $888M/day) | VDC (2004, $29M/day) | IYK (2000, $13M/day) |
| Utilities | XLU (1998, $974M/day) | VPU (2004, $55M/day) | IDU (2000, $11M/day) |
| Materials | XLB (1998, $544M/day) | VAW (2004, $10M/day) | IYM (2000, $17M/day) |
| Communication Services | XLC (2018, $589M/day) | VOX (2004, $46M/day) | IYZ (2000, $27M/day) |
| Real Estate | VNQ (2004, $348M/day) | XLRE (2015, $266M/day) | IYR (2000, $567M/day) |

Rationale:
- **SPDR XL\*** funds are primary. They have the lowest cost, the deepest liquidity and the tightest spreads, with history from 1998.
- **Vanguard V\*** funds are secondary. They are low cost with large AUM, from 2004.
- **iShares IY\*** funds are backups only, kept for their history from 2000. Their expense ratio is about 0.4%, which is above the 0.25% target. That exception is justified because they matter only before 2004 and as fallbacks.
- **VNQ** is the Real Estate primary because it has much larger AUM, a longer history than XLRE (2015) and higher volume.
- `python -m sector_dd universe-info` pulls current expense ratio, AUM and volume live from Yahoo. This is a snapshot only. Yahoo's quote-info endpoint was rate-limiting (HTTP 401) when this was built, so no snapshot is committed.

**Bias disclosures**
- **Fixed universe, survivorship bias.** The funds were chosen in 2026, knowing they survived and grew. Historical AUM and expense ratios are not available from free sources, so they are not used as filters, and no historical fund facts are made up. Only history length and dollar volume are applied point-in-time.
- **Communication Services before June 2018** is proxied by VOX/IYZ. These tracked the old, narrow *Telecom Services* sector, a different exposure from today's XLC (META, GOOGL, NFLX).
- **Real Estate before its GICS split in 2016** was part of Financials. VNQ/IYR are REIT funds and existed throughout, so this is a classification note, not a data gap.

## 2. Data

- `yfinance` with `auto_adjust=False, actions=True`, maximum history, one Parquet file per ticker in `data/`. A run log goes to `logs/`. Missing trading days, checked against the SPY calendar, go to `data/missing_report.csv`.
- **Incremental update:** the last 10 stored days are fetched again together with any new days. If the overlapping Close or Adj Close values changed, Yahoo has re-based its adjustments (a new split or dividend), so the full history is downloaded again instead of stitching two adjustment bases together. A partial intraday bar for today is dropped.
- **Adjustment convention.** `Close` is split-adjusted only and is used for **signals**: the 52-week high, drawdown and SMAs. `Adj Close` is split- and dividend-adjusted and is used for **performance**. Fills use `Open × AdjClose/Close`. Position units are held in adjusted terms, so dividends are reinvested implicitly and are counted once.
- **Validation** (`results/validation.csv`): all 34 tickers pass.
  - No split shows up as an unadjusted price jump.
  - The daily change in AdjClose/Close equals `1 − D/Close₍t−1₎` on ex-dates and is 1 on all other days. The maximum error is 1.6e-6.
  - Compounding `(Close + Dividend)` matches the Adj Close total return within 0.25% over 27 years. Counting dividends twice, or dropping them, would show a gap of 1.5× or more.
- **Risk-free rate:** the 13-week T-bill (^IRX), lagged one day, earned on idle cash.
- **Missing data:** the reference calendar showed no missing days and no NaN closes. If a held ETF lacks a price on a day, its valuation carries the last real close forward. No trade is ever filled at an invented price: an order for that day lapses instead.

## 3–4. Entry logic

- **Drawdown:** `Close / max(Close, last 252 days) − 1`, known at the close. The trade is filled at the **next day's open** with 5 bps slippage per side.
- **Thresholds**
  - Fixed: 20, 30, 40, 50 and 60%.
  - **Dynamic:** the 5th, 10th or 20th percentile of the ETF's own daily drawdowns over the previous 10 years, needing at least 3 years of drawdowns. The window is shifted one day, so it never includes today, and has a floor of 10%.
  - **Sector-specific:** a-priori, not fitted. Staples, Utilities and Health Care 20%; Tech and Energy 35%; the rest 30%.
- **Episode state machine per sector**
  - The sector is *armed* when its drawdown is at or below the threshold. The threshold is frozen at arm time.
  - The trough is tracked from that point.
  - An episode with no purchase is cancelled if the drawdown recovers above half the threshold, or after 252 days.
  - After a position closes, the drawdown has to recover above the threshold before the sector can arm again. This prevents repeat buying in the same decline.
- **Entry modes**
  - A: buy immediately.
  - B and C: buy after a 5% or 10% rebound from the trough.
  - D and E: buy after a close above SMA50 or SMA200.
- **Staged entries**
  - S1: 30% of the intended allocation at the threshold, 30% at a drawdown 10 points deeper, and the remaining 40% after a 10% rebound.
  - S2: the same, but the last 40% waits for a close above SMA50.
  - Each stage fires at most once. If confirmation comes before the deeper stage triggers, the confirmation stage buys everything still unbought and the deeper stage is marked `skipped`.

## 5. Portfolio and capital (assumptions)

The specification I received **ended at "Test maximum…"**. The following are my assumptions, all set in `config.toml` and `strategy.py`:
- Starting capital is $100,000. The grid tests **3, 5, 8 and 11 maximum concurrent positions**, with at most one position per sector.
- The intended allocation of a new position is current equity divided by max positions, fixed at the first fill. Stages buy fractions of it, limited by cash not already reserved for other orders.
- If several sectors qualify on the same day, add-ons to existing positions go first. New positions are then ranked by drawdown divided by threshold (deepest first).
- Sale proceeds go back to cash and fund later signals. Idle cash earns the T-bill rate.
- **Exits** (holding time counts from the first fill):
  - Hold for 1, 2 or 3 years.
  - +50% profit target, 3-year maximum.
  - Close back at the 52-week high seen at arm time, 3-year maximum.
  - 20% trailing stop after 1 year, 3-year maximum.
  - Close below SMA200 after 1 year, 3-year maximum.

Send the rest of section 5 and anything after it, and I will adapt the system to it.

## Results summary (2000-01-03 to 2026-11-02, see REPORT.md)

| | CAGR | Sharpe | Max DD | Avg. exposure |
|---|---|---|---|---|
| SPY buy & hold | 8.2% | 0.41 | −55% | 100% |
| Median of 1,764 configs | 4.6% | 0.31 | −39% | 26% |
| Best CAGR (dynq10, A, hold 3y, N=3) | 10.1% | 0.50 | −63% | 69% |
| Best Sharpe (fix40, E_sma200, hold 2y, N=3) | 6.6% | 0.64 | −18% | 17% |

Findings:
1. **Every threshold, entry and exit works trade by trade.** Across configurations (10th–90th percentile), win rates are 67–92% and average trades return +15% to +53%. **As a portfolio, though, almost no configuration beats SPY's return,** because capital is idle most of the time (median exposure 26%). A 40% sector drawdown happened only in 2000–02, 2008–09, 2020 and 2022.
2. **The SMA200 confirmation (E) is the most robust improvement.** It roughly halves the portfolio drawdown (median −19% versus −43% for immediate entry) at similar CAGR, by not buying falling knives in 2008. The staged entries (S1/S2) differ little from immediate entry.
3. **Holding for 2–3 years beats 1 year** in every comparison. Exits based on targets or trailing stops add little over a plain 2–3 year hold.
4. **Shallower or dynamic thresholds** (fix20, dynq20) raise exposure and CAGR. Deep fixed thresholds (50–60%) almost never trigger.
5. **Selection is unstable.** The rank correlation between in-sample (2000–12) and out-of-sample (2013–26) Sharpe across all configurations is about 0. The configurations that led in-sample earned 3–7% a year out of sample, against 14.5% for SPY. Treat any single "best" configuration as overfit.

The next step that matters most is a policy for idle capital, for example holding SPY or an equal-weight sector basket and selling it to fund signals. Whether that adds value over buy-and-hold is the real question for this strategy.

## 6. Daily signals

`python -m sector_dd signals` updates the data and runs the `[live]` strategy up to the latest close. It writes `signals/<date>.md`, `.json` and `latest.md`, containing:
- A **sector monitor:** active ETF, drawdown, threshold, distance to the threshold, position versus SMA50/200, dollar volume, and state (`watch`, `armed`, `holding`, with trough, rebound and stage status).
- The **simulated holdings**, scaled to `live.capital`, with share counts at the last close.
- The **orders for the next open:** BUY in dollars and approximate shares, and SELL with the reason.

Set `live.start` to the date real money was committed, so the simulated book matches the real account. The default live strategy is the in-sample leader, `fix40|E_sma200|hold2y|N5`. It is a placeholder for your decision, not a recommendation.

## Known limitations

- Fixed universe with survivorship bias, and a Telecom proxy before 2018 (see §1).
- Yahoo's adjusted history changes over time. The committed Parquet files are a snapshot as of 2026-11-02.
- Fills at the open with 5 bps slippage. No taxes, and no bid-ask modelling beyond the slippage figure.
- The out-of-sample slice continues the same simulation, so it is not a fresh-start portfolio.
- Only 6–45 positions per configuration over 27 years. Treat statistical confidence as low.
