"""개폐업일 정보 확인 - 실제 API 응답 구조 확인."""

import sys
from pathlib import Path
import requests
import json

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.scrapers.sbiz import SBIZConfig

# 성수동 데이터에서 실제 상가업소번호 사용
json_file = Path('data/raw/sbiz/sbiz_stores_seongsu_extracted_20251202_094917/sbiz_stores_seongsu_20251202_094917.json')

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

test_bizes_id = data['stores'][0].get('bizesId')
test_name = data['stores'][0].get('bizesNm')

print("=" * 60)
print("개폐업일 정보 확인")
print("=" * 60)
print(f"상가업소번호: {test_bizes_id}")
print(f"상호명: {test_name}")
print()

service_key = SBIZConfig.get_service_key()

# 1. 단일 상가업소 조회로 모든 필드 확인
print("1. 단일 상가업소 조회 (storeOne) - 모든 필드 확인")
print("-" * 60)

endpoint = "http://apis.data.go.kr/B553077/api/open/sdsc2/storeOne"
params = {
    'serviceKey': service_key,
    'key': test_bizes_id,
    'type': 'json'
}

try:
    response = requests.get(endpoint, params=params, timeout=30)
    if response.status_code == 200:
        result = response.json()
        header = result.get('header', {})
        
        if header.get('resultCode') == '00':
            items = result.get('body', {}).get('items', [])
            if items:
                store = items[0] if isinstance(items, list) else items
                
                # 개폐업일 관련 필드 찾기
                date_fields = [k for k in store.keys() if 'date' in k.lower() or 'dt' in k.lower() or '일' in k or 'open' in k.lower() or 'close' in k.lower()]
                
                print(f"✓ 응답 성공")
                print(f"\n개폐업일 관련 필드 검색:")
                if date_fields:
                    for field in date_fields:
                        print(f"  {field}: {store.get(field, 'N/A')}")
                else:
                    print(f"  ✗ 개폐업일 관련 필드 없음")
                
                print(f"\n전체 필드 목록 ({len(store)}개):")
                for key in sorted(store.keys()):
                    print(f"  {key}")
                
                # 수정일자기준 조회 API 확인
                print(f"\n" + "=" * 60)
                print("2. 수정일자기준 상가업소 조회 (storeListByDate)")
                print("-" * 60)
                print("※ 이 API는 특정 수정일자에 변경된 업소를 조회하는 API입니다.")
                print("  개폐업일 정보를 직접 제공하지는 않습니다.")
                
except Exception as e:
    print(f"✗ 오류: {e}")

# 3. 다른 API 확인
print(f"\n" + "=" * 60)
print("3. 개폐업일 정보 제공 가능 여부")
print("-" * 60)
print("""
현재 확인된 사실:
1. 단일 상가업소 조회 (storeOne) API 응답에는 개폐업일 필드가 포함되지 않음
2. 수정일자기준 조회 (storeListByDate)는 수정일자를 기준으로 조회하는 API
3. 상가업소정보 변경요청 (reqStoreModify)에는 개업일자/폐업일자 입력 필드가 있음
   - 하지만 이것은 사용자가 정보를 변경 요청할 때 입력하는 필드

결론:
- 현재 제공되는 API로는 개폐업일 정보를 직접 조회할 수 없음
- 수정일자기준 조회를 통해 특정 날짜에 변경된 업소를 추적할 수는 있음
- 시계열 데이터 수집을 위해서는 정기적으로 수정일자기준 조회를 수행해야 함
""")

