"""Validate Yahoo price-adjustment conventions so splits and dividends are not double-counted.

Checks per ticker:
  1. Basic sanity: positive prices, Low <= Close <= High, no NaN closes.
  2. Splits already applied: on split days `Close` must not jump by the split
     ratio (it is split-adjusted). A jump > 30% on a split day means a missed adjustment.
  3. Dividend factor consistency: Yahoo's adjustment ratio r = AdjClose/Close
     should change ONLY on ex-dividend days, by r[t-1]/r[t] = 1 - D[t]/Close[t-1].
  4. Total-return reconciliation: compounding (Close[t] + D[t]) / Close[t-1]
     should match AdjClose[end]/AdjClose[start]. If dividends were counted twice,
     or not at all, this ratio drifts far from 1.
  5. Extreme moves: |daily return| > 25% are listed for manual review.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def validate_frame(t: str, df: pd.DataFrame) -> dict:
    c, a = df["Close"], df["Adj Close"]
    d = df["Dividends"].fillna(0.0)
    s = df["Stock Splits"].fillna(0.0)
    out: dict = {"ticker": t, "rows": len(df), "first": df.index[0].date(), "last": df.index[-1].date()}

    out["nan_close"] = int(c.isna().sum())
    out["nonpositive"] = int((df[["Open", "High", "Low", "Close"]] <= 0).any(axis=1).sum())
    tol = 1e-3 * c
    out["close_outside_hl"] = int(((c > df["High"] + tol) | (c < df["Low"] - tol)).sum())

    ret = c.pct_change()
    split_days = s[s > 0].index
    out["split_events"] = len(split_days)
    out["unadjusted_splits"] = int((ret.reindex(split_days).abs() > 0.30).sum())

    r = a / c
    step = (r.shift(1) / r)[1:]
    expected = (1 - d / c.shift(1))[1:]
    err = (step - expected).abs()
    out["div_events"] = int((d > 0).sum())
    out["div_factor_max_err"] = float(err.max()) if len(err) else 0.0
    out["div_factor_bad_days"] = int((err > 2e-3).sum())

    gross = ((c + d) / c.shift(1)).iloc[1:]
    tr_manual = float(np.nanprod(gross))
    tr_adj = float(a.iloc[-1] / a.iloc[0])
    out["tr_manual"] = tr_manual
    out["tr_adjclose"] = tr_adj
    out["tr_ratio"] = tr_adj / tr_manual if tr_manual else np.nan

    big = ret[ret.abs() > 0.25]
    out["extreme_moves"] = "; ".join(f"{i.date()}:{v:+.0%}" for i, v in big.items())
    out["ok"] = bool(out["nan_close"] == 0 and out["nonpositive"] == 0
                     and out["unadjusted_splits"] == 0
                     and abs(out["tr_ratio"] - 1) < 0.02
                     and out["div_factor_bad_days"] <= max(3, 0.01 * out["div_events"]))
    return out


def validate_all(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    return pd.DataFrame([validate_frame(t, df) for t, df in frames.items()])
