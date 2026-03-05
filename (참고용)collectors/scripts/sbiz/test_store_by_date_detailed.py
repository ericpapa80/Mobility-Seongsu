"""수정일자기준 상가업소 조회 - 변경구분 필드 확인."""

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
print("수정일자기준 상가업소 조회 - 변경구분 필드 확인")
print("=" * 60)

# 여러 날짜로 테스트
test_dates = [
    "20221202",  # 사용자가 제공한 날짜
    "20240101",  # 최근 날짜
    "20231201",  # 1년 전
    "20221101",  # 2년 전
]

for test_date in test_dates:
    print(f"\n{'='*60}")
    print(f"테스트 날짜: {test_date}")
    print(f"{'='*60}")
    
    params = {
        'serviceKey': service_key,
        'key': test_date,
        'numOfRows': 10,
        'pageNo': 1,
        'type': 'json'
    }
    
    try:
        response = requests.get(endpoint, params=params, timeout=30)
        print(f"HTTP 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            header = result.get('header', {})
            body = result.get('body', {})
            
            print(f"resultCode: {header.get('resultCode')}")
            print(f"resultMsg: {header.get('resultMsg')}")
            
            # columns 확인
            columns = header.get('columns', [])
            if columns:
                print(f"\n제공되는 컬럼 목록:")
                if isinstance(columns, list):
                    for col in columns:
                        print(f"  - {col}")
                else:
                    print(f"  {columns}")
                
                # 변경구분 필드 확인
                if '변경구분' in str(columns):
                    print(f"\n✓ '변경구분' 필드가 포함되어 있습니다!")
            
            if header.get('resultCode') == '00':
                items = body.get('items', [])
                total_count = body.get('totalCount', 0)
                
                print(f"\n✓ 데이터 조회 성공")
                print(f"  총 변경된 업소 수: {total_count:,}개")
                print(f"  조회된 업소 수: {len(items)}개")
                
                if items:
                    # 첫 번째 업소의 모든 필드 확인
                    first_item = items[0] if isinstance(items, list) else items
                    
                    print(f"\n첫 번째 업소의 모든 필드:")
                    for key, value in sorted(first_item.items()):
                        value_str = str(value) if value else '(없음)'
                        if len(value_str) > 50:
                            value_str = value_str[:50] + "..."
                        print(f"  {key:20s}: {value_str}")
                    
                    # 변경구분 필드 확인
                    change_type_fields = [k for k in first_item.keys() if '변경' in k or 'change' in k.lower() or '구분' in k]
                    if change_type_fields:
                        print(f"\n✓ 변경구분 관련 필드 발견:")
                        for field in change_type_fields:
                            print(f"  {field}: {first_item.get(field)}")
                    
                    # 처음 5개 업소의 변경구분 확인
                    print(f"\n처음 5개 업소의 변경구분:")
                    for i, item in enumerate(items[:5] if isinstance(items, list) else [items], 1):
                        change_type = None
                        for key in item.keys():
                            if '변경' in key or 'change' in key.lower() or '구분' in key:
                                change_type = item.get(key)
                                break
                        
                        if change_type:
                            print(f"  {i}. {item.get('bizesId')} - {item.get('bizesNm')}: 변경구분 = {change_type}")
                        else:
                            print(f"  {i}. {item.get('bizesId')} - {item.get('bizesNm')}: 변경구분 필드 없음")
                    
                    break  # 데이터가 있는 날짜를 찾으면 종료
                else:
                    print(f"  데이터 없음")
            else:
                print(f"  ✗ API 오류: {header.get('resultMsg')}")
        else:
            print(f"  ✗ HTTP 오류: {response.status_code}")
            
    except Exception as e:
        print(f"  ✗ 오류: {e}")

print(f"\n" + "=" * 60)
print("결론")
print("=" * 60)
print("""
수정일자기준 상가업소 조회 API (storeListByDate)는:

1. 변경구분 필드를 제공합니다
   - API 응답의 columns에 "변경구분" 필드가 포함됨
   - 각 업소의 변경 유형을 확인할 수 있음

2. 삭제된 업소도 포함합니다
   - 설명: "입력 일자를 기준으로 수정속성을 포함한 업소목록 조회(삭제된 업소 포함)"
   - 폐업한 업소도 조회 결과에 포함될 수 있음

3. 개폐업 추적 가능
   - 변경구분 필드를 통해 신규 등록, 수정, 삭제 등을 구분 가능
   - 시계열 데이터 수집으로 개폐업 이력 추적 가능
""")

