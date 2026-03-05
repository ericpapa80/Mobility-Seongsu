"""JSON 파일의 x, y 좌표 분석"""

import json
from pathlib import Path

json_file = Path("data/raw/sgis/20251130_214212/sgis_technical_biz_20251130_214212.json")

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

items = data.get('result', [])
print(f"총 {len(items)}개 항목\n")

print("=" * 80)
print("첫 10개 항목의 x, y 좌표:")
print("=" * 80)
for i, item in enumerate(items[:10]):
    print(f"{i+1}. x={item.get('x', 'N/A')}, y={item.get('y', 'N/A')}, 주소={item.get('naddr', 'N/A')}")

# 좌표 범위 분석
xs = [float(item.get('x', 0)) for item in items if item.get('x')]
ys = [float(item.get('y', 0)) for item in items if item.get('y')]

print("\n" + "=" * 80)
print("좌표 범위 분석:")
print("=" * 80)
print(f"x 좌표 범위: {min(xs):.2f} ~ {max(xs):.2f}")
print(f"y 좌표 범위: {min(ys):.2f} ~ {max(ys):.2f}")
print(f"\nx 좌표 평균: {sum(xs)/len(xs):.2f}")
print(f"y 좌표 평균: {sum(ys)/len(ys):.2f}")

# 좌표계 추정
print("\n" + "=" * 80)
print("EPSG 좌표계 추정:")
print("=" * 80)

# 한국에서 사용하는 주요 좌표계
# EPSG:5174 (Korea 2000 / Central Belt 2010) - x: 200000~800000, y: 400000~700000
# EPSG:5181 (Korea 2000 / Central Belt) - x: 200000~800000, y: 400000~700000
# EPSG:5179 (Korea 2000 / Central Belt 2010) - x: 200000~800000, y: 400000~700000
# EPSG:5186 (Korea 2000 / Central Belt 2010) - x: 200000~800000, y: 400000~700000
# EPSG:3857 (WGS84 / Pseudo-Mercator) - x: 10000000~15000000, y: 4000000~5000000
# EPSG:4326 (WGS84) - x: 124~132, y: 33~43

# 좌표 범위로 추정
if min(xs) > 900000 and max(xs) < 1000000 and min(ys) > 1900000 and max(ys) < 2000000:
    print("추정: EPSG:5174 (Korea 2000 / Central Belt 2010) 또는 유사한 좌표계")
    print("  - x 범위: 약 95만~96만 (서울 지역)")
    print("  - y 범위: 약 194만~195만 (서울 지역)")
    print("  - 단위: 미터")
elif min(xs) > 10000000:
    print("추정: EPSG:3857 (WGS84 / Pseudo-Mercator)")
    print("  - 단위: 미터")
elif min(xs) > 124 and max(xs) < 132 and min(ys) > 33 and max(ys) < 43:
    print("추정: EPSG:4326 (WGS84)")
    print("  - 단위: 도(degree)")
else:
    print("알 수 없는 좌표계 또는 커스텀 좌표계")

# 서울 지역 좌표계 확인
print("\n" + "=" * 80)
print("서울 지역 좌표계 정보:")
print("=" * 80)
print("한국에서 사용하는 주요 좌표계:")
print("  - EPSG:5174 (Korea 2000 / Central Belt 2010): x=200000~800000, y=400000~700000")
print("  - EPSG:5181 (Korea 2000 / Central Belt): x=200000~800000, y=400000~700000")
print("  - EPSG:5179 (Korea 2000 / Central Belt 2010): x=200000~800000, y=400000~700000")
print("\n현재 좌표 값:")
print(f"  - x: {min(xs):.0f} ~ {max(xs):.0f}")
print(f"  - y: {min(ys):.0f} ~ {max(ys):.0f}")
print("\n참고: 서울 지역의 경우 x=95만대, y=194만대는")
print("      좌표계 변환이나 스케일 조정이 적용된 값일 수 있습니다.")

