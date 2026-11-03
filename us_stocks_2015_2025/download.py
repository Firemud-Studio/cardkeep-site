"""Download daily OHLCV history (2015-01-01 .. 2025-12-31) for the 300 largest
US-listed US companies by current market cap, one CSV per stock.

Usage: python download.py <sp500_wikipedia_html> [out_dir]
Source: Yahoo Finance via yfinance.
"""
import sys, time, concurrent.futures as cf
from pathlib import Path
import pandas as pd
import yfinance as yf

START, END = "2015-01-01", "2026-01-01"  # END is exclusive -> through 2025-12-31
TOP_N = 300

# Large US companies that are not (or were not recently) in the S&P 500.
# Duplicates with the S&P list are harmless; ranking decides who makes the cut.
SUPPLEMENT = """MRVL SNOW MSTR TEAM ZS NET CRWV MDB HUBS RDDT SOFI CPNG ROKU DKNG ALAB
COHR CIEN LITE SCCO CQP ET EPD MPLX ALNY NTRA INSM VEEV AFRM TOST RBLX HOOD APP
COIN ARES CVNA APO KKR IBKR SATS RKLB FIX CRCL FIG CW BAH MKL TKO WMG FLUT ROIV
CSL WSO UTHR ILMN PSTG NTNX OKTA DOCU TWLO GDDY CHWY LPLA EWBC FNF RGA SSNC
ACM EQH CASY THC USFD PFGC BURL DT GWRE MANH TXRH WING ELF CELH RIVN LCID""".split()

NAMES = {"MRVL": "Marvell Technology", "SNOW": "Snowflake", "MSTR": "Strategy", "TEAM": "Atlassian",
         "ZS": "Zscaler", "NET": "Cloudflare", "CRWV": "CoreWeave", "MDB": "MongoDB", "HUBS": "HubSpot",
         "RDDT": "Reddit", "SOFI": "SoFi Technologies", "CPNG": "Coupang", "ROKU": "Roku",
         "DKNG": "DraftKings", "ALAB": "Astera Labs", "COHR": "Coherent", "CIEN": "Ciena",
         "LITE": "Lumentum", "SCCO": "Southern Copper", "CQP": "Cheniere Energy Partners",
         "ET": "Energy Transfer", "EPD": "Enterprise Products Partners", "MPLX": "MPLX",
         "ALNY": "Alnylam Pharmaceuticals", "NTRA": "Natera", "INSM": "Insmed", "VEEV": "Veeva Systems",
         "AFRM": "Affirm", "TOST": "Toast", "RBLX": "Roblox", "ARES": "Ares Management",
         "SATS": "EchoStar", "RKLB": "Rocket Lab", "FIX": "Comfort Systems USA", "CRCL": "Circle Internet",
         "FIG": "Figma", "CW": "Curtiss-Wright", "BAH": "Booz Allen Hamilton", "MKL": "Markel",
         "TKO": "TKO Group", "WMG": "Warner Music Group", "FLUT": "Flutter Entertainment",
         "ROIV": "Roivant Sciences", "CSL": "Carlisle", "WSO": "Watsco", "UTHR": "United Therapeutics",
         "ILMN": "Illumina", "NTNX": "Nutanix", "OKTA": "Okta", "DOCU": "DocuSign", "TWLO": "Twilio",
         "GDDY": "GoDaddy", "CHWY": "Chewy", "LPLA": "LPL Financial", "EWBC": "East West Bancorp",
         "FNF": "Fidelity National Financial", "RGA": "Reinsurance Group of America", "SSNC": "SS&C",
         "ACM": "AECOM", "EQH": "Equitable Holdings", "CASY": "Casey's", "THC": "Tenet Healthcare",
         "USFD": "US Foods", "PFGC": "Performance Food Group", "BURL": "Burlington Stores",
         "DT": "Dynatrace", "GWRE": "Guidewire", "MANH": "Manhattan Associates", "TXRH": "Texas Roadhouse",
         "WING": "Wingstop", "ELF": "e.l.f. Beauty", "CELH": "Celsius", "RIVN": "Rivian", "LCID": "Lucid"}

# Keep one share class per company.
DROP = {"GOOG", "FOX", "NWS"}


def universe(sp500_html):
    sp = pd.read_html(sp500_html)[0]
    names = dict(zip(sp.Symbol.str.replace(".", "-", regex=False), sp.Security))
    tickers = sorted((set(names) | set(SUPPLEMENT)) - DROP)
    return tickers, names


def market_cap(t):
    for attempt in range(3):
        try:
            return t, float(yf.Ticker(t).fast_info.market_cap)
        except Exception:
            time.sleep(2 * (attempt + 1))
    return t, None


def fetch(t, out):
    for attempt in range(4):
        try:
            df = yf.Ticker(t).history(start=START, end=END, auto_adjust=False, actions=True)
            if df.empty:
                raise ValueError("empty")
            df.index = df.index.tz_localize(None).date
            df.index.name = "Date"
            df = df.rename(columns={"Stock Splits": "Stock Split"})
            cols = ["Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Split"]
            df[[c for c in cols if c in df.columns]].to_csv(out / f"{t}.csv", float_format="%.6f")
            return t, len(df), str(df.index[0]), str(df.index[-1])
        except Exception as e:
            err = e
            time.sleep(2 ** (attempt + 1))
    return t, 0, None, repr(err)


def main():
    html = sys.argv[1]
    out = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).parent / "data")
    out.mkdir(parents=True, exist_ok=True)
    tickers, names = universe(html)
    print(f"universe: {len(tickers)} tickers")
    with cf.ThreadPoolExecutor(8) as ex:
        caps = dict(ex.map(market_cap, tickers))
    missing = [t for t, c in caps.items() if not c]
    print("no market cap:", missing)
    ranked = sorted(((c, t) for t, c in caps.items() if c), reverse=True)
    # Download in rank order; skip tickers with no 2015-2025 history (e.g. 2026
    # spin-offs, delisted names) and backfill with the next largest until TOP_N.
    res, kept, i = {}, [], 0
    with cf.ThreadPoolExecutor(6) as ex:
        while len(kept) < TOP_N and i < len(ranked):
            batch = [t for _, t in ranked[i:i + TOP_N - len(kept)]]
            i += len(batch)
            for r in ex.map(lambda t: fetch(t, out), batch):
                res[r[0]] = r
            kept = [t for _, t in ranked[:i] if res[t][1]][:TOP_N]
    skipped = [(t, res[t][3]) for _, t in ranked[:i] if not res[t][1]]
    print("skipped (no data in range):", skipped)
    caps_bn = {t: round(c / 1e9, 2) for c, t in ranked}
    top = pd.DataFrame(
        [(n + 1, t, names.get(t) or NAMES.get(t, ""), caps_bn[t]) for n, t in enumerate(kept)],
        columns=["Rank", "Ticker", "Name", "MarketCap_USD_bn"],
    )
    top["Rows"] = top.Ticker.map(lambda t: res[t][1])
    top["FirstDate"] = top.Ticker.map(lambda t: res[t][2])
    top["LastDate"] = top.Ticker.map(lambda t: res[t][3])
    top.to_csv(out.parent / "tickers.csv", index=False)
    print(top.to_string(index=False))


if __name__ == "__main__":
    main()
