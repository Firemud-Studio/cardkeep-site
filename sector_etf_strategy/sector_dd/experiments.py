"""Parameter grid, parallel execution and summary tables."""
from __future__ import annotations

import itertools
import multiprocessing as mp
import os

import pandas as pd

from . import engine, metrics
from .panel import Panel
from .strategy import ENTRY_MODES, EXITS, Strategy, Threshold

_PANEL: Panel | None = None
_PERIODS: dict = {}


def build_grid(cfg: dict, base: dict) -> list[Strategy]:
    g = cfg["grid"]
    ths = ([Threshold("fixed", v) for v in g["fixed_thresholds"]]
           + [Threshold("dynamic", q) for q in g["dynamic_quantiles"]]
           + ([Threshold("sector")] if g.get("sector_thresholds", True) else []))
    entries = g.get("entries") or list(ENTRY_MODES)
    exits = g.get("exits") or list(EXITS)
    return [Strategy(threshold=t, entry=e, exit=EXITS[x], max_positions=n, **base)
            for t, e, x, n in itertools.product(ths, entries, exits, g["max_positions"])]


def evaluate(st: Strategy) -> dict:
    p = _PANEL
    res = engine.run(p, st)
    rf = pd.Series(p.rf_daily, p.dates)
    row = {"name": st.name, "threshold": st.threshold.label, "entry": st.entry,
           "exit": st.exit.label, "max_positions": st.max_positions}
    row.update(metrics.perf(res.equity, rf, res.exposure))
    row.update(metrics.trade_stats(res.trades))
    row.update(metrics.period_slices(res.equity, rf, _PERIODS))
    return row


def _init(panel, periods):
    global _PANEL, _PERIODS
    _PANEL, _PERIODS = panel, periods


def run_grid(panel: Panel, strategies: list[Strategy], periods: dict, procs: int | None = None) -> pd.DataFrame:
    procs = procs or max(1, (os.cpu_count() or 2) - 0)
    _init(panel, periods)
    if procs == 1:
        rows = [evaluate(s) for s in strategies]
    else:
        ctx = mp.get_context("fork")
        with ctx.Pool(procs, initializer=_init, initargs=(panel, periods)) as pool:
            rows = pool.map(evaluate, strategies, chunksize=8)
    return pd.DataFrame(rows)


def benchmark_row(panel: Panel, periods: dict) -> dict:
    rf = pd.Series(panel.rf_daily, panel.dates)
    eq = pd.Series(panel.bench_adj_close, panel.dates)
    row = {"name": "SPY buy&hold", "threshold": "-", "entry": "-", "exit": "-", "max_positions": "-"}
    row.update(metrics.perf(eq, rf, pd.Series(1.0, panel.dates)))
    row.update(metrics.period_slices(eq, rf, periods))
    return row
