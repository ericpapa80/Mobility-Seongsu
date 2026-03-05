"""기본 업소 데이터와 시계열 데이터 병합 스크립트."""

import sys
from pathlib import Path
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.logger import get_logger
from core.file_handler import FileHandler

logger = get_logger(__name__)


def merge_timeseries_with_base(
    base_json_path: Path,
    timeseries_json_path: Path,
    output_path: Path = None
) -> dict:
    """기본 업소 데이터와 시계열 데이터 병합.
    
    Args:
        base_json_path: 기본 업소 데이터 JSON 파일 경로
        timeseries_json_path: 시계열 데이터 JSON 파일 경로
        output_path: 출력 파일 경로 (None이면 자동 생성)
        
    Returns:
        병합된 데이터
    """
    logger.info(f"=" * 60)
    logger.info(f"데이터 병합 시작")
    logger.info(f"  기본 데이터: {base_json_path}")
    logger.info(f"  시계열 데이터: {timeseries_json_path}")
    logger.info(f"=" * 60)
    
    # 기본 데이터 로드
    logger.info("기본 데이터 로드 중...")
    with open(base_json_path, 'r', encoding='utf-8') as f:
        base_data = json.load(f)
    
    stores = base_data.get('stores', [])
    logger.info(f"기본 업소 수: {len(stores):,}개")
    
    # 시계열 데이터 로드
    logger.info("시계열 데이터 로드 중...")
    with open(timeseries_json_path, 'r', encoding='utf-8') as f:
        timeseries_data = json.load(f)
    
    store_history = timeseries_data.get('store_history', {})
    logger.info(f"시계열 데이터 업소 수: {len(store_history):,}개")
    
    # 각 업소에 시계열 정보 추가
    logger.info("데이터 병합 중...")
    merged_count = 0
    for store in stores:
        bizes_id = store.get('bizesId')
        if bizes_id and bizes_id in store_history:
            history = store_history[bizes_id]
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
        'timeseries_source': str(timeseries_json_path.name),
        'merged_count': merged_count,
        'total_with_open_date': sum(1 for s in stores if s.get('openDate')),
        'total_with_close_date': sum(1 for s in stores if s.get('closeDate'))
    })
    
    merged_data = {
        'metadata': metadata,
        'stores': stores
    }
    
    # 출력 경로 자동 생성
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = base_json_path.stem
        output_path = base_json_path.parent / f"{base_name}_with_timeseries_{timestamp}.json"
    
    # 저장
    file_handler = FileHandler()
    file_handler.save_json(merged_data, output_path)
    logger.info(f"\n✓ 병합 데이터 저장: {output_path}")
    
    # 통계 출력
    logger.info(f"\n{'='*60}")
    logger.info("병합 완료!")
    logger.info(f"{'='*60}")
    logger.info(f"총 업소 수: {len(stores):,}개")
    logger.info(f"개폐업일 정보 포함: {merged_count:,}개")
    logger.info(f"  - 개업일 확인: {metadata['total_with_open_date']:,}개")
    logger.info(f"  - 폐업일 확인: {metadata['total_with_close_date']:,}개")
    
    return merged_data


def main():
    """병합 스크립트 메인 함수."""
    import argparse
    
    parser = argparse.ArgumentParser(description='기본 데이터와 시계열 데이터 병합')
    parser.add_argument('--base', type=str, required=True, help='기본 업소 데이터 JSON 파일 경로')
    parser.add_argument('--timeseries', type=str, required=True, help='시계열 데이터 JSON 파일 경로')
    parser.add_argument('--output', type=str, help='출력 파일 경로 (선택)')
    
    args = parser.parse_args()
    
    merge_timeseries_with_base(
        base_json_path=Path(args.base),
        timeseries_json_path=Path(args.timeseries),
        output_path=Path(args.output) if args.output else None
    )


if __name__ == "__main__":
    main()

