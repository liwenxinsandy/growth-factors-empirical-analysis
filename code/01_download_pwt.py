"""Download and process Penn World Table 10.01 data.
Source: https://www.rug.nl/ggdc/productivity/pwt/

Key variables extracted:
- rgdpe (expenditure-side real GDP, mil 2017 USD)
- pop (population, millions)
- csh_i (capital formation share of GDP)
- csh_g (government consumption share of GDP)
- csh_x / csh_m (exports / imports share of GDP)
- hc (human capital index)
- ctfp / rtfPna (TFP level, US=1 / cross-country comparable)

Output: data/processed/pwt_yearly.csv, data/processed/pwt_5year.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\经济增长因素")
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

PWT_URL = "https://www.rug.nl/ggdc/docs/pwt1001.xlsx"
PWT_RAW = RAW_DIR / "pwt1001.xlsx"


def download_pwt():
    """Download PWT 10.01 raw file."""
    import urllib.request
    if PWT_RAW.exists():
        print(f"PWT file exists: {PWT_RAW}")
        return
    print(f"Downloading PWT 10.01 from {PWT_URL} ...")
    try:
        urllib.request.urlretrieve(PWT_URL, PWT_RAW)
        print(f"Downloaded: {PWT_RAW}")
    except Exception as e:
        print(f"Auto-download failed ({e})")
        print("Please manually download pwt1001.xlsx from:")
        print("  https://www.rug.nl/ggdc/productivity/pwt/")
        print(f"  Place at: {PWT_RAW}")


def process_pwt():
    """Extract core variables from PWT and save yearly panel."""
    print(f"Reading {PWT_RAW} ...")
    df = pd.read_excel(PWT_RAW, sheet_name="Data")

    cols = {
        "countrycode": "iso3",
        "country": "country",
        "year": "year",
        "rgdpe": "rgdpe",
        "rgdpo": "rgdpo",
        "pop": "pop",
        "emp": "emp",
        "avh": "avh",
        "hc": "hc",
        "csh_i": "csh_i",
        "csh_g": "csh_g",
        "csh_x": "csh_x",
        "csh_m": "csh_m",
        "ctfp": "ctfp",
        "rtfpna": "rtfpna",
    }

    available = [k for k in cols if k in df.columns]
    df = df[available].rename(columns={k: v for k, v in cols.items() if k in available})

    # Derived variables
    df["rgdpe_per_capita"] = df["rgdpe"] / df["pop"]
    df["trade_open"] = df["csh_x"] + df["csh_m"]

    # Save yearly
    yearly_path = PROCESSED_DIR / "pwt_yearly.csv"
    df.to_csv(yearly_path, index=False)
    print(f"Yearly panel saved: {yearly_path}")
    print(f"  Countries: {df['iso3'].nunique()}")
    print(f"  Year range: {df['year'].min()}-{df['year'].max()}")
    return df


def build_five_year_panel(df):
    """Aggregate yearly data into 5-year non-overlapping panel."""
    periods = [(y, y + 4) for y in range(1960, 2020, 5)]
    rows = []

    for start, end in periods:
        period_mask = (df["year"] >= start) & (df["year"] <= end)
        period_df = df[period_mask].copy()

        if period_df.empty:
            continue

        # 5-year averages
        avg = period_df.groupby("iso3").agg(
            country=("country", "first"),
            rgdpe=("rgdpe", "mean"),
            pop=("pop", "mean"),
            rgdpe_per_capita=("rgdpe_per_capita", "mean"),
            csh_i=("csh_i", "mean"),
            csh_g=("csh_g", "mean"),
            trade_open=("trade_open", "mean"),
            hc=("hc", "mean"),
            ctfp=("ctfp", "mean"),
            rtfpna=("rtfpna", "mean"),
            n_years=("year", "count"),
        ).reset_index()

        # Initial values (first year of the period)
        initial = period_df[period_df["year"] == start]
        if initial.empty:
            initial = period_df[period_df["year"] == period_df["year"].min()]
        initial = initial.groupby("iso3").agg(
            rgdpe_pc_initial=("rgdpe_per_capita", "first"),
            hc_initial=("hc", "first"),
            pop_initial=("pop", "first"),
        ).reset_index()

        # Final values (last year of the period)
        final = period_df[period_df["year"] == end]
        if final.empty:
            final = period_df[period_df["year"] == period_df["year"].max()]
        final = final.groupby("iso3").agg(
            rgdpe_pc_final=("rgdpe_per_capita", "last"),
        ).reset_index()

        merged = avg.merge(initial, on="iso3", how="left")
        merged = merged.merge(final, on="iso3", how="left")

        # Log initial GDP per capita
        merged["ln_rgdpe_initial"] = np.log(
            merged["rgdpe_pc_initial"].clip(lower=1e-6)
        )

        # Population growth rate (annualized)
        merged["pop_growth"] = (
            (np.log(merged["pop_initial"].clip(lower=1e-6)))
            .sub(np.log(merged["pop_initial"].clip(lower=1e-6)))
            * 0  # placeholder: will compute per-country
        )

        # Compute actual population growth per country
        for iso in merged["iso3"].unique():
            country_years = period_df[period_df["iso3"] == iso]
            if len(country_years) >= 2:
                pop_start = country_years["pop"].iloc[0]
                pop_end = country_years["pop"].iloc[-1]
                if pop_start > 0 and pop_end > 0:
                    yrs = max(country_years["year"].max() - country_years["year"].min(), 1)
                    g = (np.log(pop_end) - np.log(pop_start)) / yrs
                    merged.loc[merged["iso3"] == iso, "pop_growth"] = g

        # Per capita GDP growth rate (annualized %)
        merged["growth"] = np.where(
            (merged["rgdpe_pc_initial"] > 0) & (merged["rgdpe_pc_final"] > 0),
            (np.log(merged["rgdpe_pc_final"]) - np.log(merged["rgdpe_pc_initial"]))
            / (end - start + 1) * 100,
            np.nan,
        )

        merged["period"] = start
        rows.append(merged)

    panel = pd.concat(rows, ignore_index=True)

    # Order columns
    col_order = [
        "iso3", "country", "period", "n_years",
        "growth", "ln_rgdpe_initial",
        "csh_i", "pop_growth", "trade_open", "csh_g",
        "hc", "hc_initial", "ctfp", "rtfpna",
        "rgdpe", "pop", "rgdpe_per_capita",
    ]
    panel = panel[[c for c in col_order if c in panel.columns]]

    panel_path = PROCESSED_DIR / "pwt_5year.csv"
    panel.to_csv(panel_path, index=False)
    print(f"5-year panel saved: {panel_path}")
    print(f"  Countries: {panel['iso3'].nunique()}")
    print(f"  Periods: {panel['period'].nunique()}")
    return panel


if __name__ == "__main__":
    download_pwt()
    yearly = process_pwt()
    panel = build_five_year_panel(yearly)
