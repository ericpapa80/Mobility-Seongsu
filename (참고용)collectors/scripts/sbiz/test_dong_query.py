"""특정 상가업소의 행정동 단위 조회 결과 확인."""

import sys
from pathlib import Path
import requests
import json

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.scrapers.sbiz import SBIZConfig

# 대상 상가업소번호
target_bizes_id = "MA010120220800005385"
target_name = "법무사이두석사무소"

print("=" * 60)
print(f"상가업소: {target_name} ({target_bizes_id})")
print("=" * 60)

# 1. 먼저 단일 상가업소 조회로 행정동 코드 확인
print("\n1단계: 단일 상가업소 조회로 행정동 정보 확인")
print("-" * 60)

service_key = SBIZConfig.get_service_key()
store_one_endpoint = "http://apis.data.go.kr/B553077/api/open/sdsc2/storeOne"

params = {
    'serviceKey': service_key,
    'key': target_bizes_id,
    'type': 'json'
}

try:
    response = requests.get(store_one_endpoint, params=params, timeout=30)
    if response.status_code == 200:
        result = response.json()
        header = result.get('header', {})
        
        if header.get('resultCode') == '00':
            items = result.get('body', {}).get('items', [])
            if items:
                store_info = items[0]
                adong_cd = store_info.get('adongCd')
                adong_nm = store_info.get('adongNm')
                
                print(f"✓ 상가업소 정보 확인")
                print(f"  상호명: {store_info.get('bizesNm')}")
                print(f"  행정동코드: {adong_cd}")
                print(f"  행정동명: {adong_nm}")
                print(f"  주소: {store_info.get('lnoAdr')}")
                
                # 2. 행정동 단위 조회
                print(f"\n2단계: 행정동 단위 상가업소 조회 (행정동코드: {adong_cd})")
                print("-" * 60)
                
                dong_endpoint = "http://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong"
                dong_params = {
                    'serviceKey': service_key,
                    'divId': 'adongCd',
                    'key': adong_cd,
                    'numOfRows': 100,  # 처음 100개만 조회
                    'pageNo': 1,
                    'type': 'json'
                }
                
                dong_response = requests.get(dong_endpoint, params=dong_params, timeout=30)
                if dong_response.status_code == 200:
                    dong_result = dong_response.json()
                    dong_header = dong_result.get('header', {})
                    
                    if dong_header.get('resultCode') == '00':
                        dong_body = dong_result.get('body', {})
                        dong_items = dong_body.get('items', [])
                        total_count = dong_body.get('totalCount', 0)
                        
                        print(f"✓ 행정동 단위 조회 성공")
                        print(f"  행정동: {adong_nm} (코드: {adong_cd})")
                        print(f"  총 업소 수: {total_count:,}개")
                        print(f"  조회된 업소 수: {len(dong_items)}개 (페이지당)")
                        
                        # 대상 업소 찾기
                        target_found = False
                        target_index = -1
                        
                        for i, item in enumerate(dong_items):
                            if item.get('bizesId') == target_bizes_id:
                                target_found = True
                                target_index = i
                                break
                        
                        if target_found:
                            print(f"\n✓ 대상 업소 발견!")
                            print(f"  목록 내 위치: {target_index + 1}번째")
                            print(f"  상호명: {dong_items[target_index].get('bizesNm')}")
                            print(f"  주소: {dong_items[target_index].get('lnoAdr')}")
                        else:
                            print(f"\n⚠ 대상 업소가 이 페이지에 없음 (다른 페이지에 있을 수 있음)")
                        
                        # 처음 10개 업소 목록
                        print(f"\n3단계: 행정동 내 상가업소 목록 (처음 10개)")
                        print("-" * 60)
                        for i, item in enumerate(dong_items[:10], 1):
                            marker = " ← 대상" if item.get('bizesId') == target_bizes_id else ""
                            print(f"{i:3d}. {item.get('bizesId')} - {item.get('bizesNm')} ({item.get('adongNm')}){marker}")
                        
                        # 전체 목록에서 대상 업소 찾기 (모든 페이지 검색)
                        print(f"\n4단계: 전체 목록에서 대상 업소 검색")
                        print("-" * 60)
                        print(f"총 {total_count:,}개 업소 중 검색 중...")
                        
                        all_pages_found = False
                        found_page = -1
                        found_index = -1
                        
                        # 최대 10페이지까지만 검색 (성능 고려)
                        max_pages = min(10, (total_count // 100) + 1)
                        
                        for page in range(1, max_pages + 1):
                            dong_params['pageNo'] = page
                            page_response = requests.get(dong_endpoint, params=dong_params, timeout=30)
                            
                            if page_response.status_code == 200:
                                page_result = page_response.json()
                                if page_result.get('header', {}).get('resultCode') == '00':
                                    page_items = page_result.get('body', {}).get('items', [])
                                    
                                    for idx, item in enumerate(page_items):
                                        if item.get('bizesId') == target_bizes_id:
                                            all_pages_found = True
                                            found_page = page
                                            found_index = idx
                                            break
                                    
                                    if all_pages_found:
                                        break
                        
                        if all_pages_found:
                            print(f"✓ 전체 목록에서 발견!")
                            print(f"  페이지: {found_page}페이지")
                            print(f"  페이지 내 위치: {found_index + 1}번째")
                            print(f"  전체 목록 내 대략적 위치: 약 {((found_page - 1) * 100) + found_index + 1}번째")
                        else:
                            print(f"⚠ 처음 {max_pages}페이지 내에서 발견되지 않음")
                            print(f"  (총 {total_count:,}개 중 검색했으므로 더 뒤에 있을 수 있음)")
                    else:
                        print(f"✗ 행정동 조회 오류: {dong_header.get('resultMsg')}")
                else:
                    print(f"✗ HTTP 오류: {dong_response.status_code}")
            else:
                print(f"✗ 상가업소 정보 없음")
        else:
            print(f"✗ API 오류: {header.get('resultMsg')}")
    else:
        print(f"✗ HTTP 오류: {response.status_code}")
        
except Exception as e:
    print(f"✗ 오류 발생: {e}")
    import traceback
    traceback.print_exc()

