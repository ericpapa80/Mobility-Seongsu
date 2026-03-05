"""EPSG:5179 좌표를 EPSG:4326 (WGS84)로 변환하여 새 파일로 저장"""

import json
from pathlib import Path
from pyproj import Transformer

# 입력 파일
input_file = Path("data/raw/sgis/20251130_214212/sgis_technical_biz_20251130_214212.json")

# 출력 파일 (다른 이름으로 저장)
output_file = Path("data/raw/sgis/20251130_214212/sgis_technical_biz_20251130_214212_wgs84.json")

print("=" * 80)
print("좌표 변환: EPSG:5179 → EPSG:4326 (WGS84)")
print("=" * 80)

# 좌표 변환기 생성
transformer = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)

# JSON 파일 읽기
print(f"\n입력 파일 읽는 중: {input_file}")
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

items = data.get('result', [])
print(f"총 {len(items)}개 항목 처리 중...\n")

# 좌표 변환
converted_count = 0
error_count = 0

for item in items:
    try:
        x = float(item.get('x', 0))
        y = float(item.get('y', 0))
        
        if x > 0 and y > 0:
            # EPSG:5179 → EPSG:4326 변환
            lon, lat = transformer.transform(x, y)
            
            # 원본 좌표는 유지하고, 새로운 필드에 WGS84 좌표 추가
            item['x_5179'] = item.get('x')  # 원본 좌표 보존
            item['y_5179'] = item.get('y')  # 원본 좌표 보존
            item['x'] = f"{lon:.6f}"  # 경도 (longitude)
            item['y'] = f"{lat:.6f}"  # 위도 (latitude)
            item['lon'] = f"{lon:.6f}"  # 경도 별칭
            item['lat'] = f"{lat:.6f}"  # 위도 별칭
            
            converted_count += 1
        else:
            error_count += 1
            item['x_5179'] = item.get('x')
            item['y_5179'] = item.get('y')
            item['x'] = item.get('x')
            item['y'] = item.get('y')
            
    except Exception as e:
        error_count += 1
        print(f"오류 발생 (항목 {converted_count + error_count}): {e}")
        # 오류 발생 시 원본 좌표 유지
        item['x_5179'] = item.get('x')
        item['y_5179'] = item.get('y')

print(f"변환 완료: {converted_count}개 성공, {error_count}개 오류")

# 샘플 확인
if converted_count > 0:
    print("\n" + "=" * 80)
    print("변환된 샘플 (첫 5개):")
    print("=" * 80)
    for i, item in enumerate(items[:5]):
        print(f"{i+1}. {item.get('corp_nm', 'N/A')}")
        print(f"   주소: {item.get('naddr', 'N/A')}")
        print(f"   원본 (EPSG:5179): x={item.get('x_5179', 'N/A')}, y={item.get('y_5179', 'N/A')}")
        print(f"   변환 (EPSG:4326): 경도={item.get('lon', 'N/A')}, 위도={item.get('lat', 'N/A')}")
        print()

# 새 파일로 저장
print(f"\n출력 파일 저장 중: {output_file}")
output_file.parent.mkdir(parents=True, exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"저장 완료: {output_file}")
print(f"파일 크기: {output_file.stat().st_size / 1024 / 1024:.2f} MB")

# CSV도 변환된 버전으로 저장
csv_output_file = Path("data/raw/sgis/20251130_214212/sgis_technical_biz_20251130_214212_wgs84.csv")
print(f"\nCSV 파일도 저장 중: {csv_output_file}")

import csv
if items:
    fieldnames = list(items[0].keys())
    with open(csv_output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(items)
    
    print(f"CSV 저장 완료: {csv_output_file}")

print("\n" + "=" * 80)
print("변환 완료!")
print("=" * 80)
print(f"원본 파일: {input_file}")
print(f"변환된 파일: {output_file}")
print(f"변환된 CSV: {csv_output_file}")
print("\n변환된 파일에는 다음 필드가 포함됩니다:")
print("  - x, y: EPSG:4326 (WGS84) 좌표 (경도, 위도)")
print("  - lon, lat: 경도, 위도 별칭")
print("  - x_5179, y_5179: 원본 EPSG:5179 좌표 (보존)")

