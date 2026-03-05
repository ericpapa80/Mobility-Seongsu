"""좌표 매핑 확인 스크립트"""
import sys
import io

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import json
import pandas as pd

# JSON 데이터 로드
with open('restaurants_all.json', 'r', encoding='utf-8') as f:
    json_data = json.load(f)

# CSV 데이터 로드
csv_df = pd.read_csv('restaurants_all.csv', nrows=10)

print("=== 좌표 매핑 확인 ===\n")

# 여러 레스토랑 확인
for i in range(min(5, len(json_data), len(csv_df))):
    json_lat = json_data[i]["gps"]["latitude"]
    json_lng = json_data[i]["gps"]["longitude"]
    csv_lat = csv_df["gps_latitude"].iloc[i]
    csv_lng = csv_df["gps_longitude"].iloc[i]
    
    print(f"레스토랑 {i+1} ({json_data[i]['headerInfo']['nameKR']}):")
    print(f"  JSON - latitude: {json_lat}, longitude: {json_lng}")
    print(f"  CSV  - gps_latitude: {csv_lat}, gps_longitude: {csv_lng}")
    
    # 매칭 확인
    lat_match = abs(float(json_lat) - float(csv_lat)) < 0.0001
    lng_match = abs(float(json_lng) - float(csv_lng)) < 0.0001
    
    if lat_match and lng_match:
        print("  [OK] 매칭 정상")
    else:
        print("  [ERROR] 매칭 오류!")
        if not lat_match:
            print(f"    latitude 불일치: JSON={json_lat}, CSV={csv_lat}")
        if not lng_match:
            print(f"    longitude 불일치: JSON={json_lng}, CSV={csv_lng}")
    print()

# 한국 좌표 범위 확인
print("\n=== 좌표 값 범위 확인 ===")
print("한국 좌표 범위:")
print("  위도(latitude): 33~38도 (남북)")
print("  경도(longitude): 124~132도 (동서)")
print("\nCSV 데이터 샘플:")
print(f"  gps_latitude 범위: {csv_df['gps_latitude'].min():.2f} ~ {csv_df['gps_latitude'].max():.2f}")
print(f"  gps_longitude 범위: {csv_df['gps_longitude'].min():.2f} ~ {csv_df['gps_longitude'].max():.2f}")

