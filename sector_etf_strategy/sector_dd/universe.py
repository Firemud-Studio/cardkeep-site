"""Fixed ETF universe: up to three ETFs per GICS sector, in priority order.

Priority = primary, secondary, backup. At every date the backtest trades only the
first ETF in that order that is *eligible at that date* (enough history and
enough trailing dollar volume, both computed from real data). So only one ETF
per sector is ever bought, which avoids holding overlapping funds.

Why these funds (selection rationale; current fund facts can be re-checked with
`python -m sector_dd universe-info`, which pulls them live from Yahoo):
  * Select Sector SPDRs (XL*): lowest cost, deepest liquidity, history from Dec 1998.
  * Vanguard sector ETFs (V*): low cost, large AUM, history from 2004.
  * iShares US sector ETFs (IY*/ID*): expense ratio about 0.39%, above the 0.25%
    target. They are kept only as backups because their history starts in 2000.
Exceptions:
  * Real Estate: VNQ is primary instead of XLRE. It has far larger AUM and volume
    and runs from 2004, while XLRE starts in Oct 2015.
  * Communication Services: XLC exists only from June 2018. Before that the
    fallbacks VOX/IYZ track the old, much narrower *Telecom Services* sector.
    This is a different exposure, which is disclosed in the README.

Survivorship bias: the list was chosen in 2026 with knowledge of which funds
survived and grew. Historical AUM and expense ratios are not available from free
sources, so they are NOT used as point-in-time filters. Only history length and
trailing dollar volume, which are computed from real prices, are point-in-time.
"""

SECTORS: dict[str, list[str]] = {
    "Technology":             ["XLK", "VGT", "IYW"],
    "Financials":             ["XLF", "VFH", "IYF"],
    "Energy":                 ["XLE", "VDE", "IYE"],
    "Health Care":            ["XLV", "VHT", "IYH"],
    "Industrials":            ["XLI", "VIS", "IYJ"],
    "Consumer Discretionary": ["XLY", "VCR", "IYC"],
    "Consumer Staples":       ["XLP", "VDC", "IYK"],
    "Utilities":              ["XLU", "VPU", "IDU"],
    "Materials":              ["XLB", "VAW", "IYM"],
    "Communication Services": ["XLC", "VOX", "IYZ"],
    "Real Estate":            ["VNQ", "XLRE", "IYR"],
}

BENCHMARK = "SPY"
RISK_FREE = "^IRX"  # 13-week T-bill yield, percent

# A-priori sector thresholds for the "sector" threshold mode. These are NOT fitted
# to the backtest. Defensive sectors get shallower thresholds because their
# historical drawdowns are smaller; high-beta sectors get deeper ones.
SECTOR_THRESHOLDS: dict[str, float] = {
    "Consumer Staples": 0.20, "Utilities": 0.20, "Health Care": 0.20,
    "Industrials": 0.30, "Materials": 0.30, "Financials": 0.30,
    "Consumer Discretionary": 0.30, "Communication Services": 0.30,
    "Real Estate": 0.30,
    "Technology": 0.35, "Energy": 0.35,
}


def all_etfs() -> list[str]:
    return [t for ts in SECTORS.values() for t in ts]


def all_tickers() -> list[str]:
    return all_etfs() + [BENCHMARK, RISK_FREE]


def sector_of(etf: str) -> str:
    for s, ts in SECTORS.items():
        if etf in ts:
            return s
    raise KeyError(etf)
