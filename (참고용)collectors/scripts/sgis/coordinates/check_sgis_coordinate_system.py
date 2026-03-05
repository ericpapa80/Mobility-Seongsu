"""SGIS 좌표계 확인 및 변환 테스트"""

import json
from pathlib import Path

json_file = Path("data/raw/sgis/20251130_214212/sgis_technical_biz_20251130_214212.json")

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

items = data.get('result', [])
print(f"총 {len(items)}개 항목\n")

# 샘플 좌표 추출
sample = items[0]
x = float(sample.get('x', 0))
y = float(sample.get('y', 0))
addr = sample.get('naddr', '')

print("=" * 80)
print("샘플 좌표 분석:")
print("=" * 80)
print(f"주소: {addr}")
print(f"x: {x}")
print(f"y: {y}")

# 좌표 범위
xs = [float(item.get('x', 0)) for item in items if item.get('x')]
ys = [float(item.get('y', 0)) for item in items if item.get('y')]

print(f"\n전체 x 범위: {min(xs):.0f} ~ {max(xs):.0f}")
print(f"전체 y 범위: {min(ys):.0f} ~ {max(ys):.0f}")

print("\n" + "=" * 80)
print("좌표계 분석:")
print("=" * 80)

# 일반적인 한국 좌표계 범위
print("\n1. 표준 한국 좌표계 (EPSG:5174 등):")
print("   - x: 200,000 ~ 800,000 (미터)")
print("   - y: 400,000 ~ 700,000 (미터)")
print("   - 서울 지역: x≈200,000~300,000, y≈500,000~600,000")

print("\n2. 현재 데이터 좌표:")
print(f"   - x: {min(xs):.0f} ~ {max(xs):.0f}")
print(f"   - y: {min(ys):.0f} ~ {max(ys):.0f}")

print("\n3. 가능한 좌표계:")
print("   a) EPSG:5174 (Korea 2000 / Central Belt 2010) - 표준 범위 아님")
print("   b) 커스텀 좌표계 또는 변환된 좌표")
print("   c) SGIS 자체 좌표계 (내부 좌표계)")

# 좌표 변환 테스트 (pyproj가 설치되어 있다면)
try:
    from pyproj import Transformer
    
    print("\n" + "=" * 80)
    print("좌표 변환 테스트:")
    print("=" * 80)
    
    # 현재 좌표를 WGS84로 변환 시도
    # 만약 현재 좌표가 EPSG:5174라면
    transformer_5174 = Transformer.from_crs("EPSG:5174", "EPSG:4326", always_xy=True)
    lon, lat = transformer_5174.transform(x, y)
    print(f"\nEPSG:5174 → WGS84 변환:")
    print(f"  경도: {lon:.6f}, 위도: {lat:.6f}")
    print(f"  (서울 지역이면 경도≈126~127, 위도≈37~38)")
    
    # 역변환 테스트
    transformer_reverse = Transformer.from_crs("EPSG:4326", "EPSG:5174", always_xy=True)
    x_test, y_test = transformer_reverse.transform(126.5, 37.5)  # 서울 중심
    print(f"\nWGS84 (서울 중심) → EPSG:5174:")
    print(f"  x: {x_test:.0f}, y: {y_test:.0f}")
    print(f"  (현재 데이터와 비교: x={x:.0f}, y={y:.0f})")
    
    if abs(x_test - x) < 100000 and abs(y_test - y) < 100000:
        print("\n  → EPSG:5174일 가능성이 있으나 스케일이 다름")
    else:
        print("\n  → EPSG:5174가 아닐 가능성 높음")
        
except ImportError:
    print("\npyproj가 설치되지 않아 좌표 변환 테스트를 수행할 수 없습니다.")
    print("설치: pip install pyproj")
except Exception as e:
    print(f"\n좌표 변환 테스트 중 오류: {e}")

print("\n" + "=" * 80)
print("결론:")
print("=" * 80)
print("현재 좌표 값 (x=95만대, y=194만대)은 표준 한국 좌표계 범위를 벗어납니다.")
print("SGIS API 문서에서 좌표계 정보를 확인하거나,")
print("실제 지도에 표시하여 좌표계를 확인해야 합니다.")
print("\n가능성:")
print("1. SGIS 자체 좌표계 (내부 좌표계)")
print("2. 변환된 좌표 (스케일 조정 또는 오프셋 적용)")
print("3. 다른 좌표계 (UTM 등)")

