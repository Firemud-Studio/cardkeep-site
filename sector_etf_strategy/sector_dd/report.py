"""Markdown report from grid results and a detailed run of a chosen strategy."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PCT = ["cagr", "vol", "max_dd", "avg_exposure", "time_invested", "win_rate", "avg_trade_ret",
       "median_trade_ret", "worst_trade", "total_return"]


def _fmt(df: pd.DataFrame, pct: bool = False) -> pd.DataFrame:
    d = df.copy()
    for c in d.columns:
        if d[c].dtype.kind != "f":
            continue
        if pct or c in PCT or str(c).endswith(("_cagr", "_maxdd")):
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else f"{v:.1%}")
        elif c == "final_equity":
            d[c] = d[c].map(lambda v: f"{v:,.0f}")
        else:
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else f"{v:.2f}")
    return d


def md(df: pd.DataFrame, pct: bool = False) -> str:
    d = _fmt(df, pct).astype(str)
    cols = [str(c) for c in d.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(r) + " |" for r in d.values.tolist()]
    return "\n".join(lines)


def pivot(grid: pd.DataFrame, rows: str, cols: str, val: str) -> pd.DataFrame:
    return grid.pivot_table(index=rows, columns=cols, values=val, aggfunc="median")


def build(grid: pd.DataFrame, bench: dict, periods: dict, validation: pd.DataFrame,
          detail: dict | None, out: Path) -> str:
    is_k, oos_k = list(periods)[:2]
    cols = ["name", "cagr", "vol", "sharpe", "max_dd", "calmar", "avg_exposure", "n_trades",
            "win_rate", "avg_trade_ret", "avg_days_held"]
    g = grid.copy()
    s = []
    s.append("# Sector ETF drawdown strategy - backtest report\n")
    s.append(f"Period {bench['start']} to {bench['end']}. {len(g)} strategy configurations. "
             "Initial capital USD 100,000. Fills at the next open with slippage. Idle cash earns "
             "13-week T-bill yield. All returns include dividends.\n")
    s.append("## Benchmark\n")
    s.append(md(pd.DataFrame([bench])[[c for c in cols if c in bench]]))
    s.append("\n## Top 20 configurations by full-period Sharpe\n")
    s.append("Treat this list with caution. Picking the best of "
             f"{len(g)} backtests overstates expected performance (selection bias). "
             "The out-of-sample section below is the more honest view.\n")
    s.append(md(g.sort_values("sharpe", ascending=False).head(20)[cols]))
    s.append("\n## Top 20 by CAGR\n")
    s.append(md(g.sort_values("cagr", ascending=False).head(20)[cols]))

    s.append("\n## Parameter effects (median across all other parameters)\n")
    for dim in ["threshold", "entry", "exit", "max_positions"]:
        t = g.groupby(dim)[["cagr", "sharpe", "max_dd", "avg_exposure", "n_trades", "win_rate"]].median()
        s.append(f"\n### By {dim}\n")
        s.append(md(t.reset_index()))
    s.append("\n### Median Sharpe: threshold x entry\n")
    s.append(md(pivot(g, "threshold", "entry", "sharpe").reset_index()))
    s.append("\n### Median CAGR: threshold x entry\n")
    s.append(md(pivot(g, "threshold", "entry", "cagr").reset_index(), pct=True))
    s.append("\n### Median Sharpe: exit x max_positions\n")
    s.append(md(pivot(g, "exit", "max_positions", "sharpe").reset_index()))

    s.append(f"\n## In-sample / out-of-sample check\n")
    s.append(f"In-sample = {periods[is_k][0]} to {periods[is_k][1]}, out-of-sample = "
             f"{periods[oos_k][0]} to {periods[oos_k][1]}. The 10 configurations with the best "
             "in-sample Sharpe are shown with their out-of-sample results. The OOS slice continues "
             "the same simulation, so positions opened in-sample carry over.\n")
    pc = [f"{is_k}_sharpe", f"{is_k}_cagr", f"{oos_k}_sharpe", f"{oos_k}_cagr", f"{oos_k}_maxdd"]
    top = g.sort_values(f"{is_k}_sharpe", ascending=False).head(10)[["name"] + pc]
    s.append(md(top))
    med = g[pc].median()
    s.append(f"\nMedians across all configurations: IS Sharpe {med.iloc[0]:.2f}, OOS Sharpe "
             f"{med.iloc[2]:.2f}, OOS CAGR {med.iloc[3]:.1%}. SPY: IS Sharpe "
             f"{bench.get(f'{is_k}_sharpe', np.nan):.2f}, OOS Sharpe {bench.get(f'{oos_k}_sharpe', np.nan):.2f}, "
             f"OOS CAGR {bench.get(f'{oos_k}_cagr', np.nan):.1%}.\n")
    rank_corr = g[f"{is_k}_sharpe"].rank().corr(g[f"{oos_k}_sharpe"].rank())
    s.append(f"Rank correlation of IS vs OOS Sharpe across all configs: {rank_corr:.2f}.\n")

    other = [k for k in periods if k not in (is_k, oos_k)]
    if other:
        s.append("\n## Sub-period Sharpe/CAGR (median across configs vs SPY)\n")
        rows = []
        for k in other:
            rows.append({"period": f"{k} ({periods[k][0]}..{periods[k][1]})",
                         "median_cagr": g[f"{k}_cagr"].median(), "median_sharpe": g[f"{k}_sharpe"].median(),
                         "median_maxdd": g[f"{k}_maxdd"].median(),
                         "spy_cagr": bench.get(f"{k}_cagr"), "spy_sharpe": bench.get(f"{k}_sharpe"),
                         "spy_maxdd": bench.get(f"{k}_maxdd")})
        t = pd.DataFrame(rows)
        for c in ["median_cagr", "median_maxdd", "spy_cagr", "spy_maxdd"]:
            t[c] = t[c].map(lambda v: f"{v:.1%}")
        s.append(md(t))

    if detail:
        s.append(f"\n## Detailed run: `{detail['name']}`\n")
        s.append(md(pd.DataFrame([detail["perf"]])))
        s.append("\n### Calendar-year returns\n")
        s.append(md(detail["yearly"]))
        s.append("\n### Positions\n")
        s.append(md(detail["trades"]))

    s.append("\n## Data validation\n")
    s.append(f"{int(validation['ok'].sum())}/{len(validation)} tickers passed every check. "
             "The checks are: splits already applied to Close, dividend factors consistent with "
             "Adj Close, and Close+dividends total return matching Adj Close within 2%. Full table: "
             "`results/validation.csv`.\n")
    text = "\n".join(s) + "\n"
    out.write_text(text)
    return text
