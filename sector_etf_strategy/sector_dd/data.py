"""Download, store (Parquet) and incrementally update daily Yahoo Finance data.

Storage: <data_dir>/<TICKER>.parquet with columns
    Open, High, Low, Close, Adj Close, Volume, Dividends, Stock Splits
indexed by tz-naive trading date. From yfinance with auto_adjust=False:
    Open/High/Low/Close  split-adjusted, NOT dividend-adjusted
    Adj Close            split- AND dividend-adjusted (total-return series)

Incremental update: re-fetch the last few stored days plus anything new. If the
overlapping rows differ, Yahoo has re-based its history (new split, or a
dividend changed the Adj Close factors). In that case the whole history is
downloaded again rather than stitching two incompatible adjustment bases.

Missing prices are never filled here. Gaps are logged and left as gaps.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

log = logging.getLogger("sector_dd.data")

COLS = ["Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits"]
NY = ZoneInfo("America/New_York")
OVERLAP_DAYS = 10
REL_TOL = 1e-6


def _path(data_dir: Path, ticker: str) -> Path:
    return Path(data_dir) / f"{ticker.replace('^', '_')}.parquet"


def _fetch(ticker: str, start: str | None, retries: int = 4) -> pd.DataFrame:
    import yfinance as yf

    err: Exception | None = None
    for attempt in range(retries):
        try:
            kw = dict(auto_adjust=False, actions=True)
            df = (yf.Ticker(ticker).history(start=start, **kw) if start
                  else yf.Ticker(ticker).history(period="max", **kw))
            if df is None or df.empty:
                return pd.DataFrame(columns=COLS)
            df.index = pd.DatetimeIndex(df.index).tz_localize(None).normalize()
            df.index.name = "Date"
            for c in COLS:
                if c not in df.columns:
                    df[c] = 0.0 if c in ("Dividends", "Stock Splits") else np.nan
            df = df[COLS].astype(float)
            df = df[~df.index.duplicated(keep="last")].sort_index()
            return _drop_incomplete_today(df)
        except Exception as e:  # network / rate-limit
            err = e
            wait = 2 ** (attempt + 1)
            log.warning("fetch %s failed (%r), retry in %ss", ticker, e, wait)
            time.sleep(wait)
    raise RuntimeError(f"download failed for {ticker}: {err!r}")


def _drop_incomplete_today(df: pd.DataFrame) -> pd.DataFrame:
    """Drop today's bar if the US session has not closed yet (it is still partial)."""
    now = datetime.now(NY)
    today = pd.Timestamp(now.date())
    if len(df) and df.index[-1] == today and (now.hour, now.minute) < (16, 30):
        return df.iloc[:-1]
    return df


def _write(df: pd.DataFrame, path: Path) -> None:
    tmp = path.with_suffix(".tmp")
    df.to_parquet(tmp)
    tmp.replace(path)


def update_ticker(ticker: str, data_dir: Path, full: bool = False) -> dict:
    """Create or incrementally update one ticker. Returns a manifest entry."""
    path = _path(data_dir, ticker)
    mode = "full"
    if path.exists() and not full:
        old = pd.read_parquet(path)
        start = (old.index[-1] - timedelta(days=OVERLAP_DAYS)).strftime("%Y-%m-%d")
        new = _fetch(ticker, start)
        overlap = old.index.intersection(new.index)
        rebased = False
        for col in ("Close", "Adj Close"):
            a, b = old.loc[overlap, col], new.loc[overlap, col]
            ok = a.notna() & b.notna()
            if ok.any() and (np.abs(a[ok] / b[ok] - 1) > REL_TOL).any():
                rebased = True
        if rebased:
            log.info("%s: adjustment basis changed, re-downloading full history", ticker)
            df = _fetch(ticker, None)
        else:
            mode = "incremental"
            df = pd.concat([old[~old.index.isin(new.index)], new]).sort_index()
    else:
        df = _fetch(ticker, None)
    if df.empty:
        log.error("%s: no data returned", ticker)
        return {"ticker": ticker, "status": "no data"}
    _write(df, path)
    return {"ticker": ticker, "status": "ok", "mode": mode, "rows": int(len(df)),
            "first": str(df.index[0].date()), "last": str(df.index[-1].date()),
            "updated_at": datetime.now(NY).isoformat(timespec="seconds")}


def update_all(tickers: list[str], data_dir: Path, full: bool = False) -> list[dict]:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for t in tickers:
        try:
            out.append(update_ticker(t, data_dir, full))
            log.info("%s", out[-1])
        except Exception as e:
            log.error("%s: %r", t, e)
            out.append({"ticker": t, "status": f"error: {e!r}"})
    (data_dir / "manifest.json").write_text(json.dumps(out, indent=1))
    check_missing(data_dir, tickers)
    return out


def load(ticker: str, data_dir: Path) -> pd.DataFrame:
    path = _path(data_dir, ticker)
    if not path.exists():
        raise FileNotFoundError(f"{path} missing - run `python -m sector_dd update` first")
    return pd.read_parquet(path)


def check_missing(data_dir: Path, tickers: list[str], ref: str = "SPY") -> pd.DataFrame:
    """Log trading days (per the SPY calendar) missing inside each ticker's lifespan."""
    try:
        cal = load(ref, data_dir).index
    except FileNotFoundError:
        return pd.DataFrame()
    rows = []
    for t in tickers:
        if t == ref or t.startswith("^"):
            continue
        try:
            df = load(t, data_dir)
        except FileNotFoundError:
            rows.append({"ticker": t, "missing_days": None, "nan_close": None})
            continue
        span = cal[(cal >= df.index[0]) & (cal <= df.index[-1])]
        missing = span.difference(df.index)
        nan_close = int(df["Close"].isna().sum())
        if len(missing) or nan_close:
            log.warning("%s: %d missing trading days, %d NaN closes (examples: %s)",
                        t, len(missing), nan_close, [str(d.date()) for d in missing[:5]])
        rows.append({"ticker": t, "missing_days": len(missing), "nan_close": nan_close})
    out = pd.DataFrame(rows)
    out.to_csv(Path(data_dir) / "missing_report.csv", index=False)
    return out


def fund_info(tickers: list[str]) -> pd.DataFrame:
    """Current fund characteristics from Yahoo (snapshot as of today, NOT historical)."""
    import yfinance as yf

    rows = []
    for t in tickers:
        try:
            i = yf.Ticker(t).info
            inc = i.get("fundInceptionDate")
            rows.append({
                "ticker": t, "name": i.get("longName"),
                "expense_ratio_pct": i.get("netExpenseRatio"),
                "aum_usd_bn": (i.get("totalAssets") or np.nan) / 1e9,
                "avg_volume_3m": i.get("averageVolume"),
                "avg_dollar_volume_m": (i.get("averageVolume") or np.nan)
                                       * (i.get("previousClose") or np.nan) / 1e6,
                "inception": (pd.Timestamp(inc, unit="s").date() if inc else None),
                "bid": i.get("bid"), "ask": i.get("ask"),
            })
        except Exception as e:
            log.warning("info %s failed: %r", t, e)
            rows.append({"ticker": t})
        time.sleep(0.3)
    df = pd.DataFrame(rows)
    df["snapshot_date"] = datetime.now(NY).date().isoformat()
    return df
