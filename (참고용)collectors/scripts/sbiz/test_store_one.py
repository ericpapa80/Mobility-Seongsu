"""단일 상가업소 조회 API 테스트."""

import sys
from pathlib import Path
import requests
import json

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.scrapers.sbiz import SBIZConfig

# 성수동 데이터에서 상가업소번호 가져오기
json_file = Path('data/raw/sbiz/sbiz_stores_seongsu_extracted_20251202_094917/sbiz_stores_seongsu_20251202_094917.json')

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 테스트할 상가업소번호들
test_bizes_ids = [
    data['stores'][0].get('bizesId'),  # 첫 번째 업소
    data['stores'][1].get('bizesId'),  # 두 번째 업소
    'MA010120220800003375',  # 직접 입력
]

service_key = SBIZConfig.get_service_key()
endpoint = "http://apis.data.go.kr/B553077/api/open/sdsc2/storeOne"

print("=" * 60)
print("단일 상가업소 조회 API 테스트")
print("=" * 60)

for i, bizes_id in enumerate(test_bizes_ids, 1):
    if not bizes_id:
        continue
        
    print(f"\n테스트 {i}: {bizes_id}")
    print("-" * 60)
    
    # 파라미터 설정
    params = {
        'serviceKey': service_key,
        'key': bizes_id,  # 상가업소번호
        'type': 'json'
    }
    
    try:
        response = requests.get(endpoint, params=params, timeout=30)
        print(f"상태 코드: {response.status_code}")
        print(f"URL: {response.url[:100]}...")
        
        if response.status_code == 200:
            result = response.json()
            
            # 응답 구조 확인
            header = result.get('header', {})
            body = result.get('body', {})
            
            print(f"resultCode: {header.get('resultCode')}")
            print(f"resultMsg: {header.get('resultMsg')}")
            
            if header.get('resultCode') == '00':
                items = body.get('items', {})
                print(f"items 타입: {type(items)}")
                
                # items가 리스트인 경우
                if isinstance(items, list):
                    if items:
                        item = items[0]
                        print(f"✓ 성공!")
                        print(f"  상호명: {item.get('bizesNm')}")
                        print(f"  주소: {item.get('lnoAdr')}")
                        print(f"  행정동: {item.get('adongNm')}")
                    else:
                        print(f"✗ items 리스트가 비어있음")
                # items가 dict인 경우
                elif isinstance(items, dict):
                    item = items.get('item')
                    if item:
                        print(f"✓ 성공!")
                        print(f"  상호명: {item.get('bizesNm')}")
                        print(f"  주소: {item.get('lnoAdr')}")
                        print(f"  행정동: {item.get('adongNm')}")
                    else:
                        print(f"✗ item이 없음")
                        print(f"items 키: {list(items.keys())}")
                else:
                    print(f"✗ items 형식 오류: {type(items)}")
                    print(f"items 내용: {items}")
            else:
                print(f"✗ API 오류: {header.get('resultMsg')}")
                print(f"응답 내용: {response.text[:500]}")
        else:
            print(f"✗ HTTP 오류: {response.status_code}")
            print(f"응답 내용: {response.text[:500]}")
            
    except Exception as e:
        print(f"✗ 예외 발생: {e}")
        import traceback
        traceback.print_exc()

