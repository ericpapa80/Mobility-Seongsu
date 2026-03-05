"""컬럼 매핑 가이드 생성 스크립트"""
import sys
import io

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import pandas as pd

df = pd.read_csv('restaurants_all.csv', nrows=3)

print("=" * 60)
print("컬럼 매핑 가이드 - 올바른 예시 값")
print("=" * 60)
print()

# 좌표 관련
print("=== 좌표 컬럼 ===")
print(f"gps_latitude (위도): {df['gps_latitude'].iloc[0]}")
print(f"gps_longitude (경도): {df['gps_longitude'].iloc[0]}")
print()

# 이름 관련
print("=== 이름 컬럼 ===")
print(f"headerInfo_nameKR (한글명): {df['headerInfo_nameKR'].iloc[0]}")
print(f"headerInfo_nameEN (영문명): {df['headerInfo_nameEN'].iloc[0]}")
print()

# 주소 관련
print("=== 주소 컬럼 ===")
print(f"juso_roadAddrPart1 (도로명주소): {df['juso_roadAddrPart1'].iloc[0]}")
print(f"juso_jibunAddr (지번주소): {df['juso_jibunAddr'].iloc[0]}")
print(f"juso_detailAddress (상세주소): {df['juso_detailAddress'].iloc[0]}")
print(f"juso_zone2_1 (지역1): {df['juso_zone2_1'].iloc[0]}")
print(f"juso_zone2_2 (지역2): {df['juso_zone2_2'].iloc[0]}")
print(f"juso_map_1 (지도지역1): {df['juso_map_1'].iloc[0]}")
print(f"juso_map_2 (지도지역2): {df['juso_map_2'].iloc[0]}")
print(f"juso_rn (도로명): {df['juso_rn'].iloc[0]}")
print(f"juso_buldMnnm (건물번호): {df['juso_buldMnnm'].iloc[0]}")
print()

# 리뷰 관련
print("=== 리뷰 컬럼 ===")
print(f"review_review (리뷰): {str(df['review_review'].iloc[0])[:60]}...")
print(f"review_reviewSimple (간단리뷰): {str(df['review_reviewSimple'].iloc[0])[:60]}...")
print(f"review_readerReview (독자리뷰): {df['review_readerReview'].iloc[0]}")
print(f"review_businessReview (사업자리뷰): {df['review_businessReview'].iloc[0]}")
print()

# 추가 정보
print("=== 추가 정보 컬럼 ===")
print(f"extraInfo_wineInputType (와인반입): {df['extraInfo_wineInputType'].iloc[0]}")
print(f"extraInfo_wineInputYesEtc (와인반입기타): {df['extraInfo_wineInputYesEtc'].iloc[0]}")
print(f"extraInfo_wineCorkageEtc (와인코르크기타): {df['extraInfo_wineCorkageEtc'].iloc[0]}")
print(f"extraInfo_holidayYn (공휴일영업): {df['extraInfo_holidayYn'].iloc[0]}")
print()

print("=" * 60)
print("드롭다운에서 잘못 표시된 예시 (수정 필요)")
print("=" * 60)
print()
print("잘못된 매핑:")
print("  gps_latitude 예시: '청담동/강남구청역' -> 올바른 값: 숫자 좌표 (37.5174902364919)")
print("  gps_longitude 예시: '서울 강남지역' -> 올바른 값: 숫자 좌표 (127.036153686218)")
print("  review_reviewSimple 예시: '37.5174902364919' -> 올바른 값: 리뷰 텍스트")
print("  review_readerReview 예시: '127.036153686218' -> 올바른 값: 리뷰 텍스트 또는 빈 값")
print("  juso_zone2_2 예시: '23' -> 올바른 값: 지역명 (청담동/강남구청역)")
print("  juso_map_1 예시: '0' -> 올바른 값: 지역명 (서울 강남지역)")
print("  juso_map_2 예시: '서울 강남' -> 올바른 값: 지도 상세지역 (g. 학동사거리-강남구청역)")
print("  juso_rn 예시: '강남구' -> 올바른 값: 도로명 (보통 빈 값)")
print("  juso_buldMnnm 예시: '논현동' -> 올바른 값: 건물번호 (23)")
print("  review_review 예시: 'g. 학동사거리-강남구청역' -> 올바른 값: 리뷰 텍스트")
print("  extraInfo_wineInputType 예시: '된장찌개와 함께...' -> 올바른 값: NO_CHECK 등")

