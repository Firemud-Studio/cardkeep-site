"""Performance and trade statistics."""
from __future__ import annotations

import numpy as np
import pandas as pd

TD = 252


def perf(equity: pd.Series, rf_daily: pd.Series | None = None, exposure: pd.Series | None = None) -> dict:
    eq = equity.dropna()
    if len(eq) < 2:
        return {}
    r = eq.pct_change().dropna()
    rf = (rf_daily.reindex(r.index).fillna(0) if rf_daily is not None else 0 * r)
    ex = r - rf
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1 if years > 0 else np.nan
    vol = r.std() * np.sqrt(TD)
    dd = eq / eq.cummax() - 1
    down = ex[ex < 0]
    out = {
        "start": eq.index[0].date(), "end": eq.index[-1].date(),
        "final_equity": eq.iloc[-1], "total_return": eq.iloc[-1] / eq.iloc[0] - 1,
        "cagr": cagr, "vol": vol,
        "sharpe": ex.mean() / ex.std() * np.sqrt(TD) if ex.std() > 0 else np.nan,
        "sortino": ex.mean() / np.sqrt((down ** 2).mean()) * np.sqrt(TD) if len(down) else np.nan,
        "max_dd": dd.min(),
        "calmar": cagr / -dd.min() if dd.min() < 0 else np.nan,
        "ulcer": float(np.sqrt((dd ** 2).mean())),
    }
    if exposure is not None:
        e = exposure.reindex(eq.index)
        out["avg_exposure"] = e.mean()
        out["time_invested"] = (e > 0.01).mean()
    return out


def trade_stats(trades: pd.DataFrame) -> dict:
    if trades is None or trades.empty:
        return {"n_trades": 0}
    c = trades[~trades["open"]]
    out = {"n_trades": len(c), "n_open": int(trades["open"].sum())}
    if len(c):
        gains, losses = c.loc[c.ret > 0, "proceeds"] - c.loc[c.ret > 0, "invested"], \
            c.loc[c.ret <= 0, "invested"] - c.loc[c.ret <= 0, "proceeds"]
        out.update({
            "win_rate": (c.ret > 0).mean(), "avg_trade_ret": c.ret.mean(),
            "median_trade_ret": c.ret.median(), "worst_trade": c.ret.min(),
            "best_trade": c.ret.max(), "avg_days_held": c.days_held.mean(),
            "profit_factor": gains.sum() / losses.sum() if losses.sum() > 0 else np.inf,
        })
    return out


def period_slices(equity: pd.Series, rf: pd.Series, periods: dict[str, tuple[str, str]]) -> dict:
    out = {}
    for k, (a, b) in periods.items():
        s = equity.loc[a:b]
        if len(s) > 20:
            p = perf(s, rf)
            out[f"{k}_cagr"] = p["cagr"]
            out[f"{k}_sharpe"] = p["sharpe"]
            out[f"{k}_maxdd"] = p["max_dd"]
    return out
