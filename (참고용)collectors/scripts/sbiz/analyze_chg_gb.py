"""변경구분(chgGb) 필드 값 분석."""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.sbiz.api_client import SBIZAPIClient
from core.logger import get_logger

logger = get_logger(__name__)

print("=" * 60)
print("변경구분(chgGb) 필드 값 분석")
print("=" * 60)

client = SBIZAPIClient()

# 데이터가 있는 날짜로 테스트
test_date = "20250930"

print(f"\n테스트 날짜: {test_date}")
print("변경구분 필드 값 수집 중...\n")

try:
    # 최대 100개 업소 수집하여 변경구분 값 분석
    response = client.get_stores_by_date(
        date=test_date,
        num_of_rows=100,
        page_no=1
    )
    
    header = response.get('header', {})
    if header.get('resultCode') == '00':
        body = response.get('body', {})
        items = body.get('items', [])
        total_count = body.get('totalCount', 0)
        
        print(f"✓ 데이터 조회 성공")
        print(f"  총 변경된 업소 수: {total_count:,}개")
        print(f"  조회된 업소 수: {len(items)}개\n")
        
        # 변경구분 값 수집
        chg_gb_values = []
        chg_gb_examples = {}
        
        for item in items[:100]:
            chg_gb = item.get('chgGb')
            if chg_gb:
                chg_gb_values.append(chg_gb)
                if chg_gb not in chg_gb_examples:
                    chg_gb_examples[chg_gb] = {
                        'bizesId': item.get('bizesId'),
                        'bizesNm': item.get('bizesNm'),
                        'adongNm': item.get('adongNm')
                    }
        
        # 변경구분 값 통계
        counter = Counter(chg_gb_values)
        
        print("=" * 60)
        print("변경구분(chgGb) 필드 값 분석 결과")
        print("=" * 60)
        print(f"\n발견된 변경구분 값:")
        for value, count in counter.most_common():
            example = chg_gb_examples.get(value, {})
            print(f"  '{value}': {count}개")
            if example:
                print(f"    예시: {example.get('bizesId')} - {example.get('bizesNm')} ({example.get('adongNm')})")
        
        print(f"\n" + "=" * 60)
        print("변경구분 값 의미 추정")
        print("=" * 60)
        print("""
일반적인 변경구분 코드:
- C: Create (신규 등록)
- U: Update (수정)
- D: Delete (삭제/폐업)

※ 정확한 의미는 API 문서를 참조하거나 더 많은 데이터로 확인 필요
        """)
        
        # 더 많은 데이터로 확인
        print("더 많은 데이터 수집 중...")
        all_stores = client.get_all_stores_by_date(test_date)
        
        if len(all_stores) > 100:
            all_chg_gb = [s.get('chgGb') for s in all_stores if s.get('chgGb')]
            all_counter = Counter(all_chg_gb)
            
            print(f"\n전체 데이터 ({len(all_stores):,}개) 기준 변경구분 통계:")
            for value, count in all_counter.most_common():
                percentage = (count / len(all_chg_gb)) * 100 if all_chg_gb else 0
                print(f"  '{value}': {count:,}개 ({percentage:.1f}%)")
        
except Exception as e:
    print(f"오류: {e}")
    import traceback
    traceback.print_exc()

client.close()

print(f"\n" + "=" * 60)
print("결론")
print("=" * 60)
print("""
✓ 수정일자기준 상가업소 조회 API로 개폐업일 정보 확인 가능

1. API 사용법:
   GET /storeListByDate?serviceKey=...&key=YYYYMMDD&...

2. 변경구분 필드:
   - 필드명: chgGb
   - 각 업소의 변경 유형을 나타냄
   - 예상 값: C (Create/신규), U (Update/수정), D (Delete/삭제)

3. 개폐업 추적:
   - chgGb='C': 신규 개업
   - chgGb='D': 폐업 (삭제)
   - chgGb='U': 정보 수정
   - 특정 날짜에 변경된 모든 업소를 조회하여 개폐업 이력 추적 가능

4. 사용 예시:
   from plugins.sbiz.api_client import SBIZAPIClient
   
   client = SBIZAPIClient()
   stores = client.get_all_stores_by_date('20250930')
   
   for store in stores:
       chg_gb = store.get('chgGb')
       if chg_gb == 'C':
           print(f"신규 개업: {store.get('bizesNm')}")
       elif chg_gb == 'D':
           print(f"폐업: {store.get('bizesNm')}")
       elif chg_gb == 'U':
           print(f"정보 수정: {store.get('bizesNm')}")
""")

