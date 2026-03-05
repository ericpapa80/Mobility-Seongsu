"""추출된 성수동 데이터 확인."""

import pandas as pd
from pathlib import Path

# 추출된 성수동 데이터 파일
csv_file = list(Path('data/raw/sbiz').glob('**/sbiz_stores_seongsu*.csv'))[-1]

print("=" * 60)
print("추출된 성수동 데이터 요약")
print("=" * 60)

df = pd.read_csv(csv_file)

print(f"\n총 업소 수: {len(df):,}개")
print(f"컬럼 수: {len(df.columns)}개")

print(f"\n행정동별 분포:")
dong_counts = df['adongNm'].value_counts().sort_index()
for dong, count in dong_counts.items():
    print(f"  {dong}: {count:,}개")

print(f"\n업종 대분류 Top 10:")
inds_counts = df['indsLclsNm'].value_counts().head(10)
for inds, count in inds_counts.items():
    print(f"  {inds}: {count:,}개")

print(f"\n좌표 범위:")
print(f"  경도(lon): {df['lon'].min():.6f} ~ {df['lon'].max():.6f}")
print(f"  위도(lat): {df['lat'].min():.6f} ~ {df['lat'].max():.6f}")

print(f"\n좌표 데이터 유효성:")
print(f"  경도 null: {df['lon'].isna().sum()}개")
print(f"  위도 null: {df['lat'].isna().sum()}개")

print(f"\n파일 위치: {csv_file}")

