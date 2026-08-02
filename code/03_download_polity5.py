"""Download and process Polity5 democracy data.
Source: https://www.systemicpeace.org/inscrdata.html

Extracts polity2 score (-10 to +10) as primary democracy indicator.
"""

import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\经济增长因素")
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

POLITY_URL = "https://www.systemicpeace.org/inscr/p5v2018.xls"
POLITY_RAW = RAW_DIR / "p5v2018.xls"


def download_polity():
    """Download Polity5 Excel file."""
    import urllib.request
    if POLITY_RAW.exists():
        print(f"Polity5 file exists: {POLITY_RAW}")
        return
    print(f"Downloading Polity5: {POLITY_URL}")
    try:
        urllib.request.urlretrieve(POLITY_URL, POLITY_RAW)
        print(f"Downloaded: {POLITY_RAW}")
    except Exception as e:
        print(f"Download failed ({e})")
        print("Please manually download from https://www.systemicpeace.org/inscrdata.html")
        print(f"  Place at: {POLITY_RAW}")


def process_polity():
    """Extract polity2 and country codes."""
    print(f"Reading {POLITY_RAW} ...")
    df = pd.read_excel(POLITY_RAW)

    # Polity5 columns: scode, country, year, polity2, ...
    keep_cols = ["scode", "country", "year", "polity2"]
    available = [c for c in keep_cols if c in df.columns]

    if "polity2" not in df.columns:
        print(f"Available columns: {list(df.columns[:30])}")
        raise ValueError("polity2 column not found in Polity5 data")

    df = df[available].copy()

    # Map scode to iso3 using a simple lookup table
    # Polity uses Correlates of War country codes (ccode)
    # We will merge by country name later, but keep scode for now
    df = df.rename(columns={"scode": "ccode"})

    # Filter: polity2 = -66, -77, -88 are special codes (interregnum, etc.)
    df.loc[df["polity2"] < -10, "polity2"] = np.nan

    # Keep 1960 onwards
    df = df[df["year"] >= 1960]

    out_path = PROCESSED_DIR / "polity5_clean.csv"
    df.to_csv(out_path, index=False)
    print(f"Polity5 saved: {out_path}")
    print(f"  Countries: {df['country'].nunique()}")
    print(f"  Year range: {df['year'].min()}-{df['year'].max()}")
    return df


if __name__ == "__main__":
    download_polity()
    polity = process_polity()
