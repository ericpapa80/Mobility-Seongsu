"""수정일자기준 상가업소 조회 API 테스트 및 개폐업 추적 방법."""

import sys
from pathlib import Path
import requests
import json
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.scrapers.sbiz import SBIZConfig

print("=" * 60)
print("개폐업일 정보 확인 방법")
print("=" * 60)

service_key = SBIZConfig.get_service_key()
endpoint = "http://apis.data.go.kr/B553077/api/open/sdsc2/storeListByDate"

print("""
⚠ 중요: 현재 API는 개폐업일 정보를 직접 제공하지 않습니다.

대신 다음 방법으로 개폐업 추적이 가능합니다:

1. 수정일자기준 상가업소 조회 (storeListByDate)
   - 특정 날짜에 변경된 업소를 조회
   - 신규 등록, 정보 수정, 폐업 등 모든 변경사항 추적 가능

2. 시계열 데이터 수집 방법
   - 매일/매주 정기적으로 수정일자기준 조회 수행
   - 변경된 업소 목록을 비교하여 개폐업 추적
""")

print("\n" + "=" * 60)
print("수정일자기준 상가업소 조회 API 사용법")
print("=" * 60)

# 최근 날짜로 테스트
test_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

print(f"\n테스트 날짜: {test_date} (7일 전)")
print(f"API 엔드포인트: {endpoint}")

params = {
    'serviceKey': service_key,
    'key': test_date,  # YYYYMMDD 형식
    'numOfRows': 10,
    'pageNo': 1,
    'type': 'json'
}

print(f"\n요청 파라미터:")
print(f"  key (일자): {test_date}")
print(f"  numOfRows: 10")
print(f"  pageNo: 1")
print(f"  type: json")

try:
    response = requests.get(endpoint, params=params, timeout=30)
    print(f"\nHTTP 상태 코드: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        header = result.get('header', {})
        body = result.get('body', {})
        
        print(f"\n응답 결과:")
        print(f"  resultCode: {header.get('resultCode')}")
        print(f"  resultMsg: {header.get('resultMsg')}")
        print(f"  기준년월: {header.get('stdrYm', 'N/A')}")
        
        if header.get('resultCode') == '00':
            items = body.get('items', [])
            total_count = body.get('totalCount', 0)
            
            print(f"\n  총 변경된 업소 수: {total_count:,}개")
            print(f"  조회된 업소 수: {len(items)}개")
            
            if items:
                print(f"\n변경된 업소 예시 (최대 5개):")
                for i, item in enumerate(items[:5], 1):
                    print(f"  {i}. {item.get('bizesId')} - {item.get('bizesNm')} ({item.get('adongNm')})")
        else:
            print(f"\n  ✗ API 오류: {header.get('resultMsg')}")
            
except Exception as e:
    print(f"\n✗ 오류 발생: {e}")

print("\n" + "=" * 60)
print("개폐업 추적을 위한 시계열 데이터 수집 방법")
print("=" * 60)
print("""
1. 정기적 수집 스케줄
   - 매일 또는 매주 특정 시간에 수정일자기준 조회 수행
   - 예: 매일 자정에 전날 날짜로 조회

2. 데이터 비교 방법
   - 이전 수집 데이터와 비교
   - 새로 추가된 업소 → 신규 개업
   - 사라진 업소 → 폐업 가능성
   - 정보가 변경된 업소 → 정보 수정

3. 시계열 데이터 구조
   - 날짜별로 변경된 업소 목록 저장
   - 각 업소의 변경 이력 추적
   - 개폐업 패턴 분석 가능

4. 주의사항
   - 수정일자기준 조회는 "영업중인 상가 업소정보"만 제공
   - 폐업한 업소는 조회 결과에서 제외됨
   - 따라서 폐업 추적은 이전 데이터와의 비교를 통해 간접적으로 확인
""")

print("\n" + "=" * 60)
print("요청 예시")
print("=" * 60)
print(f"""
GET {endpoint}
?serviceKey={service_key[:20]}...
&key={test_date}
&numOfRows=1000
&pageNo=1
&type=json

※ key 파라미터는 YYYYMMDD 형식의 날짜입니다.
   예: 20251202, 20250101 등
""")

