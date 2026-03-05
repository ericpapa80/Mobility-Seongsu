"""단일 상가업소 조회 API 사용 가이드."""

import sys
from pathlib import Path
import requests
import json
from urllib.parse import quote

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.scrapers.sbiz import SBIZConfig

print("=" * 60)
print("단일 상가업소 조회 API 사용 가이드")
print("=" * 60)

# 성수동 데이터에서 실제 상가업소번호 예시
json_file = Path('data/raw/sbiz/sbiz_stores_seongsu_extracted_20251202_094917/sbiz_stores_seongsu_20251202_094917.json')

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 예시 상가업소번호
example_bizes_id = data['stores'][0].get('bizesId')

print(f"\n1. 상가업소번호 형식")
print(f"   - 필드명: bizesId")
print(f"   - 형식: MA로 시작하는 20자리 문자열")
print(f"   - 예시: {example_bizes_id}")

print(f"\n2. API 엔드포인트")
print(f"   URL: http://apis.data.go.kr/B553077/api/open/sdsc2/storeOne")

print(f"\n3. 필수 파라미터")
print(f"   - serviceKey: 서비스 인증키 (필수)")
print(f"   - key: 상가업소번호 (필수) - bizesId 값을 그대로 사용")
print(f"   - type: 데이터 유형 (선택) - json 또는 xml (기본값: xml)")

print(f"\n4. 요청 예시")
service_key = SBIZConfig.get_service_key()
endpoint = "http://apis.data.go.kr/B553077/api/open/sdsc2/storeOne"

params = {
    'serviceKey': service_key,
    'key': example_bizes_id,  # 상가업소번호를 그대로 사용
    'type': 'json'
}

print(f"   GET {endpoint}")
print(f"   ?serviceKey={service_key[:20]}...")
print(f"   &key={example_bizes_id}")
print(f"   &type=json")

print(f"\n5. 실제 테스트")
try:
    response = requests.get(endpoint, params=params, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        header = result.get('header', {})
        body = result.get('body', {})
        
        if header.get('resultCode') == '00':
            items = body.get('items', [])
            if items:
                item = items[0]
                print(f"   ✓ 성공!")
                print(f"   - 상호명: {item.get('bizesNm')}")
                print(f"   - 주소: {item.get('lnoAdr')}")
                print(f"   - 행정동: {item.get('adongNm')}")
            else:
                print(f"   ✗ 데이터 없음")
        else:
            print(f"   ✗ API 오류: {header.get('resultMsg')}")
    else:
        print(f"   ✗ HTTP 오류: {response.status_code}")
        
except Exception as e:
    print(f"   ✗ 오류: {e}")

print(f"\n6. 주의사항")
print(f"   - 상가업소번호는 JSON 데이터의 'bizesId' 필드 값을 그대로 사용")
print(f"   - URL 인코딩이 필요 없음 (requests 라이브러리 사용 시 자동 처리)")
print(f"   - 상가업소번호는 대소문자 구분 (MA는 대문자)")
print(f"   - 잘못된 상가업소번호 입력 시 resultCode가 '03' (NODATA_ERROR) 반환")

print(f"\n7. 성수동 데이터에서 상가업소번호 확인 방법")
print(f"   - JSON 파일: stores 배열의 각 항목의 'bizesId' 필드")
print(f"   - CSV 파일: 'bizesId' 컬럼")
print(f"   - 예시:")
for i, store in enumerate(data['stores'][:5], 1):
    print(f"     {i}. {store.get('bizesId')} - {store.get('bizesNm')}")

