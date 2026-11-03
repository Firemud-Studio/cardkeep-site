"""Command line interface.

  python -m sector_dd update [--full]     download / incrementally update Parquet data
  python -m sector_dd validate            check split/dividend adjustment conventions
  python -m sector_dd universe-info       snapshot of current fund facts (ER, AUM, volume)
  python -m sector_dd backtest [opts]     run one strategy, write equity/trades CSVs
  python -m sector_dd grid                run the full parameter grid
  python -m sector_dd report              build results/REPORT.md from grid results
  python -m sector_dd signals [--no-update]  daily monitor + orders for the next open
"""
from __future__ import annotations

import argparse
import logging
import sys
import tomllib
from pathlib import Path

import pandas as pd

from . import data, engine, experiments, metrics, report, signals, universe, validate
from .panel import build as build_panel
from .strategy import EXITS, Strategy, Threshold

ROOT = Path(__file__).resolve().parent.parent


def load_cfg(path: Path) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def base_kwargs(cfg: dict) -> dict:
    b = cfg["backtest"]
    return dict(initial_capital=float(b["initial_capital"]), slippage_bps=float(b["slippage_bps"]),
                commission=float(b["commission"]), cash_yield=bool(b["cash_yield"]),
                min_dollar_volume=float(b["min_dollar_volume"]))


def strategy_from(sec: dict, cfg: dict) -> Strategy:
    return Strategy(threshold=Threshold(sec["threshold_kind"], float(sec.get("threshold_value", 0))),
                    entry=sec["entry"], exit=EXITS[sec["exit"]],
                    max_positions=int(sec["max_positions"]), **base_kwargs(cfg))


def setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=[logging.FileHandler(log_dir / "sector_dd.log"), logging.StreamHandler()])
    logging.getLogger("yfinance").setLevel(logging.WARNING)


def periods(cfg: dict) -> dict:
    return {k: tuple(v) for k, v in cfg["periods"].items()}


def detail_run(panel, st: Strategy) -> dict:
    res = engine.run(panel, st)
    rf = pd.Series(panel.rf_daily, panel.dates)
    perf = {**metrics.perf(res.equity, rf, res.exposure), **metrics.trade_stats(res.trades)}
    yearly = res.equity.resample("YE").last()
    yearly = pd.concat([pd.Series([res.equity.iloc[0]], [res.equity.index[0]]), yearly]).pct_change().dropna()
    spy = pd.Series(panel.bench_adj_close, panel.dates)
    spy_y = pd.concat([spy.iloc[:1], spy.resample("YE").last()]).pct_change().dropna()
    yr = pd.DataFrame({"year": yearly.index.year, "strategy": yearly.values,
                       "spy": spy_y.values[:len(yearly)]})
    yr["strategy"] = yr["strategy"].map(lambda v: f"{v:.1%}")
    yr["spy"] = yr["spy"].map(lambda v: f"{v:.1%}")
    tr = res.trades[["sector", "etf", "arm_date", "entry_date", "exit_date", "days_held", "invested",
                     "ret", "stages", "exit_reason"]].copy()
    for c in ["arm_date", "entry_date", "exit_date"]:
        tr[c] = pd.to_datetime(tr[c]).dt.date
    tr["ret"] = tr["ret"].map(lambda v: f"{v:.1%}")
    tr["invested"] = tr["invested"].map(lambda v: f"{v:,.0f}")
    return {"name": st.name, "perf": {k: v for k, v in perf.items() if k not in ("start", "end")},
            "yearly": yr, "trades": tr, "res": res}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sector_dd")
    ap.add_argument("--config", default=str(ROOT / "config.toml"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("update"); u.add_argument("--full", action="store_true")
    sub.add_parser("validate")
    sub.add_parser("universe-info")
    b = sub.add_parser("backtest")
    b.add_argument("--threshold-kind", default="fixed", choices=["fixed", "dynamic", "sector"])
    b.add_argument("--threshold-value", type=float, default=0.30)
    b.add_argument("--entry", default="A_immediate")
    b.add_argument("--exit", default="hold2y", choices=list(EXITS))
    b.add_argument("--max-positions", type=int, default=5)
    g = sub.add_parser("grid"); g.add_argument("--procs", type=int, default=None)
    sub.add_parser("report")
    s = sub.add_parser("signals"); s.add_argument("--no-update", action="store_true")
    s.add_argument("--start", default=None)
    a = ap.parse_args(argv)

    cfg = load_cfg(Path(a.config))
    data_dir = ROOT / cfg["data"]["dir"]
    res_dir = ROOT / "results"; res_dir.mkdir(exist_ok=True)
    setup_logging(ROOT / "logs")
    bt = cfg["backtest"]
    end = bt.get("end") or None

    if a.cmd == "update":
        r = data.update_all(universe.all_tickers(), data_dir, a.full)
        bad = [x for x in r if x.get("status") != "ok"]
        return 1 if bad else 0

    if a.cmd == "validate":
        frames = {t: data.load(t, data_dir) for t in universe.all_etfs() + [universe.BENCHMARK]}
        v = validate.validate_all(frames)
        v.to_csv(res_dir / "validation.csv", index=False)
        print(v[["ticker", "rows", "first", "last", "split_events", "div_events",
                 "div_factor_max_err", "tr_ratio", "ok"]].to_string(index=False))
        return 0 if v["ok"].all() else 1

    if a.cmd == "universe-info":
        df = data.fund_info(universe.all_etfs())
        df.insert(1, "sector", [universe.sector_of(t) for t in df["ticker"]])
        df.insert(2, "role", [["primary", "secondary", "backup"][universe.SECTORS[universe.sector_of(t)].index(t)]
                              for t in df["ticker"]])
        df.to_csv(res_dir / "universe_snapshot.csv", index=False)
        print(df.to_string(index=False))
        return 0

    if a.cmd == "backtest":
        panel = build_panel(data_dir, bt["start"], end)
        st = Strategy(threshold=Threshold(a.threshold_kind, a.threshold_value), entry=a.entry,
                      exit=EXITS[a.exit], max_positions=a.max_positions, **base_kwargs(cfg))
        d = detail_run(panel, st)
        res = d["res"]
        tag = st.name.replace("|", "_")
        pd.DataFrame({"equity": res.equity, "cash": res.cash, "exposure": res.exposure}).to_csv(
            res_dir / f"equity_{tag}.csv")
        res.trades.to_csv(res_dir / f"positions_{tag}.csv", index=False)
        res.fills.to_csv(res_dir / f"fills_{tag}.csv", index=False)
        print(st.name)
        for k, v in d["perf"].items():
            print(f"  {k:18s} {v:.4f}" if isinstance(v, float) else f"  {k:18s} {v}")
        print(d["trades"].to_string(index=False))
        return 0

    if a.cmd == "grid":
        panel = build_panel(data_dir, bt["start"], end)
        strategies = experiments.build_grid(cfg, base_kwargs(cfg))
        logging.info("running %d configurations", len(strategies))
        grid = experiments.run_grid(panel, strategies, periods(cfg), a.procs)
        grid.to_csv(res_dir / "grid_results.csv", index=False)
        bench = experiments.benchmark_row(panel, periods(cfg))
        pd.DataFrame([bench]).to_csv(res_dir / "benchmark.csv", index=False)
        logging.info("wrote %s", res_dir / "grid_results.csv")
        return 0

    if a.cmd == "report":
        panel = build_panel(data_dir, bt["start"], end)
        grid = pd.read_csv(res_dir / "grid_results.csv")
        bench = pd.read_csv(res_dir / "benchmark.csv").iloc[0].to_dict()
        val_path = res_dir / "validation.csv"
        val = pd.read_csv(val_path) if val_path.exists() else pd.DataFrame({"ok": []})
        d = detail_run(panel, strategy_from(cfg["detail"], cfg))
        d["res"].trades.to_csv(res_dir / "detail_positions.csv", index=False)
        d["res"].fills.to_csv(res_dir / "detail_fills.csv", index=False)
        pd.DataFrame({"equity": d["res"].equity, "exposure": d["res"].exposure,
                      "spy": pd.Series(panel.bench_adj_close, panel.dates)}).to_csv(res_dir / "detail_equity.csv")
        report.build(grid, bench, periods(cfg), val, d, res_dir / "REPORT.md")
        print(f"wrote {res_dir / 'REPORT.md'}")
        return 0

    if a.cmd == "signals":
        if not a.no_update:
            data.update_all(universe.all_tickers(), data_dir)
        live = cfg["live"]
        panel = build_panel(data_dir, a.start or live.get("start", bt["start"]))
        st = strategy_from(live, cfg)
        p = signals.generate(panel, st, float(live["capital"]), ROOT / "signals")
        print((ROOT / "signals" / "latest.md").read_text())
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
