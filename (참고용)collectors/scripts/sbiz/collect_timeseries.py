"""시계열 데이터 수집 - 개폐업일 추적을 위한 변경 이력 수집 (병렬 처리 지원)."""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.sbiz.api_client import SBIZAPIClient
from core.logger import get_logger
from core.file_handler import FileHandler

logger = get_logger(__name__)

# 전역 락 (스레드 안전성)
store_history_lock = Lock()




def collect_timeseries_data(
    start_date: str,
    end_date: str,
    target_bizes_ids: Set[str] = None,
    output_dir: Path = None,
    max_workers: int = 5,
    use_parallel: bool = True
) -> Dict[str, Dict]:
    """시계열 데이터 수집 - 특정 기간 동안 변경된 업소 추적.
    
    Args:
        start_date: 시작일 (YYYYMMDD)
        end_date: 종료일 (YYYYMMDD)
        target_bizes_ids: 추적할 업소 ID 집합 (None이면 모든 업소)
        output_dir: 출력 디렉토리
        
    Returns:
        {bizesId: {openDate, closeDate, changeHistory}} 형태의 딕셔너리
    """
    client = SBIZAPIClient()
    file_handler = FileHandler()
    
    if output_dir is None:
        output_dir = Path('data/raw/sbiz/timeseries')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 날짜 범위 생성
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    
    # 업소별 변경 이력 추적
    store_history: Dict[str, Dict] = {}
    
    # 월단위로 처리 (로그는 월단위, 실제 처리는 날짜별)
    current_date = start
    current_month_str = None
    month_store_count = 0
    processed_months = 0
    
    # 총 개월 수 계산
    total_months = (end.year - start.year) * 12 + (end.month - start.month) + 1
    
    logger.info(f"=" * 60)
    logger.info(f"시계열 데이터 수집 시작 (월단위 처리)")
    logger.info(f"  기간: {start_date} ~ {end_date} ({total_months}개월)")
    logger.info(f"  대상 업소: {len(target_bizes_ids) if target_bizes_ids else '전체'}")
    logger.info(f"  병렬 처리: {'활성화' if use_parallel else '비활성화'} (최대 {max_workers}개 스레드)")
    logger.info(f"=" * 60)
    
    # 모든 날짜 목록 생성
    all_dates = []
    current_date = start
    while current_date <= end:
        all_dates.append(current_date.strftime("%Y%m%d"))
        current_date += timedelta(days=1)
    
    logger.info(f"총 처리할 날짜 수: {len(all_dates):,}일")
    
    try:
        if use_parallel and len(all_dates) > 1:
            # 병렬 처리
            logger.info(f"병렬 처리 모드: {max_workers}개 스레드로 처리")
            from scripts.sbiz.collect_timeseries_parallel import _process_dates_parallel
            _process_dates_parallel(
                all_dates, target_bizes_ids, store_history, 
                output_dir, start, end, total_months, max_workers
            )
        else:
            # 순차 처리
            logger.info("순차 처리 모드")
            from scripts.sbiz.collect_timeseries_parallel import _process_dates_sequential
            _process_dates_sequential(
                all_dates, target_bizes_ids, store_history,
                output_dir, start, end, total_months
            )
        
        # 최종 저장
        logger.info(f"\n최종 데이터 저장 중...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"timeseries_{start_date}_{end_date}_{timestamp}.json"
        
        result = {
            'metadata': {
                'start_date': start_date,
                'end_date': end_date,
                'collected_at': datetime.now().isoformat(),
                'total_stores': len(store_history),
                'target_bizes_ids_count': len(target_bizes_ids) if target_bizes_ids else None
            },
            'store_history': store_history
        }
        
        file_handler.save_json(result, output_file)
        logger.info(f"✓ 시계열 데이터 저장: {output_file}")
        
        return store_history
        
    finally:
        client.close()


def _save_intermediate_result(store_history: Dict, output_dir: Path, date_str: str):
    """중간 결과 저장."""
    try:
        intermediate_file = output_dir / f"intermediate_{date_str}.json"
        with open(intermediate_file, 'w', encoding='utf-8') as f:
            json.dump(store_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"중간 저장 실패: {e}")


def merge_with_base_data(
    base_data_path: Path,
    timeseries_data: Dict[str, Dict],
    output_path: Path = None
) -> Dict:
    """기본 업소 데이터와 시계열 데이터 병합.
    
    Args:
        base_data_path: 기본 업소 데이터 JSON 파일 경로
        timeseries_data: 시계열 데이터 (collect_timeseries_data 반환값)
        output_path: 출력 파일 경로
        
    Returns:
        병합된 데이터
    """
    logger.info(f"기본 데이터와 시계열 데이터 병합 중...")
    
    # 기본 데이터 로드
    with open(base_data_path, 'r', encoding='utf-8') as f:
        base_data = json.load(f)
    
    stores = base_data.get('stores', [])
    logger.info(f"기본 업소 수: {len(stores):,}개")
    logger.info(f"시계열 데이터 업소 수: {len(timeseries_data):,}개")
    
    # 각 업소에 시계열 정보 추가
    merged_count = 0
    for store in stores:
        bizes_id = store.get('bizesId')
        if bizes_id and bizes_id in timeseries_data:
            history = timeseries_data[bizes_id]
            store['openDate'] = history.get('openDate')
            store['closeDate'] = history.get('closeDate')
            store['changeHistory'] = history.get('changeHistory', [])
            merged_count += 1
    
    logger.info(f"병합된 업소 수: {merged_count:,}개")
    
    # 메타데이터 업데이트
    metadata = base_data.get('metadata', {})
    metadata.update({
        'merged_at': datetime.now().isoformat(),
        'timeseries_merged': True,
        'merged_count': merged_count
    })
    
    merged_data = {
        'metadata': metadata,
        'stores': stores
    }
    
    # 저장
    if output_path:
        file_handler = FileHandler()
        file_handler.save_json(merged_data, output_path)
        logger.info(f"✓ 병합 데이터 저장: {output_path}")
    
    return merged_data


def main():
    """시계열 데이터 수집 메인 함수."""
    import argparse
    
    parser = argparse.ArgumentParser(description='시계열 데이터 수집')
    parser.add_argument('--start-date', type=str, required=True, help='시작일 (YYYYMMDD)')
    parser.add_argument('--end-date', type=str, required=True, help='종료일 (YYYYMMDD)')
    parser.add_argument('--target-file', type=str, help='대상 업소 ID가 포함된 JSON 파일 경로')
    parser.add_argument('--output-dir', type=str, help='출력 디렉토리')
    
    args = parser.parse_args()
    
    # 대상 업소 ID 로드
    target_bizes_ids = None
    if args.target_file:
        with open(args.target_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            stores = data.get('stores', [])
            target_bizes_ids = {s.get('bizesId') for s in stores if s.get('bizesId')}
            logger.info(f"대상 업소 수: {len(target_bizes_ids):,}개")
    
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    # 시계열 데이터 수집
    timeseries_data = collect_timeseries_data(
        start_date=args.start_date,
        end_date=args.end_date,
        target_bizes_ids=target_bizes_ids,
        output_dir=output_dir
    )
    
    logger.info(f"\n{'='*60}")
    logger.info("시계열 데이터 수집 완료!")
    logger.info(f"{'='*60}")
    logger.info(f"총 추적 업소 수: {len(timeseries_data):,}개")
    
    # 통계
    with_open = sum(1 for h in timeseries_data.values() if h.get('openDate'))
    with_close = sum(1 for h in timeseries_data.values() if h.get('closeDate'))
    logger.info(f"개업일 확인: {with_open:,}개")
    logger.info(f"폐업일 확인: {with_close:,}개")


if __name__ == "__main__":
    main()

