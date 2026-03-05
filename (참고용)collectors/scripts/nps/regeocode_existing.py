# -*- coding: utf-8 -*-
"""기존 수집 데이터의 지오코딩만 다시 수행하는 스크립트"""

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
        self.kakao_success = 0
        self.naver_success = 0
        self.completed = 0
    
    def increment_success(self, service="Unknown"):
        with self.lock:
            self.success += 1
            self.completed += 1
            if service == "Kakao":
                self.kakao_success += 1
            elif service == "Naver":
                self.naver_success += 1
    
    def increment_fail(self):
        with self.lock:
            self.fail += 1
            self.completed += 1
    
    def get_stats(self):
        with self.lock:
            return {
                'success': self.success,
                'fail': self.fail,
                'kakao_success': self.kakao_success,
                'naver_success': self.naver_success,
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
    
    business_name_str = str(business_name).strip() if not pd.isna(business_name) and str(business_name).strip() != 'nan' else None
    
    coords = None
    service_used = None
    
    # Strategy 1: Kakao API (상호명 + 주소) - 우선순위 1
    if business_name_str:
        try:
            kakao_geocoder = Geocoder(service="kakao")
            coords = kakao_geocoder.geocode(address_str, keyword=business_name_str, delay=geocoding_delay)
            if coords:
                service_used = "Kakao"
            kakao_geocoder.close()
            if coords:
                return (idx, coords, service_used, business_name_str, address_str)
        except Exception as e:
            logger.debug(f"Kakao geocoding failed: {e}")
    
    # Strategy 2: Naver API (상호명 + 주소) - 우선순위 2
    if business_name_str:
        try:
            naver_geocoder = Geocoder(service="naver")
            coords = naver_geocoder.geocode(address_str, keyword=business_name_str, delay=geocoding_delay)
            if coords:
                service_used = "Naver"
            naver_geocoder.close()
            if coords:
                return (idx, coords, service_used, business_name_str, address_str)
        except Exception as e:
            logger.debug(f"Naver geocoding failed: {e}")
    
    # Strategy 3: Kakao API (주소만)
    try:
        kakao_geocoder = Geocoder(service="kakao")
        coords = kakao_geocoder.geocode(address_str, delay=geocoding_delay)
        if coords:
            service_used = "Kakao"
        kakao_geocoder.close()
        if coords:
            return (idx, coords, service_used, business_name_str, address_str)
    except Exception as e:
        logger.debug(f"Kakao address-only geocoding failed: {e}")
    
    # Strategy 4: Naver API (주소만)
    try:
        naver_geocoder = Geocoder(service="naver")
        coords = naver_geocoder.geocode(address_str, delay=geocoding_delay)
        if coords:
            service_used = "Naver"
        naver_geocoder.close()
        if coords:
            return (idx, coords, service_used, business_name_str, address_str)
    except Exception as e:
        logger.debug(f"Naver address-only geocoding failed: {e}")
    
    # 모든 전략 실패
    return (idx, None, None, business_name_str, address_str)


def regeocode_existing(csv_path: str, output_path: str = None, geocoding_delay: float = 0.1, workers: int = 10):
    """기존 CSV 파일의 지오코딩만 다시 수행
    
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
    print("기존 데이터 지오코딩 재수행 (카카오/네이버 우선)")
    print("=" * 80)
    print(f"입력 파일: {csv_path}")
    print(f"병렬 워커 수: {workers}개")
    
    # CSV 파일 읽기
    print("\nCSV 파일 로딩 중...")
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"전체 레코드: {len(df):,}개")
    
    # 좌표 컬럼 초기화 (x, y만 사용)
    df['x'] = None
    df['y'] = None
    
    # 기존 lon/lat 컬럼이 있으면 제거 (선택사항)
    if 'lon' in df.columns:
        df = df.drop(columns=['lon'])
    if 'lat' in df.columns:
        df = df.drop(columns=['lat'])
    
    counter = Counter()
    
    print("\n지오코딩 시작 (카카오/네이버 우선순위, 병렬 처리)...")
    print("전략: 카카오(상호명+주소) → 네이버(상호명+주소) → 카카오(주소) → 네이버(주소)\n")
    
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
                    df.at[idx, 'x'] = coords.get('x') or coords.get('lon')
                    df.at[idx, 'y'] = coords.get('y') or coords.get('lat')
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
                          f"성공: {stats['success']} (Kakao: {stats['kakao_success']}, "
                          f"Naver: {stats['naver_success']}), 실패: {stats['fail']} | "
                          f"속도: {rate:.1f}개/초, 예상 남은 시간: {remaining/60:.1f}분")
                
            except Exception as e:
                idx = future_to_idx[future]
                logger.error(f"Error processing record {idx}: {e}")
                counter.increment_fail()
    
    elapsed_time = time.time() - start_time
    stats = counter.get_stats()
    
    print("\n" + "=" * 80)
    print("지오코딩 완료")
    print("=" * 80)
    print(f"전체 레코드: {total}개")
    print(f"소요 시간: {elapsed_time/60:.1f}분 ({elapsed_time:.1f}초)")
    print(f"평균 속도: {total/elapsed_time:.1f}개/초")
    print(f"\n성공: {stats['success']}개 ({stats['success']/total*100:.1f}%)")
    print(f"  - Kakao API 성공: {stats['kakao_success']}개")
    print(f"  - Naver API 성공: {stats['naver_success']}개")
    print(f"실패: {stats['fail']}개 ({stats['fail']/total*100:.1f}%)")
    
    # 좌표 통계
    coords_df = df[df['x'].notna() & df['y'].notna()]
    if len(coords_df) > 0:
        print(f"\n좌표 범위:")
        print(f"  경도(x): {coords_df['x'].min():.6f} ~ {coords_df['x'].max():.6f}")
        print(f"  위도(y): {coords_df['y'].min():.6f} ~ {coords_df['y'].max():.6f}")
    
    # 결과 저장
    if output_path is None:
        output_path = csv_path
    else:
        output_path = Path(output_path)
    
    print(f"\n결과 저장 중: {output_path}")
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print("✅ 저장 완료!")


def main():
    parser = argparse.ArgumentParser(description='기존 수집 데이터의 지오코딩만 다시 수행')
    parser.add_argument('csv_path', help='CSV 파일 경로')
    parser.add_argument('--output', '-o', help='출력 CSV 파일 경로 (없으면 원본 덮어쓰기)')
    parser.add_argument('--geocoding-delay', type=float, default=0.1,
                       help='지오코딩 API 호출 간 지연 시간(초)')
    parser.add_argument('--workers', '-w', type=int, default=10,
                       help='병렬 처리 워커 수 (기본값: 10)')
    
    args = parser.parse_args()
    
    regeocode_existing(
        csv_path=args.csv_path,
        output_path=args.output,
        geocoding_delay=args.geocoding_delay,
        workers=args.workers
    )


if __name__ == "__main__":
    main()

