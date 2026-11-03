# Sector ETF drawdown strategy - backtest report

Period 2000-01-03 to 2026-11-02. 1764 strategy configurations. Initial capital USD 100,000. Fills at the next open with slippage. Idle cash earns 13-week T-bill yield. All returns include dividends.

## Benchmark

| name | cagr | vol | sharpe | max_dd | calmar | avg_exposure |
|---|---|---|---|---|---|---|
| SPY buy&hold | 8.2% | 19.2% | 0.41 | -55.2% | 0.15 | 100.0% |

## Top 20 configurations by full-period Sharpe

Treat this list with caution. Picking the best of 1764 backtests overstates expected performance (selection bias). The out-of-sample section below is the more honest view.

| name | cagr | vol | sharpe | max_dd | calmar | avg_exposure | n_trades | win_rate | avg_trade_ret | avg_days_held |
|---|---|---|---|---|---|---|---|---|---|---|
| fix40|E_sma200|hold2y|N3 | 6.6% | 7.5% | 0.64 | -18.1% | 0.37 | 16.5% | 6 | 100.0% | 77.9% | 505.00 |
| dynq20|E_sma200|trail20_min1y_max3y|N5 | 8.8% | 11.3% | 0.64 | -26.5% | 0.33 | 63.5% | 33 | 84.8% | 35.3% | 630.42 |
| dynq20|E_sma200|hold2y|N8 | 8.2% | 10.3% | 0.63 | -29.9% | 0.28 | 46.4% | 45 | 91.1% | 33.4% | 505.00 |
| fix30|E_sma200|hold2y|N8 | 5.5% | 5.7% | 0.63 | -14.3% | 0.39 | 18.1% | 18 | 94.4% | 51.7% | 505.00 |
| dynq20|E_sma200|hold2y|N5 | 9.0% | 11.6% | 0.63 | -26.5% | 0.34 | 55.9% | 36 | 91.7% | 31.4% | 505.00 |
| fix30|E_sma200|hold2y|N5 | 6.7% | 7.7% | 0.63 | -22.6% | 0.29 | 23.8% | 15 | 93.3% | 52.7% | 505.00 |
| fix30|E_sma200|hold2y|N3 | 8.3% | 10.7% | 0.62 | -38.0% | 0.22 | 31.1% | 12 | 91.7% | 56.1% | 505.00 |
| dynq20|E_sma200|target50_max3y|N5 | 9.2% | 12.3% | 0.62 | -37.3% | 0.25 | 56.5% | 32 | 93.8% | 38.2% | 575.78 |
| fix40|E_sma200|trail20_min1y_max3y|N3 | 6.7% | 8.1% | 0.60 | -18.1% | 0.37 | 21.8% | 6 | 100.0% | 80.5% | 666.17 |
| dynq20|E_sma200|target50_max3y|N3 | 9.6% | 13.8% | 0.59 | -47.9% | 0.20 | 59.5% | 22 | 90.9% | 37.3% | 583.05 |
| fix40|E_sma200|hold2y|N5 | 5.5% | 6.3% | 0.58 | -18.4% | 0.30 | 13.2% | 8 | 100.0% | 73.0% | 505.00 |
| fix30|E_sma200|hold2y|N11 | 4.7% | 4.8% | 0.58 | -12.6% | 0.37 | 14.7% | 20 | 90.0% | 47.3% | 505.00 |
| dynq20|E_sma200|target50_max3y|N8 | 7.6% | 10.4% | 0.58 | -29.3% | 0.26 | 47.5% | 40 | 95.0% | 37.2% | 602.77 |
| dynq20|E_sma200|hold3y|N8 | 8.0% | 11.1% | 0.57 | -30.5% | 0.26 | 54.3% | 36 | 94.4% | 43.6% | 757.00 |
| dynq20|E_sma200|target50_max3y|N11 | 6.9% | 9.0% | 0.57 | -30.6% | 0.23 | 40.1% | 44 | 95.5% | 38.2% | 613.20 |
| dynq20|E_sma200|hold3y|N11 | 7.1% | 9.6% | 0.57 | -28.3% | 0.25 | 46.0% | 41 | 95.1% | 45.2% | 757.00 |
| fix40|E_sma200|hold3y|N3 | 7.1% | 9.4% | 0.57 | -20.1% | 0.35 | 25.7% | 6 | 100.0% | 89.4% | 757.00 |
| dynq20|S1_staged_rec10|hold3y|N8 | 9.0% | 13.4% | 0.57 | -45.4% | 0.20 | 59.9% | 42 | 90.5% | 43.1% | 757.00 |
| fix40|E_sma200|target50_max3y|N3 | 5.0% | 5.4% | 0.57 | -11.3% | 0.44 | 11.6% | 6 | 100.0% | 47.9% | 376.83 |
| fix40|E_sma200|hold2y|N8 | 4.8% | 5.1% | 0.56 | -14.8% | 0.32 | 10.4% | 10 | 100.0% | 72.5% | 505.00 |

## Top 20 by CAGR

| name | cagr | vol | sharpe | max_dd | calmar | avg_exposure | n_trades | win_rate | avg_trade_ret | avg_days_held |
|---|---|---|---|---|---|---|---|---|---|---|
| dynq10|A_immediate|hold3y|N3 | 10.1% | 19.1% | 0.50 | -63.4% | 0.16 | 69.3% | 17 | 88.2% | 47.4% | 757.00 |
| dynq10|S1_staged_rec10|hold3y|N3 | 9.8% | 18.9% | 0.49 | -64.2% | 0.15 | 66.8% | 17 | 82.4% | 46.1% | 757.00 |
| dynq20|E_sma200|target50_max3y|N3 | 9.6% | 13.8% | 0.59 | -47.9% | 0.20 | 59.5% | 22 | 90.9% | 37.3% | 583.05 |
| dynq10|S2_staged_sma50|hold3y|N3 | 9.6% | 18.6% | 0.48 | -63.0% | 0.15 | 67.3% | 17 | 82.4% | 45.2% | 757.00 |
| dynq10|B_recover5|hold3y|N3 | 9.4% | 18.8% | 0.47 | -62.9% | 0.15 | 68.5% | 17 | 82.4% | 44.2% | 757.00 |
| dynq20|S2_staged_sma50|hold3y|N5 | 9.4% | 14.8% | 0.55 | -50.9% | 0.19 | 68.0% | 29 | 93.1% | 40.9% | 757.00 |
| dynq20|E_sma200|hold3y|N3 | 9.3% | 14.8% | 0.55 | -42.6% | 0.22 | 72.7% | 18 | 88.9% | 42.6% | 757.00 |
| dynq20|B_recover5|hold3y|N5 | 9.2% | 15.4% | 0.53 | -55.1% | 0.17 | 66.4% | 30 | 93.3% | 44.5% | 757.00 |
| dynq20|E_sma200|target50_max3y|N5 | 9.2% | 12.3% | 0.62 | -37.3% | 0.25 | 56.5% | 32 | 93.8% | 38.2% | 575.78 |
| dynq20|S1_staged_rec10|hold3y|N5 | 9.2% | 14.1% | 0.56 | -49.3% | 0.19 | 64.3% | 29 | 93.1% | 39.6% | 757.00 |
| dynq20|A_immediate|hold3y|N5 | 9.1% | 14.6% | 0.54 | -49.6% | 0.18 | 67.0% | 29 | 93.1% | 41.1% | 757.00 |
| dynq20|S2_staged_sma50|target50_max3y|N5 | 9.1% | 14.5% | 0.54 | -53.7% | 0.17 | 61.7% | 35 | 88.6% | 34.1% | 594.46 |
| dynq20|S2_staged_sma50|hold3y|N8 | 9.0% | 13.5% | 0.56 | -45.4% | 0.20 | 62.0% | 42 | 90.5% | 43.1% | 757.00 |
| dynq20|S1_staged_rec10|hold3y|N8 | 9.0% | 13.4% | 0.57 | -45.4% | 0.20 | 59.9% | 42 | 90.5% | 43.1% | 757.00 |
| dynq20|S2_staged_sma50|target50_max3y|N3 | 9.0% | 16.9% | 0.48 | -62.8% | 0.14 | 65.9% | 24 | 83.3% | 30.8% | 592.46 |
| dynq20|E_sma200|hold2y|N5 | 9.0% | 11.6% | 0.63 | -26.5% | 0.34 | 55.9% | 36 | 91.7% | 31.4% | 505.00 |
| dynq10|A_immediate|hold3y|N5 | 8.9% | 15.4% | 0.51 | -51.0% | 0.17 | 59.5% | 24 | 91.7% | 45.2% | 757.00 |
| dynq20|E_sma200|hold3y|N5 | 8.9% | 13.3% | 0.56 | -37.4% | 0.24 | 65.2% | 28 | 92.9% | 42.3% | 757.00 |
| dynq20|E_sma200|trail20_min1y_max3y|N5 | 8.8% | 11.3% | 0.64 | -26.5% | 0.33 | 63.5% | 33 | 84.8% | 35.3% | 630.42 |
| dynq20|B_recover5|trail20_min1y_max3y|N3 | 8.8% | 16.2% | 0.48 | -51.8% | 0.17 | 71.6% | 26 | 65.4% | 30.9% | 573.50 |

## Parameter effects (median across all other parameters)


### By threshold

| threshold | cagr | sharpe | max_dd | avg_exposure | n_trades | win_rate |
|---|---|---|---|---|---|---|
| dynq05 | 4.2% | 0.26 | -43.6% | 26.9% | 25.50 | 77.8% |
| dynq10 | 5.5% | 0.36 | -43.9% | 39.5% | 36.00 | 81.1% |
| dynq20 | 6.7% | 0.43 | -45.8% | 51.4% | 47.00 | 79.9% |
| fix20 | 5.6% | 0.35 | -48.4% | 43.0% | 39.00 | 75.6% |
| fix30 | 4.7% | 0.29 | -45.4% | 26.5% | 23.00 | 82.6% |
| fix40 | 4.3% | 0.29 | -33.7% | 15.8% | 14.50 | 83.3% |
| fix50 | 3.5% | 0.23 | -26.8% | 9.3% | 9.00 | 77.8% |
| fix60 | 3.5% | 0.29 | -16.1% | 6.7% | 6.00 | 80.0% |
| sector | 4.9% | 0.33 | -42.3% | 27.4% | 23.00 | 84.1% |

### By entry

| entry | cagr | sharpe | max_dd | avg_exposure | n_trades | win_rate |
|---|---|---|---|---|---|---|
| A_immediate | 4.8% | 0.30 | -42.8% | 27.8% | 23.00 | 80.0% |
| B_recover5 | 4.7% | 0.29 | -42.8% | 27.4% | 23.50 | 76.5% |
| C_recover10 | 4.8% | 0.30 | -41.8% | 26.3% | 22.00 | 77.8% |
| D_sma50 | 4.6% | 0.32 | -37.0% | 26.4% | 22.00 | 80.0% |
| E_sma200 | 4.3% | 0.38 | -18.8% | 20.4% | 17.00 | 86.2% |
| S1_staged_rec10 | 4.7% | 0.30 | -41.8% | 26.9% | 23.00 | 77.8% |
| S2_staged_sma50 | 4.7% | 0.31 | -39.1% | 27.1% | 23.50 | 80.0% |

### By exit

| exit | cagr | sharpe | max_dd | avg_exposure | n_trades | win_rate |
|---|---|---|---|---|---|---|
| hold1y | 3.5% | 0.23 | -37.4% | 16.3% | 28.50 | 74.4% |
| hold2y | 4.8% | 0.33 | -40.1% | 26.0% | 21.00 | 79.7% |
| hold3y | 5.1% | 0.34 | -39.8% | 32.5% | 18.00 | 86.6% |
| priorhigh_max3y | 4.8% | 0.31 | -40.4% | 23.6% | 24.00 | 89.4% |
| sma200_min1y_max3y | 4.0% | 0.26 | -37.4% | 22.8% | 26.00 | 75.0% |
| target50_max3y | 5.2% | 0.33 | -40.4% | 27.8% | 20.00 | 87.1% |
| trail20_min1y_max3y | 5.1% | 0.34 | -37.4% | 34.4% | 25.00 | 72.7% |

### By max_positions

| max_positions | cagr | sharpe | max_dd | avg_exposure | n_trades | win_rate |
|---|---|---|---|---|---|---|
| 3 | 5.1% | 0.28 | -50.0% | 36.5% | 15.00 | 75.7% |
| 5 | 4.9% | 0.31 | -46.5% | 29.9% | 21.00 | 80.0% |
| 8 | 4.6% | 0.32 | -39.1% | 23.6% | 27.00 | 81.2% |
| 11 | 4.3% | 0.33 | -30.0% | 19.6% | 31.00 | 81.2% |

### Median Sharpe: threshold x entry

| threshold | A_immediate | B_recover5 | C_recover10 | D_sma50 | E_sma200 | S1_staged_rec10 | S2_staged_sma50 |
|---|---|---|---|---|---|---|---|
| dynq05 | 0.25 | 0.24 | 0.26 | 0.30 | 0.27 | 0.25 | 0.25 |
| dynq10 | 0.39 | 0.33 | 0.34 | 0.39 | 0.35 | 0.38 | 0.37 |
| dynq20 | 0.41 | 0.41 | 0.36 | 0.45 | 0.51 | 0.41 | 0.45 |
| fix20 | 0.34 | 0.35 | 0.35 | 0.36 | 0.34 | 0.36 | 0.35 |
| fix30 | 0.29 | 0.29 | 0.28 | 0.30 | 0.47 | 0.29 | 0.30 |
| fix40 | 0.29 | 0.27 | 0.28 | 0.32 | 0.47 | 0.27 | 0.31 |
| fix50 | 0.22 | 0.22 | 0.23 | 0.20 | 0.34 | 0.23 | 0.22 |
| fix60 | 0.36 | 0.33 | 0.32 | 0.29 | 0.19 | 0.33 | 0.31 |
| sector | 0.30 | 0.34 | 0.34 | 0.33 | 0.40 | 0.32 | 0.33 |

### Median CAGR: threshold x entry

| threshold | A_immediate | B_recover5 | C_recover10 | D_sma50 | E_sma200 | S1_staged_rec10 | S2_staged_sma50 |
|---|---|---|---|---|---|---|---|
| dynq05 | 4.4% | 4.0% | 4.3% | 4.3% | 4.1% | 4.2% | 4.2% |
| dynq10 | 6.1% | 5.4% | 5.3% | 5.7% | 5.1% | 5.7% | 6.0% |
| dynq20 | 7.1% | 6.7% | 5.8% | 6.8% | 7.0% | 6.8% | 7.0% |
| fix20 | 6.0% | 5.8% | 5.8% | 5.6% | 4.5% | 5.8% | 5.6% |
| fix30 | 4.8% | 4.7% | 4.5% | 4.4% | 5.1% | 4.7% | 4.7% |
| fix40 | 4.4% | 4.1% | 4.3% | 4.1% | 4.4% | 4.3% | 4.4% |
| fix50 | 3.5% | 3.4% | 3.5% | 3.1% | 3.7% | 3.6% | 3.4% |
| fix60 | 4.1% | 3.8% | 3.6% | 3.3% | 2.6% | 3.7% | 3.5% |
| sector | 4.9% | 5.2% | 5.2% | 4.7% | 4.3% | 5.1% | 5.0% |

### Median Sharpe: exit x max_positions

| exit | 3 | 5 | 8 | 11 |
|---|---|---|---|---|
| hold1y | 0.20 | 0.22 | 0.26 | 0.26 |
| hold2y | 0.28 | 0.31 | 0.33 | 0.35 |
| hold3y | 0.32 | 0.35 | 0.34 | 0.33 |
| priorhigh_max3y | 0.30 | 0.32 | 0.32 | 0.32 |
| sma200_min1y_max3y | 0.24 | 0.25 | 0.28 | 0.29 |
| target50_max3y | 0.29 | 0.33 | 0.36 | 0.36 |
| trail20_min1y_max3y | 0.33 | 0.34 | 0.34 | 0.34 |

## In-sample / out-of-sample check

In-sample = 2000-01-01 to 2012-12-31, out-of-sample = 2013-01-01 to 2099-12-31. The 10 configurations with the best in-sample Sharpe are shown with their out-of-sample results. The OOS slice continues the same simulation, so positions opened in-sample carry over.

| name | in_sample_sharpe | in_sample_cagr | out_of_sample_sharpe | out_of_sample_cagr | out_of_sample_maxdd |
|---|---|---|---|---|---|
| fix40|E_sma200|target50_max3y|N8 | 0.59 | 5.2% | 0.67 | 2.7% | -1.9% |
| fix40|E_sma200|target50_max3y|N11 | 0.59 | 4.5% | 0.67 | 2.4% | -1.4% |
| fix40|E_sma200|hold2y|N8 | 0.57 | 5.9% | 0.70 | 3.8% | -7.1% |
| fix40|E_sma200|target50_max3y|N3 | 0.57 | 6.0% | 0.68 | 4.0% | -4.8% |
| fix40|E_sma200|hold2y|N11 | 0.56 | 5.0% | 0.69 | 3.3% | -5.4% |
| fix40|E_sma200|hold2y|N3 | 0.56 | 6.6% | 0.75 | 6.6% | -14.8% |
| fix40|E_sma200|target50_max3y|N5 | 0.55 | 5.8% | 0.68 | 3.1% | -3.0% |
| fix40|E_sma200|hold2y|N5 | 0.54 | 6.2% | 0.72 | 4.9% | -10.3% |
| dynq20|E_sma200|hold2y|N11 | 0.54 | 5.2% | 0.51 | 7.0% | -31.1% |
| fix40|E_sma200|trail20_min1y_max3y|N3 | 0.52 | 7.0% | 0.76 | 6.4% | -11.6% |

Medians across all configurations: IS Sharpe 0.17, OOS Sharpe 0.56, OOS CAGR 6.3%. SPY: IS Sharpe 0.09, OOS Sharpe 0.79, OOS CAGR 14.5%.

Rank correlation of IS vs OOS Sharpe across all configs: -0.01.


## Sub-period Sharpe/CAGR (median across configs vs SPY)

| period | median_cagr | median_sharpe | median_maxdd | spy_cagr | spy_sharpe | spy_maxdd |
|---|---|---|---|---|---|---|
| p2000s (2000-01-01..2009-12-31) | 2.7% | 0.07 | -38.9% | -0.9% | -0.05 | -55.2% |
| p2010s (2010-01-01..2019-12-31) | 2.6% | 0.37 | -13.4% | 13.3% | 0.88 | -19.3% |
| p2020s (2020-01-01..2099-12-31) | 10.1% | 0.66 | -17.8% | 14.7% | 0.64 | -33.7% |

## Detailed run: `fix40|E_sma200|hold2y|N5`

| final_equity | total_return | cagr | vol | sharpe | sortino | max_dd | calmar | ulcer | avg_exposure | time_invested | n_trades | n_open | win_rate | avg_trade_ret | median_trade_ret | worst_trade | best_trade | avg_days_held | profit_factor |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 425,065 | 325.1% | 5.5% | 6.3% | 0.58 | 0.59 | -18.4% | 0.30 | 0.02 | 13.2% | 30.3% | 8 | 0 | 100.0% | 73.0% | 58.6% | 26.4% | 1.66 | 505.00 | inf |

### Calendar-year returns

| year | strategy | spy |
|---|---|---|
| 2000 | 6.0% | -8.8% |
| 2001 | 3.4% | -11.8% |
| 2002 | -0.8% | -21.6% |
| 2003 | 7.8% | 28.2% |
| 2004 | 1.9% | 10.7% |
| 2005 | 3.2% | 4.8% |
| 2006 | 4.8% | 15.8% |
| 2007 | 4.4% | 5.1% |
| 2008 | 1.4% | -36.8% |
| 2009 | 23.6% | 26.4% |
| 2010 | 21.7% | 15.1% |
| 2011 | 6.9% | 1.9% |
| 2012 | 0.1% | 16.0% |
| 2013 | 0.0% | 32.3% |
| 2014 | 0.0% | 13.5% |
| 2015 | 0.0% | 1.2% |
| 2016 | 0.3% | 12.0% |
| 2017 | 0.9% | 21.7% |
| 2018 | 1.9% | -4.6% |
| 2019 | 2.1% | 31.2% |
| 2020 | 1.2% | 18.3% |
| 2021 | 11.0% | 28.7% |
| 2022 | 20.7% | -18.2% |
| 2023 | 10.9% | 26.2% |
| 2024 | 12.2% | 24.9% |
| 2025 | 5.3% | 17.7% |
| 2026 | 3.1% | 11.2% |

### Positions

| sector | etf | arm_date | entry_date | exit_date | days_held | invested | ret | stages | exit_reason |
|---|---|---|---|---|---|---|---|---|---|
| Technology | XLK | 2002-02-04 | 2002-11-26 | 2004-11-30 | 505 | 22,240 | 26.4% | filled | max_hold |
| Consumer Discretionary | XLY | 2008-10-09 | 2009-05-01 | 2011-05-03 | 505 | 27,340 | 78.9% | filled | max_hold |
| Technology | XLK | 2008-10-07 | 2009-05-04 | 2011-05-04 | 505 | 27,284 | 55.8% | filled | max_hold |
| Materials | XLB | 2008-10-07 | 2009-05-05 | 2011-05-05 | 505 | 27,518 | 51.7% | filled | max_hold |
| Energy | XLE | 2008-10-07 | 2009-05-29 | 2011-05-31 | 505 | 26,960 | 55.3% | filled | max_hold |
| Industrials | XLI | 2008-10-09 | 2009-06-03 | 2011-06-03 | 505 | 27,606 | 61.5% | filled | max_hold |
| Energy | XLE | 2020-03-09 | 2020-11-18 | 2022-11-21 | 505 | 46,497 | 166.5% | filled | max_hold |
| Communication Services | XLC | 2022-09-23 | 2023-01-27 | 2025-02-03 | 505 | 63,040 | 88.1% | filled | max_hold |

## Data validation

34/34 tickers passed every check. The checks are: splits already applied to Close, dividend factors consistent with Adj Close, and Close+dividends total return matching Adj Close within 2%. Full table: `results/validation.csv`.

