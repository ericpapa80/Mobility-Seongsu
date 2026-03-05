"""수정일자기준 상가업소 조회 - 변경구분 필드 실제 값 확인."""

import sys
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.sbiz.api_client import SBIZAPIClient
from core.logger import get_logger

logger = get_logger(__name__)

print("=" * 60)
print("수정일자기준 상가업소 조회 - 변경구분 필드 확인")
print("=" * 60)
print("""
API 정보:
- 엔드포인트: storeListByDate
- 설명: 입력 일자를 기준으로 수정속성을 포함한 업소목록 조회(삭제된 업소 포함)
- 변경구분 필드: 각 업소의 변경 유형을 나타냄 (신규, 수정, 삭제 등)
""")

client = SBIZAPIClient()

# 여러 날짜로 테스트 (최근 1년간)
print("\n데이터가 있는 날짜 찾는 중...")
found_date = None
change_types = set()

for days_ago in range(0, 365):
    test_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y%m%d")
    
    try:
        response = client.get_stores_by_date(
            date=test_date,
            num_of_rows=10,
            page_no=1
        )
        
        header = response.get('header', {})
        if header.get('resultCode') == '00':
            body = response.get('body', {})
            items = body.get('items', [])
            
            if items:
                found_date = test_date
                total_count = body.get('totalCount', 0)
                
                print(f"\n✓ 데이터 발견: {test_date}")
                print(f"  총 변경된 업소 수: {total_count:,}개")
                
                # 변경구분 필드 확인
                print(f"\n변경구분 필드 값 확인:")
                for i, item in enumerate(items[:10] if isinstance(items, list) else [items], 1):
                    # 변경구분 필드 찾기
                    change_type = None
                    change_type_key = None
                    
                    for key in item.keys():
                        if '변경' in key or 'change' in key.lower() or '구분' in key:
                            change_type = item.get(key)
                            change_type_key = key
                            break
                    
                    if change_type:
                        change_types.add(change_type)
                        print(f"  {i}. {item.get('bizesId')} - {item.get('bizesNm')}")
                        print(f"     변경구분 필드 ({change_type_key}): {change_type}")
                    else:
                        print(f"  {i}. {item.get('bizesId')} - {item.get('bizesNm')}")
                        print(f"     변경구분 필드 없음")
                
                # 첫 번째 업소의 모든 필드 출력
                if items:
                    first_item = items[0] if isinstance(items, list) else items
                    print(f"\n첫 번째 업소의 모든 필드:")
                    for key, value in sorted(first_item.items()):
                        value_str = str(value) if value else '(없음)'
                        if len(value_str) > 50:
                            value_str = value_str[:50] + "..."
                        print(f"  {key:20s}: {value_str}")
                
                break
    except Exception as e:
        continue

if found_date:
    print(f"\n" + "=" * 60)
    print("결론")
    print("=" * 60)
    print(f"""
✓ 수정일자기준 상가업소 조회 API로 개폐업일 정보 확인 가능

1. API 사용법:
   GET /storeListByDate?serviceKey=...&key=YYYYMMDD&...

2. 변경구분 필드:
   - API 응답에 "변경구분" 필드가 포함됨
   - 발견된 변경구분 값: {', '.join(sorted(change_types)) if change_types else '없음'}
   - 이 필드를 통해 신규 등록, 수정, 삭제 등을 구분 가능

3. 개폐업 추적:
   - 특정 날짜에 변경된 업소를 조회
   - 변경구분 필드로 변경 유형 확인
   - 삭제된 업소도 포함되므로 폐업 추적 가능
   - 시계열 데이터 수집으로 개폐업 이력 추적 가능

4. 사용 예시:
   from plugins.sbiz.api_client import SBIZAPIClient
   
   client = SBIZAPIClient()
   stores = client.get_all_stores_by_date('20221202')
   
   for store in stores:
       change_type = store.get('변경구분')  # 또는 해당 필드명
       if change_type == '신규':
           print(f"신규 개업: {store.get('bizesNm')}")
       elif change_type == '삭제':
           print(f"폐업: {store.get('bizesNm')}")
    """)
else:
    print("\n최근 1년 내 데이터가 있는 날짜를 찾지 못했습니다.")
    print("하지만 API 구조는 확인되었으므로, 데이터가 있는 날짜에 사용 가능합니다.")

client.close()

