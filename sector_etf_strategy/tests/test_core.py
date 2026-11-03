"""Unit tests. The tiny synthetic price paths here exist only to test engine
mechanics deterministically. They are never used for research results."""
import numpy as np
import pandas as pd
import pytest

from sector_dd import engine, validate
from sector_dd.panel import Panel, dynamic_threshold, features
from sector_dd.strategy import Exit, Stage, Strategy, Threshold


def frame(close, dividends=None, start="2010-01-04"):
    idx = pd.bdate_range(start, periods=len(close))
    c = pd.Series(close, idx, dtype=float)
    d = pd.Series(0.0 if dividends is None else dividends, idx)
    # Yahoo-style adjustment: factor for days before an ex-date multiplied by (1 - D/Cprev)
    step = (1 - d / c.shift(1)).fillna(1.0)
    factor = step[::-1].cumprod()[::-1].shift(-1).fillna(1.0)
    return pd.DataFrame({"Open": c, "High": c * 1.01, "Low": c * 0.99, "Close": c,
                         "Adj Close": c * factor, "Volume": 1e7, "Dividends": d, "Stock Splits": 0.0})


def make_panel(frames: dict) -> Panel:
    dates = next(iter(frames.values())).index
    f, last, ddf = {}, {}, {}
    for t, df in frames.items():
        ft = features(df)
        ddf[t] = ft["dd"]
        f[t] = {k: ft[k].reindex(dates).to_numpy(float) for k in ft.columns}
        last[t] = len(dates) - 1
    return Panel(dates, list(frames), f, np.zeros(len(dates)), np.ones(len(dates)), last, ddf)


def path_with_crash(n=900, crash_at=400, depth=0.45, rebound=0.6):
    up = np.linspace(100, 120, crash_at)
    down = np.linspace(120, 120 * (1 - depth), 100)
    rec = np.linspace(120 * (1 - depth), 120 * (1 - depth) * (1 + rebound), n - crash_at - 100)
    return np.concatenate([up, down, rec])


def test_features_have_no_lookahead():
    df = frame(path_with_crash())
    full = features(df)
    cut = features(df.iloc[:450])
    pd.testing.assert_frame_equal(full.iloc[:450], cut)


def test_dynamic_threshold_uses_past_only():
    dd = features(frame(path_with_crash(1500))).dd
    a = dynamic_threshold(dd, 0.1, 500, 100)
    dd2 = dd.copy(); dd2.iloc[1000] = -0.99
    b = dynamic_threshold(dd2, 0.1, 500, 100)
    assert a.iloc[1000] == b.iloc[1000]          # today's value doesn't affect today's threshold


SECT = {"Technology": ["AAA"], "Energy": ["BBB"]}


def run(st, closes):
    p = make_panel({t: frame(c) for t, c in closes.items()})
    return p, engine.run(p, st, sectors={s: [t] for s, t in zip(SECT, closes)})


def base(**kw):
    d = dict(threshold=Threshold("fixed", 0.30), entry="A_immediate", exit=Exit("time", 252),
             max_positions=2, slippage_bps=0, cash_yield=False, min_dollar_volume=0)
    d.update(kw)
    return Strategy(**d)


def test_immediate_entry_fills_next_open_after_signal():
    c = path_with_crash()
    p, r = run(base(), {"AAA": c, "BBB": np.full(len(c), 50.0)})
    dd = p.f["AAA"]["dd"]
    sig = int(np.where(dd <= -0.30)[0][0])
    buy = r.fills[r.fills.side == "BUY"].iloc[0]
    assert buy.date == p.dates[sig + 1]
    assert buy.price == pytest.approx(p.f["AAA"]["adj_open"][sig + 1])


def test_staged_stages_fire_once_and_respect_fractions():
    st = base(entry="S1_staged_rec10", exit=Exit("time", 400), max_positions=1)
    c = path_with_crash(depth=0.5)
    p, r = run(st, {"AAA": c, "BBB": np.full(len(c), 50.0)})
    buys = r.fills[(r.fills.side == "BUY") & (r.fills.etf == "AAA")]
    assert list(buys.stage) == ["S1", "S2", "S3"]
    a = buys.amount.to_numpy()
    assert a[0] == pytest.approx(30_000, rel=1e-6) and a[1] == pytest.approx(30_000, rel=1e-6)
    assert a[2] == pytest.approx(40_000, rel=1e-6)


def test_confirmation_buys_remaining_when_deep_stage_never_hit():
    st = base(entry="S1_staged_rec10", exit=Exit("time", 400), max_positions=1)
    c = path_with_crash(depth=0.35)               # never reaches 40%
    p, r = run(st, {"AAA": c, "BBB": np.full(len(c), 50.0)})
    buys = r.fills[r.fills.side == "BUY"]
    assert list(buys.stage) == ["S1", "S3"]
    assert buys.amount.sum() == pytest.approx(100_000, rel=1e-6)
    assert r.trades.iloc[0].stages == "filled,skipped,filled"


def test_max_positions_and_cash_never_negative():
    c = path_with_crash()
    p, r = run(base(max_positions=1), {"AAA": c, "BBB": c * 2})
    assert r.cash.min() >= -1e-6
    # only one position at a time
    t = r.trades.sort_values("entry_date")
    assert (t.entry_date.iloc[1:].values >= t.exit_date.iloc[:-1].values).all() if len(t) > 1 else True
    assert len(r.trades) == 1


def test_equity_accounting_and_time_exit():
    c = path_with_crash()
    p, r = run(base(max_positions=1), {"AAA": c, "BBB": np.full(len(c), 50.0)})
    tr = r.trades.iloc[0]
    assert tr.days_held == 253                  # decided after 252 days, filled next open
    assert r.equity.iloc[-1] == pytest.approx(r.cash.iloc[-1])
    assert r.equity.iloc[-1] == pytest.approx(100_000 * (1 + tr.ret))


def test_no_reentry_until_reset():
    c = path_with_crash(depth=0.6, rebound=0.05)   # stays deep below threshold after exit
    p, r = run(base(max_positions=1, exit=Exit("time", 100)), {"AAA": c, "BBB": np.full(len(c), 50.0)})
    assert len(r.trades) == 1


def test_validation_flags_double_counted_dividends():
    n = 300
    c = np.full(n, 100.0)
    d = np.zeros(n); d[100::60] = 1.0
    df = frame(c, d)
    assert validate.validate_frame("X", df)["ok"]
    bad = df.copy(); bad["Adj Close"] = bad["Adj Close"] * bad["Adj Close"] / bad["Close"]  # adjusted twice
    out = validate.validate_frame("X", bad)
    assert not out["ok"] and out["div_factor_bad_days"] > 0
