"""Generate summary statistics for the final growth panel.

Outputs:
- output/tables/summary_stats.csv: descriptive statistics table
- Prints key diagnostics to console.
"""

import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\经济增长因素")
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "output" / "tables"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_panel():
    panel_path = PROCESSED_DIR / "growth_panel.csv"
    if not panel_path.exists():
        print(f"Panel not found: {panel_path}")
        print("Run 06_merge_panel.py first.")
        return None
    df = pd.read_csv(panel_path)
    print(f"Loaded panel: {df.shape[0]} rows, {df['iso3'].nunique()} countries")
    return df


def compute_summary(df):
    """Compute descriptive statistics for key variables."""
    vars_to_report = [
        "growth", "ln_rgdpe_initial", "csh_i", "pop_growth",
        "trade_open", "csh_g", "schooling", "polity2",
        "inflation_cpi", "debt_gdp", "life_exp", "urban",
        "fertility", "landlocked", "latitude",
    ]

    available = [v for v in vars_to_report if v in df.columns]

    stats_list = []
    for var in available:
        series = df[var].dropna()
        stats_list.append({
            "variable": var,
            "n": len(series),
            "mean": series.mean(),
            "std": series.std(),
            "min": series.min(),
            "p25": series.quantile(0.25),
            "p50": series.quantile(0.50),
            "p75": series.quantile(0.75),
            "max": series.max(),
        })

    stats_df = pd.DataFrame(stats_list)
    out_path = OUTPUT_DIR / "summary_stats.csv"
    stats_df.to_csv(out_path, index=False)
    print(f"\nSummary stats saved: {out_path}")

    # Pretty-print
    pd.set_option("display.float_format", "{:.3f}".format)
    pd.set_option("display.max_columns", 10)
    pd.set_option("display.width", 120)
    print("\n" + "=" * 80)
    print("DESCRIPTIVE STATISTICS")
    print("=" * 80)
    print(stats_df.to_string(index=False))

    return stats_df


def panel_balance(df):
    """Report panel balance."""
    print("\n" + "=" * 80)
    print("PANEL BALANCE")
    print("=" * 80)

    period_counts = df.groupby("iso3")["period"].nunique()
    print(f"\nPeriods per country:")
    print(f"  Mean:   {period_counts.mean():.1f}")
    print(f"  Median: {period_counts.median():.0f}")
    print(f"  Min:    {period_counts.min()}")
    print(f"  Max:    {period_counts.max()}")

    # Distribution
    dist = period_counts.value_counts().sort_index()
    print(f"\n  Distribution:")
    for n_periods, n_countries in dist.items():
        print(f"    {n_periods} periods: {n_countries} countries")

    # Country count by period
    period_n = df.groupby("period")["iso3"].nunique()
    print(f"\nCountries per period:")
    for period, count in period_n.items():
        print(f"  {period}: {count}")


def missingness(df):
    """Report missing rate for each variable."""
    print("\n" + "=" * 80)
    print("MISSING RATES")
    print("=" * 80)

    skip = {"iso3", "country", "period", "n_years"}
    vars_list = [c for c in df.columns if c not in skip]
    missing = df[vars_list].isna().mean().sort_values(ascending=False)
    missing = missing[missing > 0]

    if missing.empty:
        print("  No missing values!")
    else:
        for var, rate in missing.items():
            print(f"  {var}: {rate:.1%}")


def correlations(df):
    """Correlation matrix of key variables."""
    print("\n" + "=" * 80)
    print("CORRELATIONS WITH GROWTH")
    print("=" * 80)

    if "growth" not in df.columns:
        return

    skip = {"iso3", "country", "period", "n_years", "growth"}
    vars_list = [c for c in df.columns if c not in skip and df[c].dtype in ("float64", "int64")]

    corr = df[["growth"] + vars_list].corr()["growth"].drop("growth").sort_values(key=abs, ascending=False)
    for var, r in corr.items():
        print(f"  {var}: {r:+.4f}")


def main():
    df = load_panel()
    if df is None:
        return

    compute_summary(df)
    panel_balance(df)
    missingness(df)
    correlations(df)

    print("\n" + "=" * 80)
    print("Done. See output/tables/ for saved results.")
    print("=" * 80)


if __name__ == "__main__":
    main()
