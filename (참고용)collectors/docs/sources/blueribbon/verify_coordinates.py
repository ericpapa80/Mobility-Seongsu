"""좌표 컬럼 검증 스크립트"""
import sys
import io

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import pandas as pd

df = pd.read_csv('restaurants_all.csv', nrows=10)

print("=== 좌표 컬럼 검증 ===\n")

# 좌표 관련 컬럼 찾기
coord_cols = [c for c in df.columns if 'lat' in c.lower() or 'lon' in c.lower() or 'gps' in c.lower()]
print("좌표 관련 컬럼:")
for col in coord_cols:
    print(f"  - {col}")

print("\n=== 좌표 값 검증 ===\n")
print("한국 좌표 범위:")
print("  위도(latitude): 33~38도 (남북)")
print("  경도(longitude): 124~132도 (동서)")

print("\nCSV 데이터 샘플 (상위 5개):")
for i in range(min(5, len(df))):
    lat = df['gps_latitude'].iloc[i]
    lng = df['gps_longitude'].iloc[i]
    name = df['headerInfo_nameKR'].iloc[i]
    
    print(f"\n{i+1}. {name}:")
    print(f"   gps_latitude:  {lat}")
    print(f"   gps_longitude: {lng}")
    
    # 값 범위 검증
    lat_valid = 33 <= lat <= 38
    lng_valid = 124 <= lng <= 132
    
    if lat_valid:
        print(f"   -> 위도 범위 정상 (33~38도)")
    else:
        print(f"   -> 위도 범위 이상! (33~38도 범위 밖)")
    
    if lng_valid:
        print(f"   -> 경도 범위 정상 (124~132도)")
    else:
        print(f"   -> 경도 범위 이상! (124~132도 범위 밖)")

print("\n=== 전체 데이터 범위 ===")
print(f"gps_latitude 범위:  {df['gps_latitude'].min():.2f} ~ {df['gps_latitude'].max():.2f}")
print(f"gps_longitude 범위: {df['gps_longitude'].min():.2f} ~ {df['gps_longitude'].max():.2f}")

