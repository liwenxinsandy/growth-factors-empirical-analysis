"""Download and process WDI (World Development Indicators) data.
Source: World Bank Data API via wbdata library.
Indicators fetched:
- FP.CPI.TOTL.ZG (CPI inflation)
- SP.DYN.LE00.IN (life expectancy)
- SP.DYN.TFRT.IN (fertility rate)
- SP.URB.TOTL.IN.ZS (urban population %)
- GC.DOD.TOTL.GD.ZS (central govt debt % GDP)
- TX.VAL.FUEL.ZS.UN (fuel exports % merchandise exports)
"""

import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\经济增长因素")
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# WDI indicators
INDICATORS = {
    "FP.CPI.TOTL.ZG": "inflation_cpi",
    "SP.DYN.LE00.IN": "life_exp",
    "SP.DYN.TFRT.IN": "fertility",
    "SP.URB.TOTL.IN.ZS": "urban",
    "GC.DOD.TOTL.GD.ZS": "debt_gdp",
    "TX.VAL.FUEL.ZS.UN": "fuel_exports",
}


def fetch_wdi():
    """Fetch WDI indicators via wbdata API."""
    print("Fetching WDI data from World Bank API ...")
    try:
        import wbdata
    except ImportError:
        print("wbdata not installed. Install with: pip install wbdata")
        print("Falling back to cached data or manual download.")
        return None

    # Fetch all countries
    dfs = []
    for ind_code, ind_name in INDICATORS.items():
        print(f"  Fetching {ind_code} ({ind_name}) ...")
        try:
            data = wbdata.get_dataframe({ind_code: ind_name}, country="all")
            data = data.reset_index()
            data["indicator"] = ind_name
            dfs.append(data)
        except Exception as e:
            print(f"  Failed: {e}")
            continue

    if not dfs:
        print("No WDI data fetched.")
        return None

    wdi = pd.concat(dfs, ignore_index=True)
    raw_path = RAW_DIR / "wdi_raw.csv"
    wdi.to_csv(raw_path, index=False)
    print(f"Raw WDI saved: {raw_path}")
    return wdi


def process_wdi(wdi):
    """Process WDI data into clean panel."""
    if wdi is None:
        raw_path = RAW_DIR / "wdi_raw.csv"
        if not raw_path.exists():
            print("No WDI data available. Skipping.")
            return None
        wdi = pd.read_csv(raw_path)

    # Pivot indicators to columns
    id_cols = [c for c in wdi.columns if c not in ("indicator", "value")]
    pivot = wdi.pivot_table(
        index=id_cols,
        columns="indicator",
        values="value",
        aggfunc="first",
    ).reset_index()

    # Rename columns
    date_col = [c for c in pivot.columns if "date" in c.lower() or "year" in c.lower()]
    country_col = [c for c in pivot.columns if "country" in c.lower()]
    iso_col = [c for c in pivot.columns if "iso" in c.lower() or "code" in c.lower()]

    if date_col:
        pivot = pivot.rename(columns={date_col[0]: "year"})
    if country_col:
        pivot = pivot.rename(columns={country_col[0]: "country"})

    # Ensure year is numeric
    if "year" in pivot.columns:
        pivot["year"] = pd.to_numeric(pivot["year"], errors="coerce")
        pivot = pivot[pivot["year"] >= 1960]

    # Label oil exporters (fuel > 50% of merchandise exports)
    if "fuel_exports" in pivot.columns:
        pivot["oil_exporter"] = pivot["fuel_exports"] > 50
    else:
        pivot["oil_exporter"] = np.nan

    # Drop fuel_exports after flagging
    pivot = pivot.drop(columns=["fuel_exports"], errors="ignore")

    out_path = PROCESSED_DIR / "wdi_clean.csv"
    pivot.to_csv(out_path, index=False)
    print(f"WDI saved: {out_path}")
    return pivot


if __name__ == "__main__":
    wdi_raw = fetch_wdi()
    wdi_clean = process_wdi(wdi_raw)
