"""단일 상가업소 조회로 확인 가능한 모든 정보 표시."""

import sys
from pathlib import Path
import requests
import json

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.scrapers.sbiz import SBIZConfig

# 성수동 데이터에서 실제 존재하는 상가업소번호 사용
json_file = Path('data/raw/sbiz/sbiz_stores_seongsu_extracted_20251202_094917/sbiz_stores_seongsu_20251202_094917.json')

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 실제 존재하는 상가업소번호 사용
test_bizes_id = data['stores'][0].get('bizesId')
test_name = data['stores'][0].get('bizesNm')

print("=" * 60)
print("단일 상가업소 조회 API로 확인 가능한 정보")
print("=" * 60)
print(f"상가업소번호: {test_bizes_id}")
print(f"상호명: {test_name}")
print()

service_key = SBIZConfig.get_service_key()
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
        body = result.get('body', {})
        
        if header.get('resultCode') == '00':
            items = body.get('items', [])
            
            if items:
                store = items[0] if isinstance(items, list) else items
                
                print("=" * 60)
                print("✅ 단일 상가업소 조회로 확인 가능한 정보 (총 39개 필드)")
                print("=" * 60)
                
                # 카테고리별로 정리
                categories = {
                    "기본 정보": [
                        'bizesId', 'bizesNm', 'brchNm'
                    ],
                    "업종 정보": [
                        'indsLclsCd', 'indsLclsNm',
                        'indsMclsCd', 'indsMclsNm',
                        'indsSclsCd', 'indsSclsNm',
                        'ksicCd', 'ksicNm'
                    ],
                    "행정구역 정보": [
                        'ctprvnCd', 'ctprvnNm',
                        'signguCd', 'signguNm',
                        'adongCd', 'adongNm',
                        'ldongCd', 'ldongNm'
                    ],
                    "지번 주소 정보": [
                        'lnoCd', 'plotSctCd', 'plotSctNm',
                        'lnoMnno', 'lnoSlno', 'lnoAdr'
                    ],
                    "도로명 주소 정보": [
                        'rdnmCd', 'rdnm',
                        'bldMnno', 'bldSlno', 'bldMngNo', 'bldNm',
                        'rdnmAdr'
                    ],
                    "우편번호": [
                        'oldZipcd', 'newZipcd'
                    ],
                    "상세 위치": [
                        'dongNo', 'flrNo', 'hoNo'
                    ],
                    "좌표 정보": [
                        'lon', 'lat'
                    ]
                }
                
                for category, fields in categories.items():
                    print(f"\n【 {category} 】")
                    for field in fields:
                        value = store.get(field, 'N/A')
                        if value == '':
                            value = '(없음)'
                        print(f"  {field:20s}: {value}")
                
                print("\n" + "=" * 60)
                print("API 응답 구조")
                print("=" * 60)
                print("""
응답 형식:
{
  "header": {
    "description": "소상공인시장진흥공단 상가업소정보",
    "columns": [...],  // 제공되는 컬럼 목록
    "stdrYm": "202509",  // 기준년월
    "resultCode": "00",  // 결과코드 (00: 정상)
    "resultMsg": "NORMAL SERVICE"  // 결과메시지
  },
  "body": {
    "items": [
      {
        // 위의 39개 필드 정보
      }
    ]
  }
}
                """)
                
                print("=" * 60)
                print("주요 활용 정보")
                print("=" * 60)
                print("""
1. 위치 식별
   - 행정동코드/명: 행정동 단위 조회에 사용
   - 법정동코드/명: 법정동 정보
   - 좌표(lon, lat): 지도 시각화, 거리 계산

2. 업종 분석
   - 상권업종분류: 상권 특성 분석
   - 표준산업분류: 통계청 데이터와 연계

3. 주소 정보
   - 지번주소: 전통적인 주소 체계
   - 도로명주소: 새로운 주소 체계
   - 건물관리번호: 건물 단위 조회에 사용

4. 상세 위치
   - 층정보, 호정보: 건물 내 정확한 위치
                """)
                
        else:
            print(f"✗ API 오류: {header.get('resultMsg')}")
            print(f"  resultCode: {header.get('resultCode')}")
            print("\n※ 주의: 상가업소번호가 존재하지 않거나 잘못된 경우")
            print("  resultCode: '03' (NODATA_ERROR) 반환")
    else:
        print(f"✗ HTTP 오류: {response.status_code}")
        
except Exception as e:
    print(f"✗ 오류 발생: {e}")

