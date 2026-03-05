"""CSV 파일의 center 컬럼을 x, y 컬럼으로 분리"""
import pandas as pd
from pathlib import Path
import json

csv_path = Path('data/raw/openup/20251210_105005/openup_seongsu_buildings_20251210_105005.csv')

print(f"Reading CSV: {csv_path}")
df = pd.read_csv(csv_path, encoding='utf-8-sig')
print(f"Total rows: {len(df)}")
print(f"Columns: {list(df.columns)}")

def parse_coords(s):
    if pd.isna(s) or not s:
        return None, None
    try:
        if isinstance(s, str):
            coords = json.loads(s)
        else:
            coords = s
        if isinstance(coords, list) and len(coords) >= 2:
            return float(coords[0]), float(coords[1])
    except:
        pass
    return None, None

print("Parsing center coordinates...")
coords = df['center'].apply(parse_coords)
df['x'] = coords.apply(lambda x: x[0])
df['y'] = coords.apply(lambda x: x[1])

# 컬럼 순서 조정: center 다음에 x, y 배치
cols = list(df.columns)
cols.remove('x')
cols.remove('y')
center_idx = cols.index('center')
cols.insert(center_idx + 1, 'x')
cols.insert(center_idx + 2, 'y')
df = df[cols]

print(f"New columns: {list(df.columns)}")
print(f"x valid values: {df['x'].notna().sum()}")
print(f"y valid values: {df['y'].notna().sum()}")

print(f"Saving to {csv_path}")
df.to_csv(csv_path, index=False, encoding='utf-8-sig')
print("Done!")
