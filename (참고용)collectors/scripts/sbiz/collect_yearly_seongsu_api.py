"""API를 통한 연도별 성수동 상가업소 수집.

각 연도 말일(12월 31일)에 변경된 업소를 조회하여 연도별 데이터를 수집합니다.
"""

import sys
from pathlib import Path
from typing import Dict, Set, List
from datetime import datetime
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.sbiz.api_client import SBIZAPIClient
from plugins.sbiz.scraper import SBIZScraper
from core.logger import get_logger
from core.file_handler import FileHandler

logger = get_logger(__name__)


def collect_yearly_stores_by_api(
    years: List[int],
    target_bizes_ids: Set[str] = None
) -> Dict[int, List[Dict]]:
    """API를 통해 연도별 상가업소 수집.
    
    주의: storeListByDate API는 해당 날짜에 변경된 업소만 조회합니다.
    따라서 각 연도 말일(12월 31일)에 변경된 업소만 수집됩니다.
    
    Args:
        years: 수집할 연도 리스트
        target_bizes_ids: 추적할 업소 ID 집합 (None이면 모든 업소)
        
    Returns:
        {year: [store_data]} 형태의 딕셔너리
    """
    client = SBIZAPIClient()
    yearly_stores = {}
    
    try:
        for year in sorted(years, reverse=True):  # 최신 연도부터
            # 각 연도 말일 (12월 31일)
            date_str = f"{year}1231"
            logger.info(f"\n{'='*60}")
            logger.info(f"[{year}년] {date_str} 데이터 수집 중...")
            logger.info(f"{'='*60}")
            
            # 해당 날짜에 변경된 업소 조회
            stores_by_date = client.get_all_stores_by_date(date_str)
            
            if not stores_by_date:
                logger.warning(f"  {date_str}에 변경된 업소가 없습니다.")
                yearly_stores[year] = []
                continue
            
            # 성수동 업소만 필터링
            if target_bizes_ids:
                filtered_stores = [
                    s for s in stores_by_date
                    if s.get('bizesId') in target_bizes_ids
                ]
            else:
                # 성수동 행정동명으로 필터링
                seongsu_dongs = ['성수1가1동', '성수1가2동', '성수2가1동', '성수2가3동']
                filtered_stores = [
                    s for s in stores_by_date
                    if s.get('adongNm') in seongsu_dongs
                ]
            
            yearly_stores[year] = filtered_stores
            logger.info(f"  수집된 업소 수: {len(filtered_stores):,}개")
            
            # 행정동별 통계
            if filtered_stores:
                dong_counts = {}
                for store in filtered_stores:
                    dong = store.get('adongNm', '')
                    dong_counts[dong] = dong_counts.get(dong, 0) + 1
                
                logger.info(f"  행정동별 업소 수:")
                for dong in ['성수1가1동', '성수1가2동', '성수2가1동', '성수2가3동']:
                    count = dong_counts.get(dong, 0)
                    if count > 0:
                        logger.info(f"    {dong}: {count:,}개")
            
    finally:
        client.close()
    
    return yearly_stores


def collect_current_stores_by_api() -> List[Dict]:
    """현재 시점의 성수동 상가업소를 API로 수집.
    
    Returns:
        성수동 상가업소 리스트
    """
    logger.info(f"\n{'='*60}")
    logger.info("현재 시점 성수동 상가업소 수집 중...")
    logger.info(f"{'='*60}")
    
    scraper = SBIZScraper()
    try:
        # 성동구 전체 수집
        result = scraper.scrape(
            adong_cd="11200",
            div_id="signguCd",
            adong_nm="성동구"
        )
        
        # JSON 파일에서 데이터 로드
        json_file = result.get('files', {}).get('json')
        if json_file:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            stores = data.get('stores', [])
            
            # 성수동 필터링
            seongsu_dongs = ['성수1가1동', '성수1가2동', '성수2가1동', '성수2가3동']
            seongsu_stores = [
                s for s in stores
                if s.get('adongNm') in seongsu_dongs
            ]
            
            logger.info(f"  성수동 업소 수: {len(seongsu_stores):,}개")
            
            # 행정동별 통계
            dong_counts = {}
            for store in seongsu_stores:
                dong = store.get('adongNm', '')
                dong_counts[dong] = dong_counts.get(dong, 0) + 1
            
            logger.info(f"  행정동별 업소 수:")
            for dong in seongsu_dongs:
                count = dong_counts.get(dong, 0)
                logger.info(f"    {dong}: {count:,}개")
            
            return seongsu_stores
        else:
            logger.error("JSON 파일을 찾을 수 없습니다.")
            return []
            
    finally:
        scraper.close()


def save_yearly_data(stores: List[Dict], year: int, output_dir: Path):
    """연도별 데이터를 JSON과 CSV로 저장.
    
    Args:
        stores: 상가업소 리스트
        year: 연도
        output_dir: 출력 디렉토리
    """
    if not stores:
        logger.warning(f"  [{year}년] 저장할 데이터가 없습니다.")
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    file_handler = FileHandler()
    
    # JSON 저장
    json_path = output_dir / f"sbiz_stores_seongsu_{year}_api.json"
    data = {
        'metadata': {
            'year': year,
            'collected_at': datetime.now().isoformat(),
            'total_count': len(stores),
            'source': 'api',
            'note': '해당 연도 말일(12월 31일)에 변경된 업소만 포함'
        },
        'stores': stores
    }
    file_handler.save_json(data, json_path)
    logger.info(f"  JSON 저장: {json_path}")
    
    # CSV 저장
    import pandas as pd
    csv_path = output_dir / f"sbiz_stores_seongsu_{year}_api.csv"
    df = pd.DataFrame(stores)
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    logger.info(f"  CSV 저장: {csv_path}")


def main():
    """API를 통한 연도별 성수동 상가업소 수집 메인 함수."""
    import argparse
    
    parser = argparse.ArgumentParser(description='API를 통한 연도별 성수동 상가업소 수집')
    parser.add_argument('--years', type=str,
                       default='2017,2018,2019,2020,2021,2022,2023,2024,2025',
                       help='수집할 연도 리스트 (쉼표로 구분)')
    parser.add_argument('--output-dir', type=str,
                       default='data/raw/sbiz/yearly_seongsu_api',
                       help='출력 디렉토리')
    parser.add_argument('--include-current', action='store_true',
                       help='현재 시점 데이터도 수집')
    parser.add_argument('--use-current-as-target', action='store_true',
                       help='현재 시점 데이터를 기준으로 성수동 업소 ID 추출 후 연도별 조회')
    
    args = parser.parse_args()
    
    # 연도 파싱
    years = [int(y.strip()) for y in args.years.split(',')]
    logger.info(f"수집할 연도: {years}")
    
    output_dir = Path(args.output_dir)
    
    logger.info(f"\n{'='*60}")
    logger.info("API를 통한 연도별 성수동 상가업소 수집 시작")
    logger.info(f"{'='*60}")
    logger.info(f"※ 주의: storeListByDate API는 해당 날짜에 변경된 업소만 조회합니다.")
    logger.info(f"※ 따라서 각 연도 말일(12월 31일)에 변경된 업소만 수집됩니다.")
    
    # 현재 시점 데이터 수집 (기준점)
    target_bizes_ids = None
    if args.use_current_as_target or args.include_current:
        current_stores = collect_current_stores_by_api()
        target_bizes_ids = {s.get('bizesId') for s in current_stores if s.get('bizesId')}
        logger.info(f"  성수동 대상 업소 ID 수: {len(target_bizes_ids):,}개")
        
        if args.include_current:
            current_year = datetime.now().year
            save_yearly_data(current_stores, current_year, output_dir)
    
    # 연도별 데이터 수집
    yearly_stores = collect_yearly_stores_by_api(years, target_bizes_ids)
    
    # 저장
    total_stores = 0
    for year in sorted(years):
        stores = yearly_stores.get(year, [])
        if stores:
            save_yearly_data(stores, year, output_dir)
            total_stores += len(stores)
    
    logger.info(f"\n{'='*60}")
    logger.info("연도별 성수동 상가업소 수집 완료!")
    logger.info(f"{'='*60}")
    logger.info(f"총 수집된 업소 수: {total_stores:,}개 (중복 포함)")
    logger.info(f"저장 위치: {output_dir}")
    logger.info(f"\n※ 참고: 각 연도 말일(12월 31일)에 변경된 업소만 수집되었습니다.")
    logger.info(f"※ 전체 업소 목록이 필요하면 CSV 파일 추출 방식을 사용하세요.")


if __name__ == "__main__":
    main()

