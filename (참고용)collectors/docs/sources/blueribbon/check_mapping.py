"""드롭다운 매핑 확인 스크립트"""
import sys
import io

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import pandas as pd

df = pd.read_csv('restaurants_all.csv', nrows=1)

print("=== 실제 CSV 데이터 (첫 번째 레스토랑) ===")
print(f"gps_latitude: {df['gps_latitude'].iloc[0]}")
print(f"gps_longitude: {df['gps_longitude'].iloc[0]}")
print(f"\njuso_zone2_2: {df['juso_zone2_2'].iloc[0]}")
print(f"juso_map_1: {df['juso_map_1'].iloc[0]}")
print(f"\nreview_reviewSimple: {str(df['review_reviewSimple'].iloc[0])[:80]}...")
print(f"review_readerReview: {df['review_readerReview'].iloc[0]}")

print("\n=== 문제점 ===")
print("드롭다운에서 잘못 표시된 예시:")
print("  gps_latitude 예시: '청담동/강남구청역' (잘못됨 - 실제로는 juso_zone2_2 값)")
print("  gps_longitude 예시: '서울 강남지역' (잘못됨 - 실제로는 juso_map_1 값)")
print("  review_reviewSimple 예시: '37.5174902364919' (잘못됨 - 실제로는 gps_latitude 값)")
print("  review_readerReview 예시: '127.036153686218' (잘못됨 - 실제로는 gps_longitude 값)")

print("\n=== 올바른 매핑 ===")
print("  gps_latitude: 숫자 좌표값 (예: 37.5174902364919)")
print("  gps_longitude: 숫자 좌표값 (예: 127.036153686218)")
print("  juso_zone2_2: 지역명 (예: 청담동/강남구청역)")
print("  juso_map_1: 지역명 (예: 서울 강남지역)")
print("  review_reviewSimple: 리뷰 텍스트")

