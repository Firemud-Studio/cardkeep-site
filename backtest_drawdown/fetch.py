"""Fetch the backtest universe: daily prices (2014-01-01..today) and share-count
history for every stock that was in the S&P 500 at any time 2014-2025, plus the
current S&P 500 and the large non-index stocks from ../us_stocks_2015_2025.

Usage: python fetch.py <sp500_ticker_start_end.csv> <sp500_wikipedia.html> <cache_dir>
  sp500_ticker_start_end.csv: github.com/fja05680/sp500
Writes <cache_dir>/prices/<T>.csv, <cache_dir>/shares/<T>.csv, <cache_dir>/universe.csv
"""
import sys, time, importlib.util, concurrent.futures as cf
from pathlib import Path
import pandas as pd
import yfinance as yf

spec = importlib.util.spec_from_file_location(
    "dl", Path(__file__).parent.parent / "us_stocks_2015_2025" / "download.py")
dl = importlib.util.module_from_spec(spec); spec.loader.exec_module(dl)

START, END = "2014-01-01", None


def prices(t, out):
    f = out / "prices" / f"{t}.csv"
    if f.exists():
        return t, "cached"
    for a in range(3):
        try:
            df = yf.Ticker(t).history(start=START, end=END, auto_adjust=False, actions=True)
            if df.empty:
                return t, "no data"
            df.index = df.index.tz_localize(None).normalize()
            df.index.name = "Date"
            df[["Open", "High", "Low", "Close", "Adj Close", "Volume", "Stock Splits"]].to_csv(f)
            return t, "ok"
        except Exception as e:
            err = repr(e); time.sleep(2 ** (a + 1))
    return t, "error " + err


def shares(t, out):
    f = out / "shares" / f"{t}.csv"
    if f.exists() or not (out / "prices" / f"{t}.csv").exists():
        return t, "skip"
    for a in range(3):
        try:
            s = yf.Ticker(t).get_shares_full(start=START)
            if s is None or s.empty:
                return t, "no shares"
            s.index = s.index.tz_localize(None).normalize()
            s = s.groupby(level=0).last()
            s.rename("Shares").rename_axis("Date").to_csv(f)
            return t, "ok"
        except Exception as e:
            err = repr(e); time.sleep(2 ** (a + 1))
    return t, "error " + err


def main():
    hist, html, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    (out / "prices").mkdir(parents=True, exist_ok=True)
    (out / "shares").mkdir(parents=True, exist_ok=True)
    h = pd.read_csv(hist, parse_dates=["start_date", "end_date"])
    h = h[h.end_date.isna() | (h.end_date >= "2014-01-01")]
    h["ticker"] = h.ticker.str.replace(".", "-", regex=False)
    cur, _ = dl.universe(html)
    tickers = sorted(set(h.ticker) | set(cur) | {"SPY"})
    with cf.ThreadPoolExecutor(6) as ex:
        p = dict(ex.map(lambda t: prices(t, out), tickers))
    with cf.ThreadPoolExecutor(4) as ex:
        s = dict(ex.map(lambda t: shares(t, out), tickers))
    u = pd.DataFrame({"Ticker": tickers})
    u["InSP500History"] = u.Ticker.isin(set(h.ticker))
    u["Prices"] = u.Ticker.map(p)
    u["Shares"] = u.Ticker.map(s)
    u.to_csv(out / "universe.csv", index=False)
    print(u.Prices.str[:8].value_counts(), u.Shares.str[:8].value_counts(), sep="\n")


if __name__ == "__main__":
    main()
