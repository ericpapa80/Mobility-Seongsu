"""연도별 비교 결과 확인 스크립트."""

import pandas as pd
from pathlib import Path

csv_path = Path('data/raw/sbiz/sbiz_stores_seongsu_extracted_20251202_153918/sbiz_stores_seongsu_20251202_153918_with_yearly.csv')

df = pd.read_csv(csv_path, encoding='utf-8-sig', nrows=20)

print('샘플 데이터 (개업/폐업/변경없음):')
print(df[['bizesId', 'bizesNm', '2022년_존재', '2023년_존재', '2024년_존재', '2025년_존재', '개업연도', '폐업연도', '변경없음', '존재연도']].to_string())

print('\n통계:')
print(f'변경없음(O): {df["변경없음"].notna().sum()}개')
print(f'개업연도 있음: {df[df["개업연도"] != ""].shape[0]}개')
print(f'폐업연도 있음: {df[df["폐업연도"] != ""].shape[0]}개')

# 전체 데이터 통계
df_full = pd.read_csv(csv_path, encoding='utf-8-sig')
print(f'\n전체 데이터 통계:')
print(f'  총 업소 수: {len(df_full):,}개')
print(f'  변경없음(O): {df_full["변경없음"].notna().sum():,}개')
print(f'  개업연도 있음: {df_full[df_full["개업연도"] != ""].shape[0]:,}개')
print(f'  폐업연도 있음: {df_full[df_full["폐업연도"] != ""].shape[0]:,}개')

