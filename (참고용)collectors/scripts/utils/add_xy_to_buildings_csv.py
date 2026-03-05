"""CSV 파일의 center 컬럼을 x, y 컬럼으로 분리"""
import pandas as pd
import json
from pathlib import Path
import sys

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

csv_path = project_root / 'data/raw/openup/20251210_105005/openup_seongsu_buildings_20251210_105005.csv'

print(f"Reading CSV: {csv_path}")
df = pd.read_csv(csv_path, encoding='utf-8-sig')
print(f"Shape: {df.shape}")
print(f"Columns before: {list(df.columns)}")

def parse_center(s):
    """center 컬럼의 문자열을 파싱하여 [lng, lat] 튜플로 변환"""
    try:
        if pd.notna(s) and isinstance(s, str):
            coords = json.loads(s)
            if isinstance(coords, list) and len(coords) >= 2:
                return float(coords[0]), float(coords[1])
    except Exception as e:
        pass
    return None, None

print("Parsing center column...")
coords = df['center'].apply(parse_center)
df['x'] = coords.apply(lambda c: c[0] if c and c[0] is not None else None)
df['y'] = coords.apply(lambda c: c[1] if c and c[1] is not None else None)

# 컬럼 순서 조정: center 다음에 x, y 배치
cols = list(df.columns)
cols.remove('x')
cols.remove('y')
center_idx = cols.index('center')
cols.insert(center_idx + 1, 'x')
cols.insert(center_idx + 2, 'y')
df = df[cols]

print(f"Columns after: {list(df.columns)}")
print(f"x valid values: {df['x'].notna().sum()}/{len(df)}")
print(f"y valid values: {df['y'].notna().sum()}/{len(df)}")
print(f"Sample row 0 - x: {df['x'].iloc[0]}, y: {df['y'].iloc[0]}")

print(f"Saving to {csv_path}")
df.to_csv(csv_path, index=False, encoding='utf-8-sig')
print("Done!")
