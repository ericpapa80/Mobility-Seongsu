# -*- coding: utf-8 -*-
"""성수동 지역 외 좌표 레코드 확인 스크립트"""

import sys
import pandas as pd
from pathlib import Path

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 성수동 지역 좌표 범위
SEONGSU_X_MIN, SEONGSU_X_MAX = 127.04, 127.07
SEONGSU_Y_MIN, SEONGSU_Y_MAX = 37.54, 37.55

csv_path = Path('data/raw/nps/nps_20251222_162853/nps_20251222_162853_ultimate.csv')
df = pd.read_csv(csv_path, encoding='utf-8-sig')

coords_df = df[df['x'].notna() & df['y'].notna()]
outside = coords_df[
    ~((coords_df['x'] >= SEONGSU_X_MIN) & (coords_df['x'] <= SEONGSU_X_MAX) &
      (coords_df['y'] >= SEONGSU_Y_MIN) & (coords_df['y'] <= SEONGSU_Y_MAX))
]

print(f'성수동 지역 외: {len(outside)}개')
print('\n샘플 10개 (상호명, 주소, 좌표):')
print('=' * 100)
for idx, row in outside.head(10).iterrows():
    business = str(row['사업장명']) if pd.notna(row['사업장명']) else 'N/A'
    address = str(row['주소']) if pd.notna(row['주소']) else 'N/A'
    jibun = str(row['사업장지번상세주소']) if pd.notna(row['사업장지번상세주소']) else 'N/A'
    x = row['x']
    y = row['y']
    print(f"{business} | {address} | {jibun} | ({x:.6f}, {y:.6f})")

print('\n\n좌표 분포:')
print(f'X 범위: {outside["x"].min():.6f} ~ {outside["x"].max():.6f}')
print(f'Y 범위: {outside["y"].min():.6f} ~ {outside["y"].max():.6f}')
print(f'성수동 X 범위: {SEONGSU_X_MIN} ~ {SEONGSU_X_MAX}')
print(f'성수동 Y 범위: {SEONGSU_Y_MIN} ~ {SEONGSU_Y_MAX}')

