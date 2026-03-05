"""성동구 데이터에서 성수동 관련 업소 추출 (개폐업일 정보 포함)."""

import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.logger import get_logger
from core.file_handler import FileHandler

logger = get_logger(__name__)


def main(timeseries_json_path: Path = None):
    """성동구 데이터에서 성수동 관련 업소 추출.
    
    Args:
        timeseries_json_path: 시계열 데이터 JSON 파일 경로 (선택)
    """
    # 성수동 관련 행정동 목록
    seongsu_dongs = [
        '성수1가1동',
        '성수1가2동',
        '성수2가1동',
        '성수2가3동'
    ]
    
    # 최신 성동구 데이터 파일 찾기
    csv_file = list(Path('data/raw/sbiz').glob('**/sbiz_stores_dong_성동구*.csv'))[-1]
    json_file = list(Path('data/raw/sbiz').glob('**/sbiz_stores_dong_성동구*.json'))[-1]
    
    logger.info(f"원본 CSV 파일: {csv_file}")
    logger.info(f"원본 JSON 파일: {json_file}")
    
    # 시계열 데이터 로드 (있는 경우)
    store_history = {}
    if timeseries_json_path and timeseries_json_path.exists():
        logger.info(f"시계열 데이터 로드: {timeseries_json_path}")
        with open(timeseries_json_path, 'r', encoding='utf-8') as f:
            timeseries_data = json.load(f)
        store_history = timeseries_data.get('store_history', {})
        logger.info(f"시계열 데이터 업소 수: {len(store_history):,}개")
    
    # CSV 파일 읽기
    df = pd.read_csv(csv_file)
    logger.info(f"전체 업소 수: {len(df):,}개")
    
    # 성수동 관련 업소 필터링
    seongsu_df = df[df['adongNm'].isin(seongsu_dongs)].copy()
    logger.info(f"성수동 관련 업소 수: {len(seongsu_df):,}개")
    
    # 행정동별 통계
    logger.info("\n행정동별 업소 수:")
    for dong in seongsu_dongs:
        count = len(seongsu_df[seongsu_df['adongNm'] == dong])
        logger.info(f"  {dong}: {count:,}개")
    
    if len(seongsu_df) == 0:
        logger.warning("성수동 관련 업소가 없습니다.")
        return
    
    # JSON 파일 읽기
    with open(json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    # JSON에서 성수동 관련 업소만 필터링
    original_stores = json_data.get('stores', [])
    seongsu_stores = [
        store for store in original_stores
        if store.get('adongNm') in seongsu_dongs
    ]
    
    # 시계열 데이터 병합 (개폐업일 정보 추가)
    merged_count = 0
    for store in seongsu_stores:
        bizes_id = store.get('bizesId')
        if bizes_id and bizes_id in store_history:
            history = store_history[bizes_id]
            store['openDate'] = history.get('openDate')
            store['closeDate'] = history.get('closeDate')
            store['changeHistory'] = history.get('changeHistory', [])
            merged_count += 1
    
    if store_history:
        logger.info(f"개폐업일 정보 병합: {merged_count:,}개 업소")
    
    # CSV에도 개폐업일 정보 추가
    if store_history:
        open_dates = []
        close_dates = []
        for _, row in seongsu_df.iterrows():
            bizes_id = row.get('bizesId')
            if bizes_id in store_history:
                history = store_history[bizes_id]
                open_dates.append(history.get('openDate'))
                close_dates.append(history.get('closeDate'))
            else:
                open_dates.append(None)
                close_dates.append(None)
        seongsu_df['openDate'] = open_dates
        seongsu_df['closeDate'] = close_dates
    
    # 메타데이터 업데이트
    metadata = json_data.get('metadata', {})
    metadata.update({
        'extracted_at': datetime.now().isoformat(),
        'original_file': str(csv_file.name),
        'seongsu_dongs': seongsu_dongs,
        'total_count': len(seongsu_stores),
        'timeseries_merged': bool(store_history),
        'timeseries_source': str(timeseries_json_path.name) if timeseries_json_path else None,
        'merged_count': merged_count,
        'total_with_open_date': sum(1 for s in seongsu_stores if s.get('openDate')),
        'total_with_close_date': sum(1 for s in seongsu_stores if s.get('closeDate'))
    })
    
    # 추출된 데이터 구조
    extracted_data = {
        'metadata': metadata,
        'stores': seongsu_stores
    }
    
    # 저장
    file_handler = FileHandler()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path('data/raw/sbiz') / f"sbiz_stores_seongsu_extracted_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # JSON 저장
    json_path = output_dir / f"sbiz_stores_seongsu_{timestamp}.json"
    file_handler.save_json(extracted_data, json_path)
    logger.info(f"\n✓ JSON 저장: {json_path}")
    
    # CSV 저장
    csv_path = output_dir / f"sbiz_stores_seongsu_{timestamp}.csv"
    seongsu_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    logger.info(f"✓ CSV 저장: {csv_path}")
    
    # 통계 정보 출력
    logger.info(f"\n{'='*60}")
    logger.info("추출 완료!")
    logger.info(f"{'='*60}")
    logger.info(f"총 업소 수: {len(seongsu_df):,}개")
    logger.info(f"좌표 데이터: {seongsu_df[['lon', 'lat']].notna().all(axis=1).sum():,}개 (100%)")
    if store_history:
        logger.info(f"개폐업일 정보 포함: {merged_count:,}개")
        logger.info(f"  - 개업일 확인: {metadata['total_with_open_date']:,}개")
        logger.info(f"  - 폐업일 확인: {metadata['total_with_close_date']:,}개")
    logger.info(f"저장 위치: {output_dir}")


if __name__ == "__main__":
    main()

