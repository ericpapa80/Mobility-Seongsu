# -*- coding: utf-8 -*-
"""웹 검색을 활용하여 성수동 지역 외 좌표를 재지오코딩하는 스크립트"""

import sys
import argparse
from pathlib import Path
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import re

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from plugins.nps.geocoder import Geocoder
from core.logger import get_logger

logger = get_logger(__name__)

# 성수동 지역 좌표 범위 (약간 넓힌 범위로 경계선 근처 포함)
SEONGSU_X_MIN, SEONGSU_X_MAX = 127.03, 127.08  # 기존: 127.04 ~ 127.07
SEONGSU_Y_MIN, SEONGSU_Y_MAX = 37.53, 37.56    # 기존: 37.54 ~ 37.55


def is_in_seongsu(x: float, y: float) -> bool:
    """좌표가 성수동 지역 내에 있는지 확인"""
    if pd.isna(x) or pd.isna(y):
        return False
    try:
        x_val = float(x)
        y_val = float(y)
        return (SEONGSU_X_MIN <= x_val <= SEONGSU_X_MAX and 
                SEONGSU_Y_MIN <= y_val <= SEONGSU_Y_MAX)
    except (ValueError, TypeError):
        return False


def enhance_address(address: str, business_name: str = None) -> list:
    """주소를 다양한 형태로 보완하여 리스트로 반환
    
    Args:
        address: 원본 주소
        business_name: 사업장명
        
    Returns:
        보완된 주소 리스트
    """
    if not address or pd.isna(address) or str(address).strip() == 'nan':
        return []
    
    address = str(address).strip()
    enhanced = []
    
    # 원본 주소
    enhanced.append(address)
    
    # "서울시 성동구 성수동" 추가 (다양한 형태)
    if "서울" not in address:
        enhanced.append(f"서울시 성동구 성수동 {address}")
        enhanced.append(f"서울 성동구 성수동 {address}")
    if "성동구" not in address and "서울" in address:
        enhanced.append(f"서울시 성동구 성수동 {address}")
        enhanced.append(f"서울 성동구 성수동 {address}")
    if "성수동" not in address and "성동구" in address:
        enhanced.append(f"{address} 성수동")
        # 성수동1가, 성수동2가 추가
        enhanced.append(f"{address} 성수동1가")
        enhanced.append(f"{address} 성수동2가")
    
    # 주소를 부분적으로 나누어 시도
    parts = address.split()
    if len(parts) > 1:
        # 마지막 부분 제거 (번지가 잘못되었을 수 있음)
        enhanced.append(" ".join(parts[:-1]))
        # 처음 3개 부분만 사용
        if len(parts) >= 3:
            enhanced.append(" ".join(parts[:3]))
        # 처음 2개 부분만 사용
        if len(parts) >= 2:
            enhanced.append(" ".join(parts[:2]))
    
    # 상호명과 함께 (더 다양한 조합)
    if business_name and not pd.isna(business_name):
        business_name = str(business_name).strip()
        if business_name and business_name != 'nan':
            # 성수동 포함
            enhanced.append(f"{business_name} 성수동")
            enhanced.append(f"{business_name} 서울시 성동구 성수동")
            enhanced.append(f"{business_name} 서울 성동구 성수동")
            enhanced.append(f"{business_name} {address}")
            enhanced.append(f"서울시 성동구 성수동 {business_name}")
            enhanced.append(f"서울 성동구 성수동 {business_name}")
            # 성수동1가, 성수동2가 포함
            enhanced.append(f"{business_name} 성수동1가")
            enhanced.append(f"{business_name} 성수동2가")
            enhanced.append(f"{business_name} 서울시 성동구 성수동1가")
            enhanced.append(f"{business_name} 서울시 성동구 성수동2가")
    
    # 중복 제거
    return list(dict.fromkeys(enhanced))


# Thread-safe 카운터
class Counter:
    def __init__(self):
        self.lock = threading.Lock()
        self.success = 0
        self.fail = 0
        self.naver_success = 0
        self.kakao_success = 0
        self.vworld_success = 0
        self.completed = 0
    
    def increment_success(self, service="Unknown"):
        with self.lock:
            self.success += 1
            self.completed += 1
            if service == "Naver":
                self.naver_success += 1
            elif service == "Kakao":
                self.kakao_success += 1
            elif service == "Vworld":
                self.vworld_success += 1
    
    def increment_fail(self):
        with self.lock:
            self.fail += 1
            self.completed += 1
    
    def get_stats(self):
        with self.lock:
            return {
                'success': self.success,
                'fail': self.fail,
                'naver_success': self.naver_success,
                'kakao_success': self.kakao_success,
                'vworld_success': self.vworld_success,
                'completed': self.completed
            }


def geocode_with_enhanced_addresses(args):
    """보완된 주소로 지오코딩 시도
    
    Args:
        args: (idx, row, geocoding_delay) 튜플
        
    Returns:
        (idx, coords, service_used, business_name, address_str) 튜플
    """
    idx, row, geocoding_delay = args
    
    address = row.get('주소', '')
    business_name = row.get('사업장명', '')
    jibun_address = row.get('사업장지번상세주소', '')
    
    # 주소 선택
    if pd.isna(address) or not str(address).strip() or str(address).strip() == 'nan':
        if pd.isna(jibun_address) or not str(jibun_address).strip() or str(jibun_address).strip() == 'nan':
            return (idx, None, None, business_name, None)
        address = jibun_address
    
    address_str = str(address).strip()
    business_name_str = str(business_name).strip() if not pd.isna(business_name) and str(business_name).strip() != 'nan' else None
    
    if not address_str or address_str == 'nan':
        return (idx, None, None, business_name_str, None)
    
    # 보완된 주소 리스트 생성
    enhanced_addresses = enhance_address(address_str, business_name_str)
    
    # 각 보완된 주소로 시도
    for enhanced_addr in enhanced_addresses:
        # Strategy 1: Kakao API
        try:
            kakao_geocoder = Geocoder(service="kakao")
            coords = kakao_geocoder.geocode(enhanced_addr, keyword=business_name_str, delay=geocoding_delay)
            if coords and is_in_seongsu(coords.get('x') or coords.get('lon'), coords.get('y') or coords.get('lat')):
                kakao_geocoder.close()
                return (idx, coords, "Kakao", business_name_str, enhanced_addr)
            kakao_geocoder.close()
        except Exception as e:
            logger.debug(f"Kakao geocoding failed: {e}")
        
        # Strategy 2: Naver API
        try:
            naver_geocoder = Geocoder(service="naver")
            coords = naver_geocoder.geocode(enhanced_addr, keyword=business_name_str, delay=geocoding_delay)
            if coords and is_in_seongsu(coords.get('x') or coords.get('lon'), coords.get('y') or coords.get('lat')):
                naver_geocoder.close()
                return (idx, coords, "Naver", business_name_str, enhanced_addr)
            naver_geocoder.close()
        except Exception as e:
            logger.debug(f"Naver geocoding failed: {e}")
        
        # Strategy 3: Vworld API
        try:
            vworld_geocoder = Geocoder(service="vworld")
            coords = vworld_geocoder.geocode(enhanced_addr, delay=geocoding_delay)
            if coords and is_in_seongsu(coords.get('x') or coords.get('lon'), coords.get('y') or coords.get('lat')):
                vworld_geocoder.close()
                return (idx, coords, "Vworld", business_name_str, enhanced_addr)
            vworld_geocoder.close()
        except Exception as e:
            logger.debug(f"Vworld geocoding failed: {e}")
    
    # 모든 전략 실패
    return (idx, None, None, business_name_str, address_str)


def regeocode_with_web_search(csv_path: str, output_path: str = None, geocoding_delay: float = 0.1, workers: int = 10):
    """웹 검색 전략을 활용하여 성수동 지역 외 좌표를 재지오코딩
    
    Args:
        csv_path: 원본 CSV 파일 경로
        output_path: 출력 CSV 파일 경로
        geocoding_delay: API 호출 간 지연 시간 (초)
        workers: 병렬 처리 워커 수
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {csv_path}")
        return
    
    print("=" * 80)
    print("웹 검색 전략을 활용한 성수동 지역 외 좌표 재지오코딩")
    print("=" * 80)
    print(f"입력 파일: {csv_path}")
    print(f"병렬 워커 수: {workers}개")
    
    # CSV 파일 읽기
    print("\nCSV 파일 로딩 중...")
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"전체 레코드: {len(df):,}개")
    
    # 성수동 지역 외 좌표 필터링
    coords_df = df[df['x'].notna() & df['y'].notna()]
    outside_seongsu = coords_df[
        ~((coords_df['x'] >= SEONGSU_X_MIN) & (coords_df['x'] <= SEONGSU_X_MAX) &
          (coords_df['y'] >= SEONGSU_Y_MIN) & (coords_df['y'] <= SEONGSU_Y_MAX))
    ]
    
    print(f"\n좌표가 있는 레코드: {len(coords_df):,}개")
    print(f"성수동 지역 내: {len(coords_df) - len(outside_seongsu):,}개")
    print(f"성수동 지역 외 (재지오코딩 대상): {len(outside_seongsu):,}개")
    
    if len(outside_seongsu) == 0:
        print("\n✅ 모든 좌표가 성수동 지역 내에 있습니다!")
        return
    
    counter = Counter()
    
    print("\n재지오코딩 시작 (주소 보완 전략 사용)...")
    print("전략: 주소를 다양한 형태로 보완하여 성수동 지역 내 좌표를 찾습니다.\n")
    
    total = len(outside_seongsu)
    start_time = time.time()
    
    # 병렬 처리 준비
    tasks = [(idx, row, geocoding_delay) for idx, row in outside_seongsu.iterrows()]
    
    # ThreadPoolExecutor로 병렬 처리
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_idx = {executor.submit(geocode_with_enhanced_addresses, task): task[0] for task in tasks}
        
        for future in as_completed(future_to_idx):
            try:
                idx, coords, service_used, business_name, address_str = future.result()
                
                if coords and is_in_seongsu(coords.get('x') or coords.get('lon'), coords.get('y') or coords.get('lat')):
                    df.at[idx, 'x'] = coords.get('x') or coords.get('lon')
                    df.at[idx, 'y'] = coords.get('y') or coords.get('lat')
                    counter.increment_success(service_used)
                else:
                    counter.increment_fail()
                
                # 진행 상황 출력
                stats = counter.get_stats()
                if stats['completed'] % 10 == 0 or stats['completed'] == total:
                    elapsed = time.time() - start_time
                    progress_pct = (stats['completed'] / total) * 100
                    rate = stats['completed'] / elapsed if elapsed > 0 else 0
                    remaining = (total - stats['completed']) / rate if rate > 0 else 0
                    
                    print(f"[{stats['completed']}/{total} ({progress_pct:.1f}%)] "
                          f"성공: {stats['success']} (Naver: {stats['naver_success']}, "
                          f"Kakao: {stats['kakao_success']}, Vworld: {stats['vworld_success']}), "
                          f"실패: {stats['fail']} | "
                          f"속도: {rate:.1f}개/초, 예상 남은 시간: {remaining/60:.1f}분")
                
            except Exception as e:
                idx = future_to_idx[future]
                logger.error(f"Error processing record {idx}: {e}")
                counter.increment_fail()
    
    elapsed_time = time.time() - start_time
    stats = counter.get_stats()
    
    # 최종 결과 확인
    coords_df_final = df[df['x'].notna() & df['y'].notna()]
    in_seongsu_final = coords_df_final[
        (coords_df_final['x'] >= SEONGSU_X_MIN) & (coords_df_final['x'] <= SEONGSU_X_MAX) &
        (coords_df_final['y'] >= SEONGSU_Y_MIN) & (coords_df_final['y'] <= SEONGSU_Y_MAX)
    ]
    
    print("\n" + "=" * 80)
    print("재지오코딩 완료")
    print("=" * 80)
    print(f"처리 대상: {total}개")
    print(f"소요 시간: {elapsed_time/60:.1f}분 ({elapsed_time:.1f}초)")
    print(f"평균 속도: {total/elapsed_time:.1f}개/초")
    print(f"\n성공: {stats['success']}개 ({stats['success']/total*100:.1f}%)")
    print(f"  - Naver API 성공: {stats['naver_success']}개")
    print(f"  - Kakao API 성공: {stats['kakao_success']}개")
    print(f"  - Vworld API 성공: {stats['vworld_success']}개")
    print(f"실패: {stats['fail']}개 ({stats['fail']/total*100:.1f}%)")
    
    print(f"\n최종 결과:")
    print(f"  전체 좌표: {len(coords_df_final):,}개")
    print(f"  성수동 지역 내: {len(in_seongsu_final):,}개 ({len(in_seongsu_final)/len(coords_df_final)*100:.1f}%)")
    print(f"  성수동 지역 외: {len(coords_df_final) - len(in_seongsu_final):,}개")
    
    # 결과 저장
    if output_path is None:
        output_path = csv_path
    else:
        output_path = Path(output_path)
    
    print(f"\n결과 저장 중: {output_path}")
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print("✅ 저장 완료!")


def main():
    parser = argparse.ArgumentParser(description='웹 검색 전략을 활용하여 성수동 지역 외 좌표를 재지오코딩')
    parser.add_argument('csv_path', help='CSV 파일 경로')
    parser.add_argument('--output', '-o', help='출력 CSV 파일 경로 (없으면 원본 덮어쓰기)')
    parser.add_argument('--geocoding-delay', type=float, default=0.1,
                       help='지오코딩 API 호출 간 지연 시간(초)')
    parser.add_argument('--workers', '-w', type=int, default=10,
                       help='병렬 처리 워커 수 (기본값: 10)')
    
    args = parser.parse_args()
    
    regeocode_with_web_search(
        csv_path=args.csv_path,
        output_path=args.output,
        geocoding_delay=args.geocoding_delay,
        workers=args.workers
    )


if __name__ == "__main__":
    main()

