"""Drawdown-entry backtest on the point-in-time 300 largest US stocks, 2015-2025.

Rules
- Universe each month: the 300 largest stocks by market cap at the previous
  month-end (market cap = share count as reported at that time x unadjusted close).
- Signal: the dividend/split-adjusted close crosses at or below (1 - X) x its
  trailing 252-trading-day high (52-week high), for X in 50%, 60%, 70%.
  Needs 252 days of history. Signal days run 2015-01-01 to 2025-12-31.
- Entry: next trading day's open (adjusted). One position per stock at a time.
- Exit: close of the first trading day at least 365 calendar days after entry.
- Data filter: tickers whose median daily volume is < 10,000 shares are dropped
  (Yahoo series that belong to a different instrument than the index member).
- Benchmark: SPY total return (S&P 500 with dividends) over the identical
  entry-open to exit-close window of each trade.
Usage: python backtest.py <cache_dir> <out_dir>
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

THRESHOLDS = [0.50, 0.60, 0.70]
TOP_N = 300
# second share class of the same company (keep GOOGL, FOXA, NWSA, UAA)
MIN_MEDIAN_VOLUME = 10_000
DUP_CLASSES = {"GOOG", "FOX", "NWS", "UA"}
SIG_START, SIG_END = "2015-01-01", "2025-12-31"


def load(cache):
    u = pd.read_csv(cache / "universe.csv")
    tick = u[u.Prices.isin(["ok", "cached"])].Ticker.tolist()
    adj, adjo, mcap = {}, {}, {}
    for t in tick:
        p = pd.read_csv(cache / "prices" / f"{t}.csv", index_col=0, parse_dates=True)
        p = p[~p.index.duplicated(keep="last")].dropna(subset=["Close", "Adj Close"])
        p = p[p.Close > 0]
        if p.Volume.median() < MIN_MEDIAN_VOLUME:
            continue  # reused/foreign-line tickers with bogus price series (e.g. PARA, SW)
        f = (p["Adj Close"] / p.Close)
        adj[t] = p["Adj Close"]
        adjo[t] = p.Open * f
        if t == "SPY":
            continue
        sf = cache / "shares" / f"{t}.csv"
        if not sf.exists() or t in DUP_CLASSES:
            continue
        s = pd.read_csv(sf, index_col=0, parse_dates=True)["Shares"]
        s = s[s > 0].sort_index()
        # Work in split-adjusted units (yfinance Close is split-adjusted). Reported
        # share counts before a split may or may not already be adjusted: pick
        # whichever reading is closer to the post-split share counts.
        splits = p["Stock Splits"][p["Stock Splits"] > 0]
        if len(splits):
            factor = pd.Series([splits[splits.index > d].prod() for d in s.index], index=s.index)
            ref_obs = s[s.index > splits.index[-1]]
            ref = ref_obs.median() if len(ref_obs) else s.iat[-1]
            a, b = s, s * factor
            s = a.where((np.log(a / ref)).abs() <= (np.log(b / ref)).abs(), b)
        # damp one-off reporting glitches
        s = s.rolling(5, center=True, min_periods=1).median()
        first = s.index[0]
        s = s.reindex(p.index.union(s.index)).ffill().bfill().reindex(p.index)
        s[s.index < first - pd.Timedelta(days=400)] = np.nan  # don't backfill far
        mcap[t] = p.Close * s
    return (pd.DataFrame(adj).sort_index(), pd.DataFrame(adjo).sort_index(),
            pd.DataFrame(mcap).sort_index())


def run(adj, adjo, mcap, out):
    dates = adj.index
    spy_c, spy_o = adj.pop("SPY"), adjo.pop("SPY")
    # point-in-time top-300 membership: month-end rank applied to next month
    me = mcap.groupby(mcap.index.to_period("M")).last()
    rank = me.rank(axis=1, ascending=False)
    member_m = (rank <= TOP_N).shift(1)  # previous month-end ranking
    member = member_m.reindex(dates.to_period("M")).set_axis(dates).fillna(False).astype(bool)
    member = member.reindex(columns=adj.columns, fill_value=False)
    me.stack().rename("MarketCap").to_frame().join(rank.stack().rename("Rank")).query(
        "Rank <= @TOP_N").to_csv(out / "monthly_top300.csv")

    hi = adj.rolling(252, min_periods=252).max()
    dd = adj / hi - 1
    pos = {d: i for i, d in enumerate(dates)}
    trades = []
    for X in THRESHOLDS:
        below = dd <= -X
        cross = below & ~below.shift(1, fill_value=False)
        sig = cross & member & (dates >= SIG_START).reshape(-1, 1) & (dates <= SIG_END).reshape(-1, 1)
        for t in adj.columns:
            busy_until = None
            for d in sig.index[sig[t].values]:
                if busy_until is not None and d <= busy_until:
                    continue
                i = pos[d] + 1
                c = adj[t]
                while i < len(dates) and np.isnan(adjo[t].iat[i]):
                    i += 1
                if i >= len(dates):
                    continue
                ed = dates[i]
                target = ed + pd.Timedelta(days=365)
                path = c.iloc[i:].dropna()
                full = path.index[-1] >= target
                xd = path.index[path.index >= target][0] if full else path.index[-1]
                path = path.loc[:xd]
                ep = adjo[t].iat[i]
                eq = np.concatenate([[ep], path.values])
                mdd = (eq / np.maximum.accumulate(eq) - 1).min()
                bret = spy_c.loc[xd] / spy_o.loc[ed] - 1
                trades.append(dict(Threshold=f"{int(X*100)}%", Ticker=t, SignalDate=d.date(),
                                   EntryDate=ed.date(), ExitDate=xd.date(), EntryPrice=ep,
                                   ExitPrice=path.iat[-1], DrawdownAtSignal=dd.at[d, t],
                                   PITRank=int(rank.shift(1).loc[d.to_period("M"), t]),
                                   Return=path.iat[-1] / ep - 1, MaxDrawdown=mdd,
                                   SPYReturn=bret, FullYear=full))
                busy_until = xd
    tr = pd.DataFrame(trades)
    tr["Excess"] = tr.Return - tr.SPYReturn
    tr["EntryYear"] = pd.to_datetime(tr.EntryDate).dt.year
    tr.to_csv(out / "trades.csv", index=False, float_format="%.6f")
    return tr, spy_c, spy_o, adj, adjo


def stats(g):
    return pd.Series({
        "Trades": len(g),
        "AvgReturn": g.Return.mean(), "MedianReturn": g.Return.median(),
        "WinRate": (g.Return > 0).mean(),
        "AvgTradeMaxDD": g.MaxDrawdown.mean(), "WorstTradeMaxDD": g.MaxDrawdown.min(),
        "BestReturn": g.Return.max(), "WorstReturn": g.Return.min(),
        "SPYAvgReturn": g.SPYReturn.mean(), "SPYMedianReturn": g.SPYReturn.median(),
        "AvgExcess": g.Excess.mean(), "MedianExcess": g.Excess.median(),
        "BeatSPYRate": (g.Excess > 0).mean(),
    })


def portfolio(tr, adj, adjo, spy_c, spy_o):
    """Equal-weight across open positions; flat (cash at 0%) when none open."""
    dates = adj.index
    res = {}
    for X, g in tr.groupby("Threshold"):
        r = pd.DataFrame(0.0, index=dates, columns=["sum"]); n = pd.Series(0, index=dates)
        for row in g.itertuples():
            ed, xd = pd.Timestamp(row.EntryDate), pd.Timestamp(row.ExitDate)
            c = adj[row.Ticker].loc[ed:xd].ffill()
            dr = c.pct_change()
            dr.iloc[0] = c.iloc[0] / adjo[row.Ticker].loc[ed] - 1  # entry day: open -> close
            r.loc[dr.index, "sum"] += dr.values; n.loc[dr.index] += 1
        daily = (r["sum"] / n.replace(0, np.nan)).fillna(0.0)
        res[X] = daily
    spy = spy_c.pct_change().fillna(0.0)
    res["SPY"] = spy
    df = pd.DataFrame(res).loc["2015-01-01":]
    return df


def curve_stats(daily):
    eq = (1 + daily).cumprod()
    yrs = (daily.index[-1] - daily.index[0]).days / 365.25
    return pd.Series({"TotalReturn": eq.iat[-1] - 1, "CAGR": eq.iat[-1] ** (1 / yrs) - 1,
                      "MaxDrawdown": (eq / eq.cummax() - 1).min(),
                      "AnnVol": daily.std() * np.sqrt(252),
                      "Sharpe(rf=0)": daily.mean() / daily.std() * np.sqrt(252)})


def main():
    cache, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    adj, adjo, mcap = load(cache)
    tr, spy_c, spy_o, adj, adjo = run(adj, adjo, mcap, out)
    summ = tr.groupby("Threshold").apply(stats)
    summ_full = tr[tr.FullYear].groupby("Threshold").apply(stats)
    yearly = tr.groupby(["Threshold", "EntryYear"]).apply(stats)
    summ.to_csv(out / "summary.csv", float_format="%.4f")
    yearly.to_csv(out / "by_entry_year.csv", float_format="%.4f")
    daily = portfolio(tr, adj, adjo, spy_c, spy_o)
    daily.to_csv(out / "portfolio_daily_returns.csv", float_format="%.6f")
    ps = daily.apply(curve_stats).T
    ps.to_csv(out / "portfolio_summary.csv", float_format="%.4f")
    cal = (1 + daily).groupby(daily.index.year).prod() - 1
    cal.to_csv(out / "portfolio_calendar_returns.csv", float_format="%.4f")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(summ.T, summ_full.T, ps, cal, sep="\n\n")
    print(yearly[["Trades", "AvgReturn", "MedianReturn", "WinRate", "AvgTradeMaxDD", "SPYAvgReturn", "AvgExcess"]])


if __name__ == "__main__":
    main()
