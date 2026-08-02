import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(r'C:\Users\Lenovo\Documents\经济增长因素')
RAW_DIR = ROOT / 'data' / 'raw'
PROCESSED_DIR = ROOT / 'data' / 'processed'
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

BL_URL = 'http://www.barrolee.com/data/BL_v3.0/BL2013_MF2599_v3.0.xlsx'
BL_RAW = RAW_DIR / 'BL_v3.0.xlsx'
BL_CSV_URL = 'http://www.barrolee.com/data/BL_v3.0/BL2013_MF2599_v3.0.csv'
BL_CSV_RAW = RAW_DIR / 'BL_v3.0.csv'

def download_barro_lee():
    import urllib.request
    if BL_RAW.exists():
        print(f'Barro-Lee file exists: {BL_RAW}')
        return 'xlsx'
    if BL_CSV_RAW.exists():
        print(f'Barro-Lee CSV exists: {BL_CSV_RAW}')
        return 'csv'
    print(f'Downloading Barro-Lee (Excel): {BL_URL}')
    try:
        urllib.request.urlretrieve(BL_URL, BL_RAW)
        print(f'Downloaded: {BL_RAW}')
        return 'xlsx'
    except Exception as e:
        print(f'Excel download failed ({e}), trying CSV...')
        try:
            urllib.request.urlretrieve(BL_CSV_URL, BL_CSV_RAW)
            print(f'Downloaded: {BL_CSV_RAW}')
            return 'csv'
        except Exception as e2:
            print(f'CSV download failed ({e2})')
            print('Please manually download from http://www.barrolee.com/')
            print(f'  Excel: {BL_RAW}')
            print(f'  CSV:   {BL_CSV_RAW}')
            return None

def process_barro_lee(fmt):
    if fmt == 'xlsx':
        df = pd.read_excel(BL_RAW)
    elif fmt == 'csv':
        df = pd.read_csv(BL_CSV_RAW)
    else:
        raise FileNotFoundError('Barro-Lee data not found')
    id_cols = [c for c in df.columns if 'country' in c.lower() or 'code' in c.lower() or c.lower() == 'iso3']
    edu_cols = [c for c in df.columns if 'yr_sch' in c.lower() and 'MF' in c]
    if not edu_cols:
        edu_cols = [c for c in df.columns if 'yr_sch' in c.lower()]
    if not id_cols or not edu_cols:
        print('Auto-detect failed; trying manual mapping...')
        print(f'Available columns: {list(df.columns[:20])}')
        code_col = [c for c in df.columns if 'blcode' in c.lower() or 'wbcode' in c.lower()]
        if not code_col:
            code_col = [c for c in df.columns if c.lower() in ('code', 'iso', 'iso3')]
        name_col = [c for c in df.columns if c.lower() in ('country', 'countryname')]
        id_cols = code_col + name_col if code_col else df.columns[:2].tolist()
        edu_cols = [c for c in df.columns if any(str(y) in c for y in range(1950, 2050))]
        edu_cols = [c for c in edu_cols if 'yr_sch' in c.lower() or 'sch' in c.lower()]
    if not edu_cols:
        raise ValueError('Cannot extract education columns from Barro-Lee data')
    id_df = df[id_cols].copy()
    id_df.columns = ['iso3', 'country']
    long_rows = []
    for col in edu_cols:
        year_str = ''.join(c for c in col if c.isdigit())
        if not year_str:
            continue
        year = int(year_str)
        temp = id_df.copy()
        temp['year'] = year
        temp['school'] = df[col]
        long_rows.append(temp)
    result = pd.concat(long_rows, ignore_index=True)
    result = result.dropna(subset=['school'])
    result = result[result['year'].isin(range(1960, 2020, 5))]
    result['iso3'] = result['iso3'].str.strip().str.upper()
    out_path = PROCESSED_DIR / 'barro_lee_clean.csv'
    result.to_csv(out_path, index=False)
    print(f'Barro-Lee saved: {out_path}')
    print(f'  Countries: {result[\"iso3\"].nunique()}')
    print(f'  Years: {sorted(result[\"year\"].unique())}')
    return result

if __name__ == '__main__':
    fmt = download_barro_lee()
    if fmt:
        bl_data = process_barro_lee(fmt)
