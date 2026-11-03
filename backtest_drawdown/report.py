"""Render results/*.csv into REPORT_TABLES.md."""
from pathlib import Path
import pandas as pd

r = Path(__file__).parent / "results"
pct = lambda x: f"{x:.1%}"
out = []
s = pd.read_csv(r / "summary.csv", index_col=0)
rows = {"Trades": "Trades", "AvgReturn": "Average 1-yr return", "MedianReturn": "Median 1-yr return",
        "WinRate": "Win rate", "AvgTradeMaxDD": "Avg max drawdown during hold",
        "WorstTradeMaxDD": "Worst max drawdown during hold", "BestReturn": "Best trade",
        "WorstReturn": "Worst trade", "SPYAvgReturn": "S&P 500 (SPY) avg, same windows",
        "SPYMedianReturn": "S&P 500 (SPY) median, same windows", "AvgExcess": "Avg excess vs SPY",
        "MedianExcess": "Median excess vs SPY", "BeatSPYRate": "% of trades beating SPY"}
t = s[list(rows)].T.rename(index=rows)
t = t.apply(lambda c: [f"{int(v)}" if i == 0 else pct(v) for i, v in enumerate(c)])
out += ["## Trade statistics (entry signals 2015-2025, 1-year hold)\n", t.to_markdown(), ""]

p = pd.read_csv(r / "portfolio_summary.csv", index_col=0)
p = p.map(lambda v: f"{v:.2f}") if hasattr(p, "map") else p
p["TotalReturn"] = pd.read_csv(r / "portfolio_summary.csv", index_col=0).TotalReturn.map(pct)
for c in ["CAGR", "MaxDrawdown", "AnnVol"]:
    p[c] = pd.read_csv(r / "portfolio_summary.csv", index_col=0)[c].map(pct)
out += ["## Portfolio view (equal weight across open positions, cash when none), Jan 2015 - last exit\n",
        p.to_markdown(), ""]

c = pd.read_csv(r / "portfolio_calendar_returns.csv", index_col=0).map(pct)
out += ["## Portfolio calendar-year returns vs S&P 500 (SPY)\n", c.to_markdown(), ""]

y = pd.read_csv(r / "by_entry_year.csv")
for X, g in y.groupby("Threshold"):
    g = g.set_index("EntryYear")[["Trades", "AvgReturn", "MedianReturn", "WinRate", "AvgTradeMaxDD",
                                  "WorstTradeMaxDD", "SPYAvgReturn", "AvgExcess"]]
    g = g.reindex(range(2015, 2026))
    g["Trades"] = g.Trades.fillna(0).astype(int)
    for col in g.columns[1:]:
        g[col] = g[col].map(lambda v: "" if pd.isna(v) else pct(v))
    out += [f"## By entry year: {X} drop\n", g.to_markdown(), ""]
(Path(__file__).parent / "REPORT_TABLES.md").write_text("\n".join(out))
