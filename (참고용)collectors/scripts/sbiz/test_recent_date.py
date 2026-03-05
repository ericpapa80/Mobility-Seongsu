"""최근 날짜로 수정일자기준 조회 테스트."""

import sys
from pathlib import Path
import requests
import json
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.scrapers.sbiz import SBIZConfig

service_key = SBIZConfig.get_service_key()
endpoint = "http://apis.data.go.kr/B553077/api/open/sdsc2/storeListByDate"

print("=" * 60)
print("수정일자기준 상가업소 조회 - 최근 날짜 테스트")
print("=" * 60)

# 최근 30일 동안 데이터가 있는 날짜 찾기
for days_ago in range(0, 30):
    test_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y%m%d")
    
    params = {
        'serviceKey': service_key,
        'key': test_date,
        'numOfRows': 1,
        'pageNo': 1,
        'type': 'json'
    }
    
    try:
        response = requests.get(endpoint, params=params, timeout=30)
        if response.status_code == 200:
            result = response.json()
            header = result.get('header', {})
            
            if header.get('resultCode') == '00':
                body = result.get('body', {})
                total_count = body.get('totalCount', 0)
                
                if total_count > 0:
                    print(f"\n✓ 데이터 발견: {test_date}")
                    print(f"  변경된 업소 수: {total_count:,}개")
                    
                    items = body.get('items', [])
                    if items:
                        item = items[0]
                        print(f"\n  예시 업소:")
                        print(f"    상가업소번호: {item.get('bizesId')}")
                        print(f"    상호명: {item.get('bizesNm')}")
                        print(f"    행정동: {item.get('adongNm')}")
                    
                    print(f"\n" + "=" * 60)
                    print("개폐업일 정보 확인 방법 요약")
                    print("=" * 60)
                    print(f"""
API: storeListByDate (수정일자기준 상가업소 조회)

요청 방법:
  GET {endpoint}
  ?serviceKey={service_key[:20]}...
  &key={test_date}  ← YYYYMMDD 형식의 날짜
  &numOfRows=1000
  &pageNo=1
  &type=json

설명:
  - 특정 날짜에 변경된 업소를 조회합니다
  - 신규 등록, 정보 수정, 폐업 등 모든 변경사항을 추적할 수 있습니다
  - 하지만 개폐업일 정보를 직접 제공하지는 않습니다

시계열 데이터 수집:
  1. 매일 정기적으로 수정일자기준 조회 수행
  2. 날짜별 변경된 업소 목록 저장
  3. 이전 데이터와 비교하여 개폐업 추적
     - 새로 추가된 업소 → 신규 개업
     - 사라진 업소 → 폐업 가능성
     - 정보 변경된 업소 → 정보 수정

주의:
  - 이 API는 "영업중인 상가 업소정보"만 제공
  - 폐업한 업소는 조회 결과에서 제외됨
  - 폐업 추적은 이전 데이터와의 비교를 통해 간접적으로 확인
                    """)
                    break
    except:
        continue
else:
    print("\n최근 30일 내 데이터가 있는 날짜를 찾지 못했습니다.")
    print("API 사용법은 동일합니다.")

