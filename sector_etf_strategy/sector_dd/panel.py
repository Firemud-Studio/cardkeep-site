"""Aligned numpy panel of point-in-time features for the backtest engine.

All features at index i use data up to and including the close of day i only.
Trades decided at the close of i are filled at the open of i+1.

  close      split-adjusted close (signal price; matches what was quoted, up to splits)
  adj_close  split+dividend adjusted close (performance / valuation)
  adj_open   Open * AdjClose/Close (dividend-adjusted open, used for fills)
  high252    rolling 252-day max of close (needs a full 252 days)
  dd         close / high252 - 1   (<= 0)
  sma50/200  simple moving averages of close
  dvol63     63-day median of close*volume (USD; split-invariant)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import data, universe


@dataclass
class Panel:
    dates: pd.DatetimeIndex
    etfs: list[str]
    f: dict[str, dict[str, np.ndarray]]          # f[etf][feature] -> array len(dates)
    rf_daily: np.ndarray                          # daily risk-free return
    bench_adj_close: np.ndarray
    last_idx: dict[str, int] = field(default_factory=dict)
    dd_frames: dict[str, pd.Series] = field(default_factory=dict)


def features(df: pd.DataFrame) -> pd.DataFrame:
    c = df["Close"]
    out = pd.DataFrame(index=df.index)
    out["close"] = c
    out["adj_close"] = df["Adj Close"]
    out["adj_open"] = df["Open"] * df["Adj Close"] / c
    out["high252"] = c.rolling(252, min_periods=252).max()
    out["dd"] = c / out["high252"] - 1
    out["sma50"] = c.rolling(50, min_periods=50).mean()
    out["sma200"] = c.rolling(200, min_periods=200).mean()
    out["dvol63"] = (c * df["Volume"]).rolling(63, min_periods=63).median()
    return out


def build(data_dir: Path, start: str, end: str | None = None,
          etfs: list[str] | None = None) -> Panel:
    etfs = etfs or universe.all_etfs()
    spy = data.load(universe.BENCHMARK, data_dir)
    cal = spy.index[(spy.index >= pd.Timestamp(start))]
    if end:
        cal = cal[cal <= pd.Timestamp(end)]
    f, last_idx, dd_frames = {}, {}, {}
    for t in etfs:
        raw = data.load(t, data_dir)
        feat = features(raw)                       # computed on full history (warm-up before start)
        dd_frames[t] = feat["dd"]
        al = feat.reindex(cal)                     # no filling: missing days stay NaN
        f[t] = {k: al[k].to_numpy(float) for k in al.columns}
        valid = np.where(~np.isnan(f[t]["close"]))[0]
        last_idx[t] = int(valid[-1]) if len(valid) else -1
    try:
        irx = data.load(universe.RISK_FREE, data_dir)["Close"]
        # A yield is a rate, not a price: carrying the last quote across a
        # holiday gap is the standard convention.
        rf = (irx.reindex(cal.union(irx.index)).ffill().reindex(cal) / 100 / 252).shift(1).fillna(0)
        rf_daily = rf.to_numpy(float)
    except FileNotFoundError:
        rf_daily = np.zeros(len(cal))
    bench = spy["Adj Close"].reindex(cal).to_numpy(float)
    return Panel(cal, etfs, f, rf_daily, bench, last_idx, dd_frames)


def dynamic_threshold(dd: pd.Series, q: float, window: int = 2520, min_periods: int = 756,
                      floor: float = 0.10) -> pd.Series:
    """Threshold at date t = -(q-quantile of the ETF's daily drawdowns over the
    previous `window` trading days), using data up to t-1 only."""
    thr = -dd.rolling(window, min_periods=min_periods).quantile(q).shift(1)
    return thr.clip(lower=floor)
