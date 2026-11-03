"""Strategy specification: thresholds, entry stages, exits, portfolio rules."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Threshold:
    """kind='fixed'   value = drawdown magnitude, e.g. 0.30
       kind='dynamic' value = quantile of the ETF's own trailing drawdown distribution, e.g. 0.10
       kind='sector'  per-sector magnitudes from universe.SECTOR_THRESHOLDS (or `overrides`)"""
    kind: str = "fixed"
    value: float = 0.30
    window: int = 2520
    min_periods: int = 756
    floor: float = 0.10
    overrides: tuple = ()          # (("Technology", 0.4), ...)

    @property
    def label(self) -> str:
        if self.kind == "fixed":
            return f"fix{int(round(self.value * 100))}"
        if self.kind == "dynamic":
            return f"dynq{int(round(self.value * 100)):02d}"
        return "sector"


@dataclass(frozen=True)
class Stage:
    """One purchase tranche of a position.

    kind='drawdown' fires when dd <= -(arm_threshold + offset)
    kind='recovery' fires when close >= trough_since_arm * (1 + param)
    kind='sma'      fires when close > SMA(param)   (param 50 or 200)
    frac           share of the intended allocation. If the LAST stage is a
                   confirmation stage (recovery/sma), it buys whatever is still
                   unfilled. Earlier drawdown stages that never triggered are
                   then forfeited, never bought twice.
    Confirmation stages that are not first need at least one earlier fill.
    """
    kind: str
    frac: float = 1.0
    offset: float = 0.0
    param: float = 0.0


@dataclass(frozen=True)
class Exit:
    """kind: 'time'      sell after max_hold trading days
             'target'    sell when position return >= param (or at max_hold)
             'prior_high' sell when close regains the 252d high seen at arm time (or max_hold)
             'trailing'  after min_hold, sell when adj close falls `param` below its peak since entry
             'sma'       after min_hold, sell on a close below SMA(param)
       All kinds also exit at max_hold (trading days from the first fill)."""
    kind: str = "time"
    max_hold: int = 756
    min_hold: int = 0
    param: float = 0.0

    @property
    def label(self) -> str:
        y = self.max_hold / 252
        if self.kind == "time":
            return f"hold{y:g}y"
        if self.kind == "target":
            return f"target{int(self.param * 100)}_max{y:g}y"
        if self.kind == "prior_high":
            return f"priorhigh_max{y:g}y"
        if self.kind == "trailing":
            return f"trail{int(self.param * 100)}_min{self.min_hold / 252:g}y_max{y:g}y"
        if self.kind == "sma":
            return f"sma{int(self.param)}_min{self.min_hold / 252:g}y_max{y:g}y"
        return self.kind


ENTRY_MODES: dict[str, tuple[Stage, ...]] = {
    "A_immediate": (Stage("drawdown", 1.0),),
    "B_recover5":  (Stage("recovery", 1.0, param=0.05),),
    "C_recover10": (Stage("recovery", 1.0, param=0.10),),
    "D_sma50":     (Stage("sma", 1.0, param=50),),
    "E_sma200":    (Stage("sma", 1.0, param=200),),
    # Staged: 30% at threshold, 30% 10 points deeper, remaining 40% on confirmation
    "S1_staged_rec10": (Stage("drawdown", 0.3), Stage("drawdown", 0.3, offset=0.10),
                        Stage("recovery", 0.4, param=0.10)),
    "S2_staged_sma50": (Stage("drawdown", 0.3), Stage("drawdown", 0.3, offset=0.10),
                        Stage("sma", 0.4, param=50)),
}

EXITS: dict[str, Exit] = {
    "hold1y": Exit("time", 252),
    "hold2y": Exit("time", 504),
    "hold3y": Exit("time", 756),
    "target50_max3y": Exit("target", 756, param=0.50),
    "priorhigh_max3y": Exit("prior_high", 756),
    "trail20_min1y_max3y": Exit("trailing", 756, min_hold=252, param=0.20),
    "sma200_min1y_max3y": Exit("sma", 756, min_hold=252, param=200),
}


@dataclass(frozen=True)
class Strategy:
    threshold: Threshold = Threshold()
    entry: str = "A_immediate"
    exit: Exit = Exit()
    max_positions: int = 5
    initial_capital: float = 100_000.0
    slippage_bps: float = 5.0           # per side, applied to the fill price
    commission: float = 0.0             # USD per order
    cash_yield: bool = True             # idle cash earns the 13-week T-bill rate
    min_dollar_volume: float = 10e6     # point-in-time eligibility (63d median)
    disarm_frac: float = 0.5            # unfilled episode cancelled if dd recovers above thr*disarm_frac
    max_wait: int = 252                 # ... or after this many days without a first fill
    min_trade: float = 100.0
    stages_override: tuple = field(default=())

    @property
    def stages(self) -> tuple[Stage, ...]:
        return self.stages_override or ENTRY_MODES[self.entry]

    @property
    def name(self) -> str:
        return f"{self.threshold.label}|{self.entry}|{self.exit.label}|N{self.max_positions}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["name"] = self.name
        return d
