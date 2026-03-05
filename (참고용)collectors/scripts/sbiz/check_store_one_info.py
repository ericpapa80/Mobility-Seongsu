"""단일 상가업소 조회로 확인 가능한 정보 확인."""

import sys
from pathlib import Path
import requests
import json

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.scrapers.sbiz import SBIZConfig

# 사용자가 제공한 상가업소번호
target_bizes_id = "0101202504A0041274"

print("=" * 60)
print("단일 상가업소 조회 API로 확인 가능한 정보")
print("=" * 60)
print(f"상가업소번호: {target_bizes_id}")
print()

service_key = SBIZConfig.get_service_key()
endpoint = "http://apis.data.go.kr/B553077/api/open/sdsc2/storeOne"

params = {
    'serviceKey': service_key,
    'key': target_bizes_id,
    'type': 'json'
}

try:
    response = requests.get(endpoint, params=params, timeout=30)
    print(f"HTTP 상태 코드: {response.status_code}")
    print()
    
    if response.status_code == 200:
        result = response.json()
        header = result.get('header', {})
        body = result.get('body', {})
        
        print("=" * 60)
        print("응답 헤더 정보")
        print("=" * 60)
        print(f"resultCode: {header.get('resultCode')}")
        print(f"resultMsg: {header.get('resultMsg')}")
        print(f"description: {header.get('description', 'N/A')}")
        print(f"기준년월 (stdrYm): {header.get('stdrYm', 'N/A')}")
        print()
        
        if header.get('resultCode') == '00':
            items = body.get('items', [])
            
            if items:
                store = items[0] if isinstance(items, list) else items
                
                print("=" * 60)
                print("상가업소 상세 정보")
                print("=" * 60)
                
                # 기본 정보
                print("\n【 기본 정보 】")
                print(f"  상가업소번호 (bizesId): {store.get('bizesId', 'N/A')}")
                print(f"  상호명 (bizesNm): {store.get('bizesNm', 'N/A')}")
                print(f"  지점명 (brchNm): {store.get('brchNm', 'N/A') or '(없음)'}")
                
                # 업종 정보
                print("\n【 업종 정보 】")
                print(f"  상권업종 대분류코드: {store.get('indsLclsCd', 'N/A')}")
                print(f"  상권업종 대분류명: {store.get('indsLclsNm', 'N/A')}")
                print(f"  상권업종 중분류코드: {store.get('indsMclsCd', 'N/A')}")
                print(f"  상권업종 중분류명: {store.get('indsMclsNm', 'N/A')}")
                print(f"  상권업종 소분류코드: {store.get('indsSclsCd', 'N/A')}")
                print(f"  상권업종 소분류명: {store.get('indsSclsNm', 'N/A')}")
                print(f"  표준산업분류코드 (ksicCd): {store.get('ksicCd', 'N/A')}")
                print(f"  표준산업분류명 (ksicNm): {store.get('ksicNm', 'N/A')}")
                
                # 위치 정보
                print("\n【 위치 정보 】")
                print(f"  시도코드: {store.get('ctprvnCd', 'N/A')}")
                print(f"  시도명: {store.get('ctprvnNm', 'N/A')}")
                print(f"  시군구코드: {store.get('signguCd', 'N/A')}")
                print(f"  시군구명: {store.get('signguNm', 'N/A')}")
                print(f"  행정동코드: {store.get('adongCd', 'N/A')}")
                print(f"  행정동명: {store.get('adongNm', 'N/A')}")
                print(f"  법정동코드: {store.get('ldongCd', 'N/A')}")
                print(f"  법정동명: {store.get('ldongNm', 'N/A')}")
                
                # 주소 정보
                print("\n【 주소 정보 】")
                print(f"  PNU코드 (lnoCd): {store.get('lnoCd', 'N/A')}")
                print(f"  지번본번지: {store.get('lnoMnno', 'N/A')}")
                print(f"  지번부번지: {store.get('lnoSlno', 'N/A')}")
                print(f"  지번주소 (lnoAdr): {store.get('lnoAdr', 'N/A')}")
                print(f"  도로명코드 (rdnmCd): {store.get('rdnmCd', 'N/A')}")
                print(f"  도로명 (rdnm): {store.get('rdnm', 'N/A')}")
                print(f"  건물본번지: {store.get('bldMnno', 'N/A')}")
                print(f"  건물부번지: {store.get('bldSlno', 'N/A')}")
                print(f"  건물관리번호 (bldMngNo): {store.get('bldMngNo', 'N/A')}")
                print(f"  건물명 (bldNm): {store.get('bldNm', 'N/A') or '(없음)'}")
                print(f"  도로명주소 (rdnmAdr): {store.get('rdnmAdr', 'N/A')}")
                print(f"  구우편번호: {store.get('oldZipcd', 'N/A')}")
                print(f"  신우편번호: {store.get('newZipcd', 'N/A')}")
                
                # 상세 위치 정보
                print("\n【 상세 위치 정보 】")
                print(f"  동정보 (dongNo): {store.get('dongNo', 'N/A') or '(없음)'}")
                print(f"  층정보 (flrNo): {store.get('flrNo', 'N/A') or '(없음)'}")
                print(f"  호정보 (hoNo): {store.get('hoNo', 'N/A') or '(없음)'}")
                
                # 좌표 정보
                print("\n【 좌표 정보 】")
                print(f"  경도 (lon): {store.get('lon', 'N/A')}")
                print(f"  위도 (lat): {store.get('lat', 'N/A')}")
                print(f"  좌표계: WGS84")
                
                # 전체 필드 목록
                print("\n" + "=" * 60)
                print("전체 필드 목록 (총 {}개)".format(len(store)))
                print("=" * 60)
                for key, value in sorted(store.items()):
                    value_str = str(value) if value else '(없음)'
                    if len(value_str) > 50:
                        value_str = value_str[:50] + "..."
                    print(f"  {key:20s}: {value_str}")
                
            else:
                print("✗ 상가업소 정보가 없습니다.")
                print(f"응답 내용: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")
        else:
            print(f"✗ API 오류: {header.get('resultMsg')}")
            print(f"응답 내용: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")
    else:
        print(f"✗ HTTP 오류: {response.status_code}")
        print(f"응답 내용: {response.text[:500]}")
        
except Exception as e:
    print(f"✗ 오류 발생: {e}")
    import traceback
    traceback.print_exc()

