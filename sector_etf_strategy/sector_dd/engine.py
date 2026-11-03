"""Event-driven daily portfolio backtest.

Daily sequence for trading day i:
  1. Fill orders decided at the close of i-1 at the open of i: sells first, then
     buys. Fill price = dividend-adjusted open +/- slippage.
  2. Accrue T-bill interest on cash.
  3. Mark positions to market at the dividend-adjusted close.
  4. Exit rules are checked on close-of-day-i data -> sell orders for i+1.
  5. Entry state machine per sector, on close-of-day-i data -> buy orders for i+1.

Units are held in "adjusted" terms (fills and valuation both use Adj Close-based
prices). Dividends are therefore reinvested implicitly, and dividends and splits
are each counted exactly once. Signals use the split-adjusted Close only.

Capital rules
  * At most `max_positions` open positions, and at most one per sector (no overlapping funds).
  * Intended allocation of a new position = equity / max_positions, fixed at
    its first fill. Each stage buys frac * intended, capped by unreserved cash.
  * Proceeds from closed positions return to cash and fund later opportunities.
  * When several sectors qualify on the same day and slots are scarce, deeper
    relative drawdowns (dd / threshold) go first. Ticker order breaks ties.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import universe
from .panel import Panel, dynamic_threshold
from .strategy import Strategy


@dataclass
class Episode:
    etf: str
    arm_idx: int
    thr: float
    peak: float               # 252d high (split-adj close) at arm time
    trough: float
    filled: list = field(default_factory=list)      # per-stage: None | 'filled' | 'skipped' | 'missed'
    intended: float = 0.0


@dataclass
class Position:
    sector: str
    etf: str
    episode: Episode
    first_idx: int
    units: float = 0.0
    cost: float = 0.0          # total cash spent incl. slippage/commission
    peak_val: float = 0.0      # max adj close since entry (for trailing stop)
    fills: list = field(default_factory=list)


@dataclass
class Result:
    strategy: Strategy
    equity: pd.Series
    cash: pd.Series
    exposure: pd.Series
    trades: pd.DataFrame       # one row per closed (or open, marked) position
    fills: pd.DataFrame        # one row per order fill
    pending: list              # orders decided on the last day (for live signals)
    episodes: dict             # final per-sector state (for live signals)
    positions: dict


_THR_CACHE: dict = {}


def threshold_array(panel: Panel, etf: str, sector: str, th) -> np.ndarray:
    key = (id(panel), etf, th)
    if key not in _THR_CACHE:
        n = len(panel.dates)
        if th.kind == "fixed":
            arr = np.full(n, th.value)
        elif th.kind == "sector":
            ov = dict(th.overrides)
            arr = np.full(n, ov.get(sector, universe.SECTOR_THRESHOLDS[sector]))
        elif th.kind == "dynamic":
            s = dynamic_threshold(panel.dd_frames[etf], th.value, th.window, th.min_periods, th.floor)
            arr = s.reindex(panel.dates).to_numpy(float)
        else:
            raise ValueError(th.kind)
        _THR_CACHE[key] = arr
    return _THR_CACHE[key]


def run(panel: Panel, st: Strategy, sectors: dict[str, list[str]] | None = None) -> Result:
    sectors = sectors or universe.SECTORS
    sectors = {s: [t for t in ts if t in panel.f] for s, ts in sectors.items()}
    n = len(panel.dates)
    f = panel.f
    stages = st.stages
    slip = st.slippage_bps / 1e4
    ex = st.exit

    thr = {(s, t): threshold_array(panel, t, s, st.threshold) for s, ts in sectors.items() for t in ts}
    # active ETF per sector per day (first eligible in priority order)
    active: dict[str, list] = {}
    for s, ts in sectors.items():
        act = [None] * n
        for t in reversed(ts):
            ok = (~np.isnan(f[t]["dd"]) & ~np.isnan(thr[(s, t)])
                  & (f[t]["dvol63"] >= st.min_dollar_volume))
            for i in np.where(ok)[0]:
                act[i] = t
        active[s] = act

    cash = st.initial_capital
    positions: dict[str, Position] = {}
    episodes: dict[str, Episode | None] = {s: None for s in sectors}
    need_reset = {s: False for s in sectors}
    last_px: dict[str, float] = {}
    pend_sells: list[tuple[str, str]] = []           # (sector, reason)
    pend_buys: list[dict] = []
    eq = np.empty(n); cash_arr = np.empty(n); expo = np.empty(n)
    closed, fills = [], []

    def close_position(i, s, px, reason, at):
        nonlocal cash
        p = positions.pop(s)
        gross = p.units * px * (1 - slip)
        proceeds = gross - st.commission
        cash += proceeds
        fills.append(dict(date=panel.dates[i], sector=s, etf=p.etf, side="SELL", stage=reason,
                          units=p.units, price=px * (1 - slip), amount=proceeds))
        closed.append(dict(sector=s, etf=p.etf, arm_date=panel.dates[p.episode.arm_idx],
                           threshold=p.episode.thr, entry_date=panel.dates[p.first_idx],
                           exit_date=panel.dates[i], exit_at=at, days_held=i - p.first_idx,
                           invested=p.cost, proceeds=proceeds, ret=proceeds / p.cost - 1,
                           stages=",".join(str(x) for x in p.episode.filled), exit_reason=reason,
                           open=False))
        episodes[s] = None
        need_reset[s] = True

    for i in range(n):
        # ---- 1. fills at open ------------------------------------------------
        if pend_sells:
            keep = []
            for s, reason in pend_sells:
                if s not in positions:
                    continue
                p = positions[s]
                px = f[p.etf]["adj_open"][i]
                if np.isnan(px):
                    keep.append((s, reason)); continue
                close_position(i, s, px, reason, "open")
            pend_sells = keep
        if pend_buys:
            for o in pend_buys:
                s, t = o["sector"], o["etf"]
                px = f[t]["adj_open"][i]
                amt = min(o["amount"], cash - st.commission)
                if np.isnan(px) or amt < st.min_trade:
                    # no tradable price / no cash: the order lapses and the stage can fire again
                    for j in o["stage_idx"]:
                        o["episode"].filled[j] = None
                    continue
                fill_px = px * (1 + slip)
                units = amt / fill_px
                cash -= amt + st.commission
                p = positions.get(s)
                if p is None:
                    p = positions[s] = Position(s, t, o["episode"], i)
                p.units += units
                p.cost += amt + st.commission
                p.fills.append(o["stage"])
                fills.append(dict(date=panel.dates[i], sector=s, etf=t, side="BUY",
                                  stage=o["stage"], units=units, price=fill_px, amount=amt))
            pend_buys = []

        # ---- 2. interest -----------------------------------------------------
        if st.cash_yield and cash > 0:
            cash *= 1 + panel.rf_daily[i]

        # ---- 3. mark to market ----------------------------------------------
        value = 0.0
        for s, p in list(positions.items()):
            px = f[p.etf]["adj_close"][i]
            if np.isnan(px):
                px = last_px.get(p.etf, p.cost / max(p.units, 1e-12))
            else:
                last_px[p.etf] = px
                p.peak_val = max(p.peak_val, px)
            if i > panel.last_idx[p.etf] >= 0:   # fund stopped trading: liquidate at last close
                close_position(i, s, last_px[p.etf] / (1 - slip), "delisted", "last_close")
                continue
            value += p.units * px
        equity = cash + value
        eq[i], cash_arr[i], expo[i] = equity, cash, value / equity if equity > 0 else 0.0

        # ---- 4. exits --------------------------------------------------------
        selling = {s for s, _ in pend_sells}
        for s, p in positions.items():
            if s in selling:
                continue
            c = f[p.etf]["close"][i]
            if np.isnan(c):
                continue
            held = i - p.first_idx
            ac = f[p.etf]["adj_close"][i]
            reason = None
            if held >= ex.max_hold:
                reason = "max_hold"
            elif held >= ex.min_hold:
                if ex.kind == "target" and p.units * ac >= p.cost * (1 + ex.param):
                    reason = "target"
                elif ex.kind == "prior_high" and c >= p.episode.peak:
                    reason = "prior_high"
                elif ex.kind == "trailing" and ac <= p.peak_val * (1 - ex.param):
                    reason = "trailing"
                elif ex.kind == "sma":
                    sma = f[p.etf][f"sma{int(ex.param)}"][i]
                    if not np.isnan(sma) and c < sma:
                        reason = "sma"
            if reason:
                pend_sells.append((s, reason))

        # ---- 5. entries ------------------------------------------------------
        selling = {s for s, _ in pend_sells}
        reserved = 0.0
        n_open = len(positions) - len(selling)
        cands = []
        for s in sectors:
            if s in selling:
                continue
            ep = episodes[s]
            if ep is None:
                t = active[s][i]
                if t is None:
                    continue
                d, th = f[t]["dd"][i], thr[(s, t)][i]
                if need_reset[s]:
                    if d > -th:
                        need_reset[s] = False
                    continue
                if d <= -th:
                    ep = episodes[s] = Episode(t, i, th, f[t]["high252"][i], f[t]["close"][i],
                                               [None] * len(stages))
                else:
                    continue
            t = ep.etf
            c, d = f[t]["close"][i], f[t]["dd"][i]
            if np.isnan(c):
                continue
            ep.trough = min(ep.trough, c)
            any_filled = any(x == "filled" for x in ep.filled)
            if not any_filled and s not in positions:
                if d > -ep.thr * st.disarm_frac or i - ep.arm_idx > st.max_wait:
                    episodes[s] = None
                    need_reset[s] = True
                    continue
            fire = []
            for j, stg in enumerate(stages):
                if ep.filled[j] is not None:
                    continue
                if stg.kind == "drawdown":
                    ok = d <= -(ep.thr + stg.offset)
                else:
                    if j > 0 and not (any_filled or fire):
                        ok = False
                    elif stg.kind == "recovery":
                        ok = c >= ep.trough * (1 + stg.param)
                    else:
                        sma = f[t][f"sma{int(stg.param)}"][i]
                        ok = not np.isnan(sma) and c > sma
                if ok:
                    fire.append(j)
            if fire:
                depth = -d / ep.thr if ep.thr > 0 else 0.0
                cands.append((s in positions, depth, s, fire))
        # existing positions' add-ons first, then new positions by depth
        cands.sort(key=lambda x: (not x[0], -x[1], x[2]))
        for is_open, _, s, fire in cands:
            ep = episodes[s]
            if not is_open:
                if n_open >= st.max_positions:
                    continue
                ep.intended = equity / st.max_positions
                n_open += 1
            filled_frac = sum(stages[k].frac for k, x in enumerate(ep.filled) if x == "filled")
            amount, labels, idxs = 0.0, [], []
            for j in fire:
                stg = stages[j]
                last_confirm = j == len(stages) - 1 and stg.kind != "drawdown"
                frac = (1 - filled_frac) if last_confirm else stg.frac
                if last_confirm:
                    for k in range(j):
                        if ep.filled[k] is None:
                            ep.filled[k] = "skipped"
                avail = cash - reserved - amount
                a = min(frac * ep.intended, avail)
                if a < st.min_trade:
                    ep.filled[j] = "missed"
                    continue
                amount += a
                filled_frac += frac
                ep.filled[j] = "filled"
                labels.append(f"S{j + 1}")
                idxs.append(j)
            if amount > 0:
                reserved += amount
                pend_buys.append(dict(sector=s, etf=ep.etf, amount=amount, episode=ep,
                                      stage="+".join(labels), stage_idx=idxs,
                                      decided=panel.dates[i]))
            elif not is_open:
                n_open -= 1
                if all(x is not None for x in ep.filled):
                    episodes[s] = None
                    need_reset[s] = True

    # open positions at the end are reported (marked to market), not sold
    for s, p in positions.items():
        val = p.units * last_px.get(p.etf, np.nan)
        closed.append(dict(sector=s, etf=p.etf, arm_date=panel.dates[p.episode.arm_idx],
                           threshold=p.episode.thr, entry_date=panel.dates[p.first_idx],
                           exit_date=panel.dates[-1], exit_at="mark", days_held=n - 1 - p.first_idx,
                           invested=p.cost, proceeds=val, ret=val / p.cost - 1,
                           stages=",".join(str(x) for x in p.episode.filled), exit_reason="open",
                           open=True))
    idx = panel.dates
    return Result(st, pd.Series(eq, idx), pd.Series(cash_arr, idx), pd.Series(expo, idx),
                  pd.DataFrame(closed), pd.DataFrame(fills),
                  pending=[{k: v for k, v in o.items() if k not in ("episode", "stage_idx")}
                           for o in pend_buys]
                  + [{"sector": s, "side": "SELL", "reason": r, "etf": positions[s].etf}
                     for s, r in pend_sells if s in positions],
                  episodes=episodes, positions=positions)
