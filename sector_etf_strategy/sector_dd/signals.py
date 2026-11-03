"""Daily monitoring and signal generation.

Runs the configured live strategy on all data up to the latest close. Writes:
  * a market monitor: each sector's active ETF, drawdown, threshold, trend, episode state
  * the simulated portfolio the strategy holds today (scaled to the live capital)
  * the orders the strategy places at the next open

The simulated portfolio starts at `live.start`. Pick a start equal to the day
real money was committed, so the simulation and the real account stay
comparable.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import engine, universe
from .panel import Panel
from .strategy import Strategy


def monitor(panel: Panel, st: Strategy, res: engine.Result) -> pd.DataFrame:
    i = len(panel.dates) - 1
    rows = []
    for s, ts in universe.SECTORS.items():
        ts = [t for t in ts if t in panel.f]
        thr = {t: engine.threshold_array(panel, t, s, st.threshold)[i] for t in ts}
        act = next((t for t in ts if not np.isnan(panel.f[t]["dd"][i]) and not np.isnan(thr[t])
                    and panel.f[t]["dvol63"][i] >= st.min_dollar_volume), None)
        ep = res.episodes.get(s)
        pos = res.positions.get(s)
        t = pos.etf if pos else (ep.etf if ep else act)
        if t is None:
            rows.append({"sector": s, "etf": None, "state": "no eligible ETF"}); continue
        f = panel.f[t]
        c = f["close"][i]
        state = "holding" if pos else ("armed" if ep else "watch")
        row = {"sector": s, "etf": t, "close": c, "high252": f["high252"][i], "drawdown": f["dd"][i],
               "threshold": -thr[t], "dist_to_threshold": f["dd"][i] + thr[t],
               "above_sma50": c > f["sma50"][i], "above_sma200": c > f["sma200"][i],
               "dollar_vol_63d_m": f["dvol63"][i] / 1e6, "state": state}
        if ep:
            row.update({"armed_on": panel.dates[ep.arm_idx].date(), "trough": ep.trough,
                        "recovery_from_trough": c / ep.trough - 1,
                        "stages": ",".join(str(x) for x in ep.filled)})
        rows.append(row)
    return pd.DataFrame(rows)


def generate(panel: Panel, st: Strategy, live_capital: float, out_dir: Path) -> dict:
    res = engine.run(panel, st)
    i = len(panel.dates) - 1
    asof = panel.dates[i].date()
    scale = live_capital / res.equity.iloc[-1]
    mon = monitor(panel, st, res)

    holdings = []
    for s, p in res.positions.items():
        px_adj = panel.f[p.etf]["adj_close"][i]
        raw_close = panel.f[p.etf]["close"][i]
        value = p.units * px_adj * scale
        holdings.append({"sector": s, "etf": p.etf, "entry_date": str(panel.dates[p.first_idx].date()),
                         "days_held": i - p.first_idx, "value_usd": round(value, 2),
                         "shares_at_last_close": round(value / raw_close, 2),
                         "unrealized_ret": p.units * px_adj / p.cost - 1, "stages": p.fills})
    orders = []
    for o in res.pending:
        t = o["etf"]
        raw_close = panel.f[t]["close"][i]
        if o.get("side") == "SELL":
            p = res.positions[o["sector"]]
            orders.append({"side": "SELL", "sector": o["sector"], "etf": t, "reason": o["reason"],
                           "shares": round(p.units * panel.f[t]["adj_close"][i] * scale / raw_close, 2)})
        else:
            amt = o["amount"] * scale
            orders.append({"side": "BUY", "sector": o["sector"], "etf": t, "stage": o["stage"],
                           "amount_usd": round(amt, 2), "approx_shares": round(amt / raw_close, 2)})
    payload = {"as_of": str(asof), "strategy": st.name, "live_capital": live_capital,
               "cash_usd": round(res.cash.iloc[-1] * scale, 2),
               "orders_next_open": orders, "holdings": holdings,
               "monitor": json.loads(mon.to_json(orient="records", date_format="iso"))}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{asof}.json").write_text(json.dumps(payload, indent=1, default=str))
    (out_dir / f"{asof}.md").write_text(render(payload, mon))
    (out_dir / "latest.md").write_text(render(payload, mon))
    return payload


def render(p: dict, mon: pd.DataFrame) -> str:
    m = mon.copy()
    for c in ["drawdown", "threshold", "dist_to_threshold", "recovery_from_trough"]:
        if c in m:
            m[c] = m[c].map(lambda v: "" if pd.isna(v) else f"{v:.1%}")
    for c in ["close", "high252", "trough", "dollar_vol_63d_m"]:
        if c in m:
            m[c] = m[c].map(lambda v: "" if pd.isna(v) else f"{v:,.2f}")
    m = m.fillna("").astype(str)
    lines = [f"# Signals as of {p['as_of']}", "", f"Strategy: `{p['strategy']}`",
             f"Live capital: ${p['live_capital']:,.0f}, simulated cash ${p['cash_usd']:,.0f}", "",
             "## Orders for next open"]
    if p["orders_next_open"]:
        for o in p["orders_next_open"]:
            lines.append("- " + ", ".join(f"{k}={v}" for k, v in o.items()))
    else:
        lines.append("- none")
    lines += ["", "## Holdings"]
    lines += ["- " + ", ".join(f"{k}={v}" for k, v in h.items()) for h in p["holdings"]] or ["- none"]
    lines += ["", "## Sector monitor", "",
              "| " + " | ".join(m.columns) + " |", "|" + "---|" * len(m.columns)]
    lines += ["| " + " | ".join(r) + " |" for r in m.values.tolist()]
    return "\n".join(lines) + "\n"
