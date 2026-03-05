"""성수동 데이터 수집 (연도별 비교 방식).

기본 데이터 수집 → 연도별 비교 데이터 수집 → 성수동 추출 → 병합
"""

import sys
from pathlib import Path
from datetime import datetime
import json
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.sbiz.scraper import SBIZScraper
from scripts.sbiz.collect_yearly_comparison import collect_yearly_data, compare_yearly_data
from scripts.sbiz.extract_seongsu import main as extract_seongsu_main
from core.logger import get_logger

logger = get_logger(__name__)


def merge_yearly_with_base(base_json_path: Path, yearly_comparison_path: Path, output_path: Path):
    """연도별 비교 결과를 기본 데이터와 병합.
    
    Args:
        base_json_path: 기본 데이터 JSON 파일 경로
        yearly_comparison_path: 연도별 비교 결과 JSON 파일 경로
        output_path: 출력 파일 경로
    """
    # 기본 데이터 로드
    with open(base_json_path, 'r', encoding='utf-8') as f:
        base_data = json.load(f)
    
    # 연도별 비교 결과 로드
    with open(yearly_comparison_path, 'r', encoding='utf-8') as f:
        comparison_data = json.load(f)
    
    store_status = comparison_data.get('store_status', {})
    
    # 기본 데이터의 각 업소에 연도별 정보 추가
    stores = base_data.get('stores', [])
    merged_count = 0
    
    for store in stores:
        bizes_id = store.get('bizesId')
        if bizes_id and bizes_id in store_status:
            status = store_status[bizes_id]
            store['openDate'] = status.get('openDate')  # YYYYMMDD 형식
            store['closeDate'] = status.get('closeDate')  # YYYYMMDD 형식
            store['openYear'] = status.get('openYear')
            store['closeYear'] = status.get('closeYear')
            store['statusHistory'] = status.get('statusHistory', [])
            store['firstSeenYear'] = status.get('firstSeenYear')
            store['lastSeenYear'] = status.get('lastSeenYear')
            store['firstSeenDate'] = status.get('firstSeenDate')  # YYYYMMDD 형식
            store['lastSeenDate'] = status.get('lastSeenDate')  # YYYYMMDD 형식
            merged_count += 1
    
    # 메타데이터 업데이트
    metadata = base_data.get('metadata', {})
    metadata.update({
        'yearly_comparison_merged': True,
        'yearly_comparison_source': str(yearly_comparison_path),
        'merged_at': datetime.now().isoformat(),
        'merged_count': merged_count
    })
    
    # 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(base_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"연도별 비교 결과 병합 완료: {merged_count:,}개 업소")


def main():
    """성수동 데이터 수집 (연도별 비교 방식) 메인 함수."""
    parser = argparse.ArgumentParser(description='성수동 데이터 수집 (연도별 비교 방식)')
    parser.add_argument('--years', type=str,
                       default='2025,2024,2023,2022,2021,2020,2019,2018,2017',
                       help='조회할 연도 리스트 (쉼표로 구분)')
    parser.add_argument('--month', type=int, default=10, help='조회할 월 (기본값: 10)')
    parser.add_argument('--day', type=int, default=10, help='조회할 일 (기본값: 10)')
    parser.add_argument('--skip-base', action='store_true',
                       help='기본 데이터 수집 건너뛰기')
    parser.add_argument('--skip-yearly', action='store_true',
                       help='연도별 비교 데이터 수집 건너뛰기')
    parser.add_argument('--skip-extract', action='store_true',
                       help='성수동 추출 건너뛰기')
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("성수동 데이터 수집 (연도별 비교 방식)")
    logger.info("=" * 60)
    
    # 1. 기본 데이터 수집
    base_json_path = None
    if not args.skip_base:
        logger.info(f"\n[1단계] 기본 데이터 수집 (성동구 전체)")
        logger.info("-" * 60)
        
        scraper = SBIZScraper()
        try:
            result = scraper.scrape(
                adong_cd="11200",
                div_id="signguCd",
                adong_nm="성동구"
            )
            
            # JSON 파일 경로 찾기
            files = result.get('files', {})
            json_file = files.get('json')
            if json_file:
                base_json_path = Path(json_file)
                logger.info(f"기본 데이터 저장: {base_json_path}")
            else:
                # 파일 경로가 없으면 결과에서 직접 찾기
                output_dir = Path('data/raw/sbiz')
                json_files = sorted(output_dir.glob("sbiz_stores_dong_성동구_*/sbiz_stores_dong_성동구_*.json"),
                                   reverse=True)
                if json_files:
                    base_json_path = json_files[0]
                    logger.info(f"기본 데이터 저장: {base_json_path}")
                else:
                    logger.error("기본 데이터 JSON 파일을 찾을 수 없습니다.")
                    return
        finally:
            scraper.close()
    else:
        # 기존 데이터 찾기
        base_dir = Path('data/raw/sbiz')
        json_files = sorted(base_dir.glob("sbiz_stores_dong_성동구_*/sbiz_stores_dong_성동구_*.json"),
                           reverse=True)
        if json_files:
            base_json_path = json_files[0]
            logger.info(f"기존 데이터 사용: {base_json_path}")
    
    if not base_json_path:
        logger.error("기본 데이터를 찾을 수 없습니다.")
        return
    
    # 2. 연도별 비교 데이터 수집
    yearly_comparison_path = None
    if not args.skip_yearly:
        logger.info(f"\n[2단계] 연도별 비교 데이터 수집")
        logger.info("-" * 60)
        
        # 연도 파싱
        years = [int(y.strip()) for y in args.years.split(',')]
        logger.info(f"조회할 연도: {years}")
        logger.info(f"조회 날짜: 매년 {args.month}월 {args.day}일")
        
        # 성수동 업소 ID 로드
        with open(base_json_path, 'r', encoding='utf-8') as f:
            base_data = json.load(f)
        stores = base_data.get('stores', [])
        seongsu_dongs = ['성수1가1동', '성수1가2동', '성수2가1동', '성수2가3동']
        seongsu_stores = [s for s in stores if s.get('adongNm') in seongsu_dongs]
        target_bizes_ids = {s.get('bizesId') for s in seongsu_stores if s.get('bizesId')}
        logger.info(f"성수동 대상 업소 수: {len(target_bizes_ids):,}개")
        
        # 연도별 데이터 수집
        yearly_data = collect_yearly_data(
            years=years,
            month=args.month,
            day=args.day,
            target_bizes_ids=target_bizes_ids
        )
        
        # 연도별 비교 분석
        store_status = compare_yearly_data(yearly_data, month=args.month, day=args.day)
        
        # 결과 저장
        output_dir = Path('data/raw/sbiz/yearly_comparison')
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        yearly_comparison_path = output_dir / f"yearly_comparison_{timestamp}.json"
        with open(yearly_comparison_path, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'years': years,
                    'month': args.month,
                    'day': args.day,
                    'collected_at': datetime.now().isoformat(),
                    'total_stores': len(store_status)
                },
                'store_status': store_status
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"연도별 비교 결과 저장: {yearly_comparison_path}")
    else:
        # 기존 연도별 비교 데이터 찾기
        comparison_dir = Path('data/raw/sbiz/yearly_comparison')
        json_files = sorted(comparison_dir.glob("yearly_comparison_*.json"), reverse=True)
        if json_files:
            yearly_comparison_path = json_files[0]
            logger.info(f"기존 연도별 비교 데이터 사용: {yearly_comparison_path}")
    
    # 3. 성수동 추출 및 병합
    if not args.skip_extract and yearly_comparison_path:
        logger.info(f"\n[3단계] 성수동 추출 및 연도별 비교 결과 병합")
        logger.info("-" * 60)
        
        # 성수동 추출 (기본)
        extract_seongsu_main(timeseries_json_path=None)
        
        # 추출된 파일 찾기
        extract_dir = Path('data/raw/sbiz')
        json_files = sorted(extract_dir.glob("sbiz_stores_seongsu_extracted_*/sbiz_stores_seongsu_*.json"),
                           reverse=True)
        if json_files:
            extracted_json_path = json_files[0]
            
            # 연도별 비교 결과 병합
            merge_yearly_with_base(extracted_json_path, yearly_comparison_path, extracted_json_path)
            logger.info(f"최종 데이터 저장: {extracted_json_path}")
    
    logger.info(f"\n{'='*60}")
    logger.info("성수동 데이터 수집 완료 (연도별 비교 방식)!")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()

