"""성동구 수집 → 성수동 추출 → 시계열 데이터 병합 통합 스크립트."""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.sbiz.scraper import SBIZScraper
from scripts.sbiz.collect_timeseries import collect_timeseries_data
from scripts.sbiz.extract_seongsu import main as extract_seongsu
from core.logger import get_logger

logger = get_logger(__name__)


def main(
    collect_base: bool = True,
    collect_timeseries: bool = True,
    extract_seongsu_flag: bool = True,
    timeseries_start_date: str = None,
    timeseries_end_date: str = None,
    timeseries_days_back: int = 365
):
    """통합 수집 프로세스 실행.
    
    Args:
        collect_base: 기본 데이터 수집 여부
        collect_timeseries: 시계열 데이터 수집 여부
        extract_seongsu_flag: 성수동 추출 여부
        timeseries_start_date: 시계열 데이터 시작일 (YYYYMMDD, None이면 자동 계산)
        timeseries_end_date: 시계열 데이터 종료일 (YYYYMMDD, None이면 오늘)
        timeseries_days_back: 시계열 데이터 수집 기간 (일)
    """
    logger.info(f"=" * 60)
    logger.info(f"성동구 → 성수동 데이터 수집 (개폐업일 정보 포함)")
    logger.info(f"=" * 60)
    
    base_json_path = None
    timeseries_json_path = None
    
    # 1. 기본 데이터 수집 (성동구 전체)
    if collect_base:
        logger.info(f"\n[1단계] 성동구 전체 데이터 수집")
        logger.info(f"-" * 60)
        
        scraper = SBIZScraper()
        try:
            result = scraper.scrape(
                adong_cd="11200",
                adong_nm="성동구",
                save_json=True,
                save_csv=True,
                div_id="signguCd"
            )
            logger.info(f"✓ 성동구 수집 완료: {result['count']}개 업소")
            base_json_path = Path(result['files'].get('json'))
            logger.info(f"  저장 위치: {base_json_path}")
        except Exception as e:
            logger.error(f"✗ 성동구 수집 실패: {e}")
            return
        finally:
            scraper.close()
    else:
        # 최신 성동구 데이터 파일 찾기
        base_json_path = list(Path('data/raw/sbiz').glob('**/sbiz_stores_dong_성동구*.json'))[-1]
        logger.info(f"기존 데이터 사용: {base_json_path}")
    
    # 2. 시계열 데이터 수집
    if collect_timeseries and base_json_path:
        logger.info(f"\n[2단계] 시계열 데이터 수집 (개폐업일 추적)")
        logger.info(f"-" * 60)
        
        # 날짜 계산
        if timeseries_end_date is None:
            timeseries_end_date = datetime.now().strftime("%Y%m%d")
        
        if timeseries_start_date is None:
            end_dt = datetime.strptime(timeseries_end_date, "%Y%m%d")
            start_dt = end_dt - timedelta(days=timeseries_days_back)
            timeseries_start_date = start_dt.strftime("%Y%m%d")
        
        logger.info(f"  기간: {timeseries_start_date} ~ {timeseries_end_date}")
        
        # 성수동 업소 ID만 로드
        import json
        seongsu_dongs = ['성수1가1동', '성수1가2동', '성수2가1동', '성수2가3동']
        
        with open(base_json_path, 'r', encoding='utf-8') as f:
            base_data = json.load(f)
        stores = base_data.get('stores', [])
        
        # 성수동 업소만 필터링
        seongsu_stores = [s for s in stores if s.get('adongNm') in seongsu_dongs]
        target_bizes_ids = {s.get('bizesId') for s in seongsu_stores if s.get('bizesId')}
        logger.info(f"  성수동 대상 업소 수: {len(target_bizes_ids):,}개 (전체 {len(stores):,}개 중)")
        
        # 시계열 데이터 수집
        try:
            output_dir = Path('data/raw/sbiz/timeseries')
            timeseries_data = collect_timeseries_data(
                start_date=timeseries_start_date,
                end_date=timeseries_end_date,
                target_bizes_ids=target_bizes_ids,
                output_dir=output_dir,
                max_workers=5,  # 병렬 처리 스레드 수
                use_parallel=True  # 병렬 처리 활성화
            )
            
            # 시계열 데이터 파일 경로 찾기
            timeseries_files = list(output_dir.glob(f"timeseries_{timeseries_start_date}_{timeseries_end_date}*.json"))
            if timeseries_files:
                timeseries_json_path = timeseries_files[-1]
                logger.info(f"✓ 시계열 데이터 저장: {timeseries_json_path}")
            else:
                logger.warning("시계열 데이터 파일을 찾을 수 없습니다.")
        except Exception as e:
            logger.error(f"✗ 시계열 데이터 수집 실패: {e}")
            import traceback
            traceback.print_exc()
    
    # 3. 성수동 추출 (개폐업일 정보 포함)
    if extract_seongsu_flag:
        logger.info(f"\n[3단계] 성수동 추출 (개폐업일 정보 포함)")
        logger.info(f"-" * 60)
        
        try:
            extract_seongsu(timeseries_json_path=timeseries_json_path)
            logger.info(f"✓ 성수동 추출 완료")
        except Exception as e:
            logger.error(f"✗ 성수동 추출 실패: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info(f"\n{'='*60}")
    logger.info("전체 프로세스 완료!")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='성동구 → 성수동 데이터 수집 (개폐업일 정보 포함)')
    parser.add_argument('--skip-base', action='store_true', help='기본 데이터 수집 건너뛰기')
    parser.add_argument('--skip-timeseries', action='store_true', help='시계열 데이터 수집 건너뛰기')
    parser.add_argument('--skip-extract', action='store_true', help='성수동 추출 건너뛰기')
    parser.add_argument('--timeseries-start', type=str, help='시계열 데이터 시작일 (YYYYMMDD)')
    parser.add_argument('--timeseries-end', type=str, help='시계열 데이터 종료일 (YYYYMMDD)')
    parser.add_argument('--timeseries-days', type=int, default=365, help='시계열 데이터 수집 기간 (일, 기본: 365)')
    
    args = parser.parse_args()
    
    main(
        collect_base=not args.skip_base,
        collect_timeseries=not args.skip_timeseries,
        extract_seongsu_flag=not args.skip_extract,
        timeseries_start_date=args.timeseries_start,
        timeseries_end_date=args.timeseries_end,
        timeseries_days_back=args.timeseries_days
    )

