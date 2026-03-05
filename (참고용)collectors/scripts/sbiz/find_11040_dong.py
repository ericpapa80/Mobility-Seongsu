"""11040 관련 행정동 찾기."""

import sys
from pathlib import Path
import requests
import json

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.scrapers.sbiz import SBIZConfig

# 행정동 조회 API
def get_dongs(signgu_cd):
    """시군구의 행정동 목록 조회."""
    endpoint = "http://apis.data.go.kr/B553077/api/open/sdsc2/baroApi"
    service_key = SBIZConfig.get_service_key()
    
    params = {
        'serviceKey': service_key,
        'resId': 'dong',
        'catId': 'admi',  # 행정동
        'signguCd': signgu_cd,
        'type': 'json'
    }
    
    try:
        response = requests.get(endpoint, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"에러: {e}")
        return None

# 종로구 코드는 11110 (서울시 종로구)
# 하지만 11040도 확인해봐야 함
test_codes = ["11110", "11040"]

for code in test_codes:
    print(f"\n{'='*60}")
    print(f"시군구 코드: {code}의 행정동 목록 조회")
    print(f"{'='*60}")
    
    result = get_dongs(code)
    if result:
        body = result.get('body', {})
        items = body.get('items', [])
        
        if isinstance(items, dict):
            items = items.get('item', [])
            if not isinstance(items, list):
                items = [items] if items else []
        
        print(f"행정동 개수: {len(items)}")
        
        # 11040으로 시작하는 행정동 찾기
        found = [item for item in items if isinstance(item, dict) and item.get('adongCd', '').startswith('11040')]
        
        if found:
            print(f"\n11040으로 시작하는 행정동:")
            for item in found[:10]:  # 최대 10개만
                print(f"  {item.get('adongCd')}: {item.get('adongNm')}")
        else:
            print(f"\n11040으로 시작하는 행정동 없음")
            if items:
                print(f"\n첫 5개 행정동 예시:")
                for item in items[:5]:
                    print(f"  {item.get('adongCd')}: {item.get('adongNm')}")

