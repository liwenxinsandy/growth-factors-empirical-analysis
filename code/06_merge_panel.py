"""Merge all processed datasets into a unified 5-year panel.

Inputs (from data/processed/):
- pwt_5year.csv: PWT 5-year panel (core economic variables)
- barro_lee_clean.csv: education data (5-year intervals)
- polity5_clean.csv: democracy scores (annual)
- wdi_clean.csv: WDI indicators (annual)
- geo_cepii_clean.csv: geographic data (cross-section)

Outputs:
- data/processed/growth_panel.csv: final analysis panel
- data/processed/variable_coverage.csv: missing rate report
"""

import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\经济增长因素")
PROCESSED_DIR = ROOT / "data" / "processed"


def load_all():
    """Load all processed datasets."""
    datasets = {}

    pwt_path = PROCESSED_DIR / "pwt_5year.csv"
    if pwt_path.exists():
        datasets["pwt"] = pd.read_csv(pwt_path)
        print(f"Loaded PWT: {len(datasets['pwt'])} rows")

    bl_path = PROCESSED_DIR / "barro_lee_clean.csv"
    if bl_path.exists():
        datasets["barro_lee"] = pd.read_csv(bl_path)
        print(f"Loaded Barro-Lee: {len(datasets['barro_lee'])} rows")

    polity_path = PROCESSED_DIR / "polity5_clean.csv"
    if polity_path.exists():
        datasets["polity"] = pd.read_csv(polity_path)
        print(f"Loaded Polity5: {len(datasets['polity'])} rows")

    wdi_path = PROCESSED_DIR / "wdi_clean.csv"
    if wdi_path.exists():
        datasets["wdi"] = pd.read_csv(wdi_path)
        print(f"Loaded WDI: {len(datasets['wdi'])} rows")

    geo_path = PROCESSED_DIR / "geo_cepii_clean.csv"
    if geo_path.exists():
        datasets["geo"] = pd.read_csv(geo_path)
        print(f"Loaded GeoDist: {len(datasets['geo'])} rows")

    return datasets


def merge_education(panel, bl):
    """Merge Barro-Lee education data: match period start year."""
    if bl is None:
        return panel

    bl_renamed = bl.rename(columns={"year": "period", "school": "schooling"})
    bl_renamed = bl_renamed[["iso3", "period", "schooling"]]

    merged = panel.merge(bl_renamed, on=["iso3", "period"], how="left")
    print(f"  After Barro-Lee merge: {merged['schooling'].notna().sum()} obs with education")
    return merged


def merge_polity(panel, polity):
    """Merge Polity5: use period start year polity2 value."""
    if polity is None:
        return panel

    # Keep only period start years (1960, 1965, ..., 2015)
    polity_years = polity[polity["year"].isin(range(1960, 2020, 5))].copy()
    polity_years = polity_years.rename(columns={"year": "period"})

    # polity2 is the only variable we need; rename for clarity
    polity_years = polity_years[["country", "period", "polity2"]]

    # Merge on country name and period (polity doesnt have iso3)
    # We will do a two-step: first get iso3 mapping from panel
    iso_map = panel[["iso3", "country"]].drop_duplicates()

    # Try name-based merge via iso_map
    polity_with_iso = polity_years.merge(
        iso_map, on="country", how="left"
    )

    # Also try merging directly on period
    merged = panel.merge(
        polity_with_iso[["iso3", "period", "polity2"]],
        on=["iso3", "period"],
        how="left",
    )

    # Check if we got matches; if not, try merging by country+period
    if merged["polity2"].isna().all() or merged["polity2"].notna().sum() < 10:
        print("  Polity iso3 merge failed, trying country name merge ...")
        panel_plus = panel.merge(
            polity_years, on=["country", "period"], how="left"
        )
        merged["polity2"] = panel_plus["polity2"]

    print(f"  After Polity5 merge: {merged['polity2'].notna().sum()} obs with polity2")
    return merged


def merge_wdi(panel, wdi):
    """Merge WDI: 5-year average for each indicator."""
    if wdi is None:
        return panel

    wdi = wdi.copy()
    if "year" not in wdi.columns:
        return panel

    # Assign each WDI year to a 5-year period
    wdi["period"] = (wdi["year"] // 5) * 5

    # Identify indicator columns (exclude id/grouping columns)
    skip = {"country", "year", "period", "iso3", "iso", "code", "date"}
    ind_cols = [c for c in wdi.columns if c not in skip and wdi[c].dtype in ("float64", "int64")]

    if not ind_cols:
        print("  No WDI indicator columns found")
        return panel

    # 5-year average
    group_cols = [c for c in wdi.columns if c in ("iso3", "iso", "country")]
    group_cols = [c for c in group_cols if c in wdi.columns]
    if "iso3" not in group_cols:
        # Need iso3 for merge; try country name fallback
        wdi_avg = wdi.groupby(["country", "period"])[ind_cols].mean().reset_index()
        merged = panel.merge(wdi_avg, on=["country", "period"], how="left")
    else:
        wdi_avg = wdi.groupby(["iso3", "period"])[ind_cols].mean().reset_index()
        merged = panel.merge(wdi_avg, on=["iso3", "period"], how="left")

    n_matched = sum(merged[c].notna().sum() for c in ind_cols if c in merged.columns)
    print(f"  After WDI merge: {n_matched} indicator observations")
    return merged


def merge_geo(panel, geo):
    """Merge CEPII GeoDist cross-sectional data."""
    if geo is None:
        return panel

    geo = geo[["iso3", "landlocked", "latitude"]]
    merged = panel.merge(geo, on="iso3", how="left")
    print(f"  After GeoDist merge: {merged['landlocked'].notna().sum()} obs with geo data")
    return merged


def apply_filters(panel):
    """Apply sample filters."""
    n_before = len(panel)

    # Population threshold: >= 1 million (pop is in millions from PWT)
    if "pop" in panel.columns:
        panel = panel[panel["pop"] >= 1.0].copy()

    # Require at least 6 periods per country
    period_counts = panel.groupby("iso3")["period"].nunique()
    valid_countries = period_counts[period_counts >= 6].index
    panel = panel[panel["iso3"].isin(valid_countries)].copy()

    # Remove major oil exporters (optional flag)
    if "oil_exporter" in panel.columns:
        # Flag but dont remove; allow robustness checks later
        panel["oil_exporter"] = panel["oil_exporter"].fillna(False)

    n_after = len(panel)
    print(f"  Filtered: {n_before} -> {n_after} rows")
    print(f"  Countries after filter: {panel['iso3'].nunique()}")
    return panel


def report_coverage(panel):
    """Generate variable coverage report."""
    coverage = panel.notna().mean().sort_values(ascending=False)
    coverage = coverage[coverage.index != "iso3"]
    coverage = coverage[coverage.index != "country"]
    coverage = coverage[coverage.index != "period"]

    coverage_df = pd.DataFrame({
        "variable": coverage.index,
        "coverage_rate": coverage.values,
    })

    out_path = PROCESSED_DIR / "variable_coverage.csv"
    coverage_df.to_csv(out_path, index=False)
    print(f"\nCoverage report saved: {out_path}")
    print(coverage_df.to_string(index=False))


def main():
    datasets = load_all()

    if "pwt" not in datasets:
        print("ERROR: PWT 5-year panel is required. Run 01_download_pwt.py first.")
        return

    panel = datasets["pwt"]

    print("\nMerging datasets...")
    panel = merge_education(panel, datasets.get("barro_lee"))
    panel = merge_polity(panel, datasets.get("polity"))
    panel = merge_wdi(panel, datasets.get("wdi"))
    panel = merge_geo(panel, datasets.get("geo"))

    print("\nApplying sample filters...")
    panel = apply_filters(panel)

    # Final output
    out_csv = PROCESSED_DIR / "growth_panel.csv"
    panel.to_csv(out_csv, index=False)
    print(f"\nFinal panel saved: {out_csv}")
    print(f"  Shape: {panel.shape}")
    print(f"  Countries: {panel['iso3'].nunique()}")
    print(f"  Periods: {sorted(panel['period'].unique())}")

    # Also save Stata format if pyreadstat available
    try:
        out_dta = PROCESSED_DIR / "growth_panel.dta"
        panel.to_stata(out_dta, write_index=False)
        print(f"  Stata: {out_dta}")
    except Exception:
        pass

    report_coverage(panel)


if __name__ == "__main__":
    main()
