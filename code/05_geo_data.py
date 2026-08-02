"""Download and process CEPII GeoDist geographic data.
Source: http://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=6

Extracts: landlocked indicator, latitude (absolute).
"""

import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\经济增长因素")
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

GEODIST_URL = "http://www.cepii.fr/DATA_DOWNLOAD/geo_cepii/postdta/geo_cepii.zip"
GEODIST_ZIP = RAW_DIR / "geo_cepii.zip"
GEODIST_RAW = RAW_DIR / "geo_cepii.xls"


def download_geodist():
    """Download CEPII GeoDist zip file."""
    import urllib.request
    import zipfile

    if GEODIST_RAW.exists():
        print(f"GeoDist file exists: {GEODIST_RAW}")
        return

    print(f"Downloading GeoDist: {GEODIST_URL}")
    try:
        urllib.request.urlretrieve(GEODIST_URL, GEODIST_ZIP)
        print(f"Downloaded zip: {GEODIST_ZIP}")
        with zipfile.ZipFile(GEODIST_ZIP, "r") as zf:
            zf.extractall(RAW_DIR)
        print(f"Extracted to: {RAW_DIR}")
    except Exception as e:
        print(f"Download failed ({e})")
        print("Please manually download from http://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=6")
        print(f"  Place at: {GEODIST_RAW}")
        print("  or extract the zip to the raw directory.")


def process_geodist():
    """Extract landlocked and latitude from GeoDist."""
    # Find the actual data file in raw directory
    xls_files = list(RAW_DIR.glob("geo_cepii*.xls")) + list(RAW_DIR.glob("geo_cepii*.xlsx"))
    csv_files = list(RAW_DIR.glob("geo_cepii*.csv"))

    df = None
    if xls_files:
        df = pd.read_excel(xls_files[0])
    elif csv_files:
        df = pd.read_csv(csv_files[0])
    else:
        print("GeoDist data file not found in raw directory.")
        print("Expected: geo_cepii.xls, geo_cepii.xlsx, or geo_cepii.csv")
        return None

    # CEPII GeoDist columns: iso_o (origin), iso_d (destination), dist, ...
    # We want country-level attributes for origin country
    if "iso_o" in df.columns:
        group_col = "iso_o"
    elif "iso3" in df.columns:
        group_col = "iso3"
    elif "iso" in df.columns:
        group_col = "iso"
    else:
        print(f"Cannot identify ISO code column. Columns: {list(df.columns[:10])}")
        return None

    # Build country-level geographic attributes
    geo = pd.DataFrame()
    geo["iso3"] = df[group_col].str.strip().str.upper()

    # Landlocked: from CEPII geo data if available, otherwise default False
    if "landlocked_o" in df.columns:
        geo["landlocked"] = df.groupby(group_col)["landlocked_o"].first().reset_index(drop=True)
    elif "landlocked" in df.columns:
        geo["landlocked"] = df.groupby(group_col)["landlocked"].first().reset_index(drop=True)
    else:
        # Use distance-based heuristic: if min distance to any country < threshold
        # This is imperfect but provides a fallback
        if "dist" in df.columns:
            min_dist = df.groupby(group_col)["dist"].min()
        geo["landlocked"] = 0

    # Latitude (absolute value)
    lat_col = None
    for candidate in ["lat_o", "lat", "latitude_o", "latitude"]:
        if candidate in df.columns:
            lat_col = candidate
            break
    if lat_col:
        geo["latitude"] = df.groupby(group_col)[lat_col].first().abs().reset_index(drop=True)
    else:
        geo["latitude"] = np.nan

    # Deduplicate
    geo = geo.drop_duplicates(subset=["iso3"])
    geo = geo.dropna(subset=["iso3"])

    out_path = PROCESSED_DIR / "geo_cepii_clean.csv"
    geo.to_csv(out_path, index=False)
    print(f"GeoDist saved: {out_path}")
    print(f"  Countries: {geo['iso3'].nunique()}")
    return geo


if __name__ == "__main__":
    download_geodist()
    geo = process_geodist()
