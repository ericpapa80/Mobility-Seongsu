# -*- coding: utf-8 -*-
"""Vworld API를 사용하여 모든 레코드를 다시 지오코딩하는 스크립트"""

import sys
import argparse
from pathlib import Path
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from plugins.nps.geocoder import Geocoder
from core.logger import get_logger

logger = get_logger(__name__)


# Thread-safe 카운터
class Counter:
    def __init__(self):
        self.lock = threading.Lock()
        self.success = 0
        self.fail = 0
        self.vworld_success = 0
        self.kakao_fallback_success = 0
        self.completed = 0
    
    def increment_success(self, service="Vworld"):
        with self.lock:
            self.success += 1
            self.completed += 1
            if service == "Vworld":
                self.vworld_success += 1
            else:
                self.kakao_fallback_success += 1
    
    def increment_fail(self):
        with self.lock:
            self.fail += 1
            self.completed += 1
    
    def get_stats(self):
        with self.lock:
            return {
                'success': self.success,
                'fail': self.fail,
                'vworld_success': self.vworld_success,
                'kakao_fallback_success': self.kakao_fallback_success,
                'completed': self.completed
            }


def geocode_record(args):
    """단일 레코드를 지오코딩하는 함수 (병렬 처리용)
    
    Args:
        args: (idx, row, geocoding_delay) 튜플
        
    Returns:
        (idx, coords, service_used, business_name, address_str) 튜플
    """
    idx, row, geocoding_delay = args
    
    address = row.get('주소', '')
    business_name = row.get('사업장명', '')
    jibun_address = row.get('사업장지번상세주소', '')
    
    # 주소 선택: 주소가 없으면 사업장지번상세주소 사용
    if pd.isna(address) or not str(address).strip() or str(address).strip() == 'nan':
        if pd.isna(jibun_address) or not str(jibun_address).strip() or str(jibun_address).strip() == 'nan':
            return (idx, None, None, business_name, None)
        address = jibun_address
    
    address_str = str(address).strip()
    
    if not address_str or address_str == 'nan':
        return (idx, None, None, business_name, None)
    
    # 각 스레드마다 독립적인 Geocoder 인스턴스 생성
    geocoder = Geocoder(service="vworld")
    service_used = "Vworld"
    
    # Vworld API로 지오코딩
    coords = geocoder.geocode(address_str, delay=geocoding_delay)
    
    # Vworld 실패 시 상호명과 함께 카카오로 재시도
    if not coords and business_name and not pd.isna(business_name):
        keyword = str(business_name).strip()
        if keyword and keyword != 'nan':
            try:
                kakao_geocoder = Geocoder(service="kakao")
                coords = kakao_geocoder.geocode(address_str, keyword=keyword, delay=geocoding_delay)
                if coords:
                    service_used = "Kakao(폴백)"
                kakao_geocoder.close()
            except Exception as e:
                logger.debug(f"Kakao fallback failed: {e}")
    
    # 여전히 실패 시 최종 카카오 재시도
    if not coords and business_name and not pd.isna(business_name):
        try:
            kakao_geocoder = Geocoder(service="kakao")
            keyword = str(business_name).strip()
            coords = kakao_geocoder.geocode(address_str, keyword=keyword, delay=geocoding_delay)
            if coords:
                service_used = "Kakao(폴백)"
            kakao_geocoder.close()
        except Exception as e:
            logger.debug(f"Kakao final fallback failed: {e}")
    
    geocoder.close()
    
    return (idx, coords, service_used, business_name, address_str)


def regeocode_with_vworld(csv_path: str, output_path: str = None, geocoding_delay: float = 0.1, workers: int = 10):
    """Vworld API를 사용하여 모든 레코드를 병렬로 다시 지오코딩
    
    Args:
        csv_path: 원본 CSV 파일 경로
        output_path: 출력 CSV 파일 경로 (없으면 원본 파일 덮어쓰기)
        geocoding_delay: API 호출 간 지연 시간 (초)
        workers: 병렬 처리 워커 수 (기본값: 10)
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {csv_path}")
        return
    
    print("=" * 80)
    print("Vworld API를 사용한 병렬 재지오코딩")
    print("=" * 80)
    print(f"입력 파일: {csv_path}")
    print(f"병렬 워커 수: {workers}개")
    
    # CSV 파일 읽기
    print("\nCSV 파일 로딩 중...")
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"전체 레코드: {len(df):,}개")
    
    # 모든 레코드 좌표 초기화
    df['x'] = None
    df['y'] = None
    df['lon'] = None
    df['lat'] = None
    
    counter = Counter()
    
    print("\n지오코딩 시작 (병렬 처리)...")
    print("상호명과 주소를 함께 사용하여 더 정확한 위치를 찾습니다.\n")
    
    total = len(df)
    start_time = time.time()
    
    # 병렬 처리 준비
    tasks = [(idx, row, geocoding_delay) for idx, row in df.iterrows()]
    
    # ThreadPoolExecutor로 병렬 처리
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # 모든 작업 제출
        future_to_idx = {executor.submit(geocode_record, task): task[0] for task in tasks}
        
        # 완료된 작업 처리
        for future in as_completed(future_to_idx):
            try:
                idx, coords, service_used, business_name, address_str = future.result()
                
                if coords:
                    df.at[idx, 'x'] = coords.get('x')
                    df.at[idx, 'y'] = coords.get('y')
                    df.at[idx, 'lon'] = coords.get('lon')
                    df.at[idx, 'lat'] = coords.get('lat')
                    counter.increment_success(service_used)
                else:
                    counter.increment_fail()
                
                # 진행 상황 출력 (10개마다)
                stats = counter.get_stats()
                if stats['completed'] % 10 == 0 or stats['completed'] == total:
                    elapsed = time.time() - start_time
                    progress_pct = (stats['completed'] / total) * 100
                    rate = stats['completed'] / elapsed if elapsed > 0 else 0
                    remaining = (total - stats['completed']) / rate if rate > 0 else 0
                    
                    print(f"[{stats['completed']}/{total} ({progress_pct:.1f}%)] "
                          f"성공: {stats['success']} (Vworld: {stats['vworld_success']}, "
                          f"Kakao: {stats['kakao_fallback_success']}), 실패: {stats['fail']} | "
                          f"속도: {rate:.1f}개/초, 예상 남은 시간: {remaining/60:.1f}분")
                
            except Exception as e:
                idx = future_to_idx[future]
                logger.error(f"Error processing record {idx}: {e}")
                counter.increment_fail()
    
    elapsed_time = time.time() - start_time
    stats = counter.get_stats()
    
    print("\n" + "=" * 80)
    print("재지오코딩 완료")
    print("=" * 80)
    print(f"전체 레코드: {total}개")
    print(f"소요 시간: {elapsed_time/60:.1f}분 ({elapsed_time:.1f}초)")
    print(f"평균 속도: {total/elapsed_time:.1f}개/초")
    print(f"\n성공: {stats['success']}개 ({stats['success']/total*100:.1f}%)")
    print(f"  - Vworld API 성공: {stats['vworld_success']}개")
    print(f"  - Kakao API 폴백 성공: {stats['kakao_fallback_success']}개")
    print(f"실패: {stats['fail']}개 ({stats['fail']/total*100:.1f}%)")
    
    # 좌표 범위 확인
    coords_df = df[df['x'].notna() & df['y'].notna()]
    if len(coords_df) > 0:
        print(f"\n좌표 범위:")
        print(f"  경도(x): {coords_df['x'].min():.6f} ~ {coords_df['x'].max():.6f}")
        print(f"  위도(y): {coords_df['y'].min():.6f} ~ {coords_df['y'].max():.6f}")
        
        # 성수동 지역 좌표 범위 확인 (대략적인 범위)
        seongsu_x_min, seongsu_x_max = 127.04, 127.07  # 성수동 경도 범위
        seongsu_y_min, seongsu_y_max = 37.54, 37.55    # 성수동 위도 범위
        
        in_seongsu = coords_df[
            (coords_df['x'] >= seongsu_x_min) & (coords_df['x'] <= seongsu_x_max) &
            (coords_df['y'] >= seongsu_y_min) & (coords_df['y'] <= seongsu_y_max)
        ]
        print(f"\n성수동 지역 내 좌표: {len(in_seongsu)}개 ({len(in_seongsu)/len(coords_df)*100:.1f}%)")
        print(f"성수동 지역 외 좌표: {len(coords_df) - len(in_seongsu)}개")
    
    # 결과 저장
    if output_path is None:
        output_path = csv_path
    else:
        output_path = Path(output_path)
    
    print(f"\n결과 저장 중: {output_path}")
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print("✅ 저장 완료!")


def main():
    parser = argparse.ArgumentParser(description='Vworld API를 사용하여 모든 레코드를 병렬로 다시 지오코딩')
    parser.add_argument('csv_path', help='CSV 파일 경로')
    parser.add_argument('--output', '-o', help='출력 CSV 파일 경로 (없으면 원본 덮어쓰기)')
    parser.add_argument('--geocoding-delay', type=float, default=0.1,
                       help='지오코딩 API 호출 간 지연 시간(초)')
    parser.add_argument('--workers', '-w', type=int, default=10,
                       help='병렬 처리 워커 수 (기본값: 10)')
    
    args = parser.parse_args()
    
    regeocode_with_vworld(
        csv_path=args.csv_path,
        output_path=args.output,
        geocoding_delay=args.geocoding_delay,
        workers=args.workers
    )


if __name__ == "__main__":
    main()

