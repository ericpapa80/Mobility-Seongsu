"""성동구 수집 데이터 확인."""

import pandas as pd
from pathlib import Path

# 최신 성동구 데이터 파일 찾기
csv_file = list(Path('data/raw/sbiz').glob('**/sbiz_stores_dong_성동구*.csv'))[-1]

print(f"파일: {csv_file}")
print("=" * 60)

df = pd.read_csv(csv_file)

print(f"총 업소 수: {len(df):,}개")
print(f"컬럼 수: {len(df.columns)}개")
print(f"\n행정동별 업소 수:")
dong_counts = df['adongNm'].value_counts().sort_index()
print(dong_counts)

print(f"\n성수동 관련 업소:")
seongsu_dongs = ['성수1가2동', '성수2가3동', '성수1동', '성수2가동']
for dong in seongsu_dongs:
    count = len(df[df['adongNm'] == dong])
    if count > 0:
        print(f"  {dong}: {count:,}개")

print(f"\n좌표 데이터 확인 (첫 5개):")
print(df[['bizesNm', 'adongNm', 'lon', 'lat']].head())

print(f"\n좌표 데이터 유효성:")
print(f"  경도(lon) null: {df['lon'].isna().sum()}개")
print(f"  위도(lat) null: {df['lat'].isna().sum()}개")

