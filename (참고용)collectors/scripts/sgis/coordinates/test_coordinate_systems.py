"""다양한 좌표계로 변환 테스트"""

import json
from pathlib import Path

json_file = Path("data/raw/sgis/20251130_214212/sgis_technical_biz_20251130_214212.json")

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

items = data.get('result', [])
sample = items[0]
x = float(sample.get('x', 0))
y = float(sample.get('y', 0))
addr = sample.get('naddr', '')

print("=" * 80)
print("SGIS 좌표계 확인")
print("=" * 80)
print(f"샘플 주소: {addr}")
print(f"x: {x:.0f}")
print(f"y: {y:.0f}")

# 서울 중심 좌표 (WGS84)
seoul_lon = 127.0
seoul_lat = 37.5

print("\n" + "=" * 80)
print("다양한 좌표계로 서울 중심 좌표 변환 테스트:")
print("=" * 80)

try:
    from pyproj import Transformer
    
    # 테스트할 좌표계들
    test_crs = [
        ("EPSG:5174", "Korea 2000 / Central Belt 2010"),
        ("EPSG:5181", "Korea 2000 / Central Belt"),
        ("EPSG:5179", "Korea 2000 / Central Belt 2010"),
        ("EPSG:5186", "Korea 2000 / Central Belt 2010"),
        ("EPSG:3857", "WGS84 / Pseudo-Mercator"),
        ("EPSG:32652", "WGS84 / UTM zone 52N"),
        ("EPSG:2097", "Korea 2000 / East Belt 2010"),
    ]
    
    print(f"\n서울 중심 (경도 {seoul_lon}, 위도 {seoul_lat})을 각 좌표계로 변환:\n")
    
    for crs_code, crs_name in test_crs:
        try:
            transformer = Transformer.from_crs("EPSG:4326", crs_code, always_xy=True)
            x_test, y_test = transformer.transform(seoul_lon, seoul_lat)
            
            # 현재 데이터와 비교
            diff_x = abs(x_test - x)
            diff_y = abs(y_test - y)
            
            print(f"{crs_code} ({crs_name}):")
            print(f"  변환된 좌표: x={x_test:.0f}, y={y_test:.0f}")
            print(f"  현재 데이터: x={x:.0f}, y={y:.0f}")
            print(f"  차이: x={diff_x:.0f}, y={diff_y:.0f}")
            
            if diff_x < 10000 and diff_y < 10000:
                print(f"  → 가능성 있음! (차이가 작음)")
            print()
            
        except Exception as e:
            print(f"{crs_code}: 변환 실패 - {e}\n")
    
    # 역변환 테스트: 현재 좌표를 WGS84로 변환
    print("=" * 80)
    print("현재 좌표를 WGS84로 역변환 테스트:")
    print("=" * 80)
    
    for crs_code, crs_name in test_crs:
        try:
            transformer = Transformer.from_crs(crs_code, "EPSG:4326", always_xy=True)
            lon, lat = transformer.transform(x, y)
            
            print(f"\n{crs_code} ({crs_name}) → WGS84:")
            print(f"  경도: {lon:.6f}, 위도: {lat:.6f}")
            
            # 서울 지역인지 확인 (경도 126~127, 위도 37~38)
            if 126.0 <= lon <= 127.5 and 37.0 <= lat <= 38.0:
                print(f"  → ✅ 서울 지역 좌표! 이 좌표계일 가능성 높음!")
            else:
                print(f"  → ❌ 서울 지역이 아님 (서울: 경도 126~127, 위도 37~38)")
                
        except Exception as e:
            print(f"{crs_code}: 역변환 실패 - {e}")
    
except ImportError:
    print("\npyproj가 설치되지 않았습니다.")
    print("설치: pip install pyproj")
except Exception as e:
    print(f"\n오류 발생: {e}")

print("\n" + "=" * 80)
print("추가 정보:")
print("=" * 80)
print("SGIS API는 내부 좌표계를 사용할 수 있습니다.")
print("실제 지도에 표시하거나 API 문서를 확인하여 정확한 좌표계를 확인해야 합니다.")

