"""연도별 특정 날짜 비교를 통한 개폐업 추적.

매년 특정 날짜(예: 10월 10일)의 데이터를 조회하여 연도별 비교로 개폐업을 추적합니다.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.sbiz.api_client import SBIZAPIClient
from plugins.sbiz.scraper import SBIZScraper
from core.logger import get_logger

logger = get_logger(__name__)


def collect_yearly_data(
    years: List[int],
    month: int = 10,
    day: int = 10,
    target_bizes_ids: Set[str] = None,
    div_id: str = "signguCd",
    area_cd: str = "11200"
) -> Dict[int, Dict[str, Dict]]:
    """연도별 특정 날짜 데이터 수집.
    
    Args:
        years: 조회할 연도 리스트 (예: [2025, 2024, 2023, ...])
        month: 조회할 월 (기본값: 10)
        day: 조회할 일 (기본값: 10)
        target_bizes_ids: 추적할 업소 ID 집합 (None이면 모든 업소)
        div_id: 구분ID (기본값: signguCd)
        area_cd: 지역 코드 (기본값: 11200 = 성동구)
        
    Returns:
        {year: {bizesId: store_data}} 형태의 딕셔너리
    """
    client = SBIZAPIClient()
    yearly_data = {}
    
    try:
        for year in sorted(years, reverse=True):  # 최신 연도부터
            date_str = f"{year}{month:02d}{day:02d}"
            logger.info(f"\n{'='*60}")
            logger.info(f"[{year}년] {month}월 {day}일 데이터 수집 중...")
            logger.info(f"{'='*60}")
            
            # 해당 날짜에 변경된 업소 조회 (storeListByDate)
            # 주의: storeListByDate는 해당 날짜에 변경된 업소만 조회함
            # 연도별 비교를 위해서는 해당 날짜 시점의 전체 업소 목록이 필요하지만,
            # API는 현재 시점의 데이터만 제공하므로,
            # 각 연도의 10월 10일에 변경된 업소를 추적하고
            # 연도별로 누적하여 비교하는 방식을 사용
            
            # 해당 날짜에 변경된 업소 조회
            stores_by_date = client.get_all_stores_by_date(date_str)
            
            if not stores_by_date:
                logger.warning(f"  {date_str}에 변경된 업소가 없습니다.")
                yearly_data[year] = {}
                continue
            
            # 성수동 업소만 필터링
            if target_bizes_ids:
                filtered_stores = [
                    s for s in stores_by_date
                    if s.get('bizesId') in target_bizes_ids
                ]
            else:
                filtered_stores = stores_by_date
            
            # 업소별 데이터 저장 (bizesId를 키로)
            year_stores = {}
            for store in filtered_stores:
                bizes_id = store.get('bizesId')
                if bizes_id:
                    year_stores[bizes_id] = store
            
            yearly_data[year] = year_stores
            logger.info(f"  수집된 업소 수: {len(year_stores):,}개")
            
    finally:
        client.close()
    
    return yearly_data


def compare_yearly_data(
    yearly_data: Dict[int, Dict[str, Dict]], 
    month: int = 10, 
    day: int = 10
) -> Dict[str, Dict]:
    """연도별 데이터 비교하여 개폐업 추적.
    
    주의: storeListByDate는 해당 날짜에 변경된 업소만 조회하므로,
    연도별 비교는 "해당 연도 10월 10일에 변경된 업소"를 기준으로 합니다.
    
    Args:
        yearly_data: {year: {bizesId: store_data}} 형태의 딕셔너리
        month: 조회한 월 (기본값: 10)
        day: 조회한 일 (기본값: 10)
        
    Returns:
        {bizesId: {openDate, closeDate, openYear, closeYear, statusHistory}} 형태의 딕셔너리
    """
    store_status = {}
    years = sorted(yearly_data.keys(), reverse=True)  # 최신 연도부터
    
    if not years:
        return store_status
    
    # 모든 연도의 업소 ID 수집
    all_bizes_ids = set()
    for year in years:
        all_bizes_ids.update(yearly_data[year].keys())
    
    logger.info(f"\n{'='*60}")
    logger.info("연도별 비교 분석 중...")
    logger.info(f"{'='*60}")
    logger.info(f"전체 추적 업소 수: {len(all_bizes_ids):,}개")
    logger.info(f"※ 주의: 각 연도의 {month}월 {day}일에 변경된 업소만 추적됩니다.")
    
    # 각 업소별로 연도별 상태 추적
    for bizes_id in all_bizes_ids:
        status_history = []
        first_seen_year = None
        last_seen_year = None
        first_seen_date = None
        last_seen_date = None
        
        # 최신 연도부터 과거로 순회
        for i, year in enumerate(years):
            exists = bizes_id in yearly_data[year]
            store_data = yearly_data[year].get(bizes_id, {})
            chg_gb = store_data.get('chgGb', '').strip() if store_data else ''
            
            # 날짜 문자열 생성 (YYYYMMDD)
            date_str = f"{year}{month:02d}{day:02d}"
            
            if exists:
                if first_seen_year is None:
                    first_seen_year = year
                    first_seen_date = date_str
                last_seen_year = year
                last_seen_date = date_str
                
                # 변경구분에 따라 상태 결정
                if chg_gb == 'C':
                    # 신규 개업
                    status_history.append({
                        'date': date_str,
                        'year': year,
                        'month': month,
                        'day': day,
                        'status': 'open',
                        'chgGb': chg_gb,
                        'note': f'{year}년 {month}월 {day}일에 신규 개업 (C)'
                    })
                elif chg_gb == 'D':
                    # 폐업
                    status_history.append({
                        'date': date_str,
                        'year': year,
                        'month': month,
                        'day': day,
                        'status': 'close',
                        'chgGb': chg_gb,
                        'note': f'{year}년 {month}월 {day}일에 폐업 (D)'
                    })
                elif chg_gb == 'U':
                    # 정보 수정 (영업중)
                    status_history.append({
                        'date': date_str,
                        'year': year,
                        'month': month,
                        'day': day,
                        'status': 'operating',
                        'chgGb': chg_gb,
                        'note': f'{year}년 {month}월 {day}일에 정보 수정 (U)'
                    })
                else:
                    # 변경구분 없음 (영업중으로 추정)
                    status_history.append({
                        'date': date_str,
                        'year': year,
                        'month': month,
                        'day': day,
                        'status': 'operating',
                        'chgGb': chg_gb or 'N/A',
                        'note': f'{year}년 {month}월 {day}일에 변경 이력 있음'
                    })
        
        # 최종 상태 결정
        open_year = None
        close_year = None
        open_date = None
        close_date = None
        
        # 개업 날짜: 'C' (신규)가 처음 나타난 날짜
        for status in reversed(status_history):  # 과거부터
            if status.get('chgGb') == 'C':
                open_year = status['year']
                open_date = status['date']
                break
        
        # 폐업 날짜: 'D' (폐업)가 가장 최근에 나타난 날짜
        for status in status_history:  # 최신부터
            if status.get('chgGb') == 'D':
                close_year = status['year']
                close_date = status['date']
                break
        
        # 개업 연도/날짜가 없으면 첫 등장 연도/날짜를 개업으로 설정
        if open_year is None and first_seen_year:
            open_year = first_seen_year
            open_date = first_seen_date
        
        store_status[bizes_id] = {
            'openDate': open_date,  # YYYYMMDD 형식
            'closeDate': close_date,  # YYYYMMDD 형식
            'openYear': open_year,
            'closeYear': close_year,
            'statusHistory': status_history,
            'firstSeenYear': first_seen_year,
            'lastSeenYear': last_seen_year,
            'firstSeenDate': first_seen_date,  # YYYYMMDD 형식
            'lastSeenDate': last_seen_date  # YYYYMMDD 형식
        }
    
    # 통계
    opened = sum(1 for s in store_status.values() if s.get('openYear'))
    closed = sum(1 for s in store_status.values() if s.get('closeYear'))
    operating = sum(1 for s in store_status.values() 
                   if s.get('openYear') and not s.get('closeYear'))
    
    logger.info(f"\n분석 결과:")
    logger.info(f"  개업 추적: {opened:,}개")
    logger.info(f"  폐업 추적: {closed:,}개")
    logger.info(f"  현재 영업중: {operating:,}개")
    
    return store_status


def main():
    """연도별 비교 데이터 수집 메인 함수."""
    import argparse
    
    parser = argparse.ArgumentParser(description='연도별 특정 날짜 비교를 통한 개폐업 추적')
    parser.add_argument('--years', type=str, 
                       default='2025,2024,2023,2022,2021,2020,2019,2018,2017',
                       help='조회할 연도 리스트 (쉼표로 구분, 예: 2025,2024,2023)')
    parser.add_argument('--month', type=int, default=10, help='조회할 월 (기본값: 10)')
    parser.add_argument('--day', type=int, default=10, help='조회할 일 (기본값: 10)')
    parser.add_argument('--base-file', type=str, 
                       help='기본 데이터 JSON 파일 경로 (성수동 업소 ID 추출용)')
    parser.add_argument('--output-dir', type=str, 
                       default='data/raw/sbiz/yearly_comparison',
                       help='출력 디렉토리')
    
    args = parser.parse_args()
    
    # 연도 파싱
    years = [int(y.strip()) for y in args.years.split(',')]
    logger.info(f"조회할 연도: {years}")
    logger.info(f"조회 날짜: 매년 {args.month}월 {args.day}일")
    
    # 성수동 업소 ID 로드
    target_bizes_ids = None
    if args.base_file:
        with open(args.base_file, 'r', encoding='utf-8') as f:
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
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 연도별 원본 데이터 저장
    yearly_file = output_dir / f"yearly_data_{timestamp}.json"
    with open(yearly_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'years': years,
                'month': args.month,
                'day': args.day,
                'collected_at': datetime.now().isoformat(),
                'target_bizes_ids_count': len(target_bizes_ids) if target_bizes_ids else None
            },
            'yearly_data': yearly_data
        }, f, ensure_ascii=False, indent=2)
    logger.info(f"\n연도별 데이터 저장: {yearly_file}")
    
    # 비교 분석 결과 저장
    comparison_file = output_dir / f"yearly_comparison_{timestamp}.json"
    with open(comparison_file, 'w', encoding='utf-8') as f:
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
    logger.info(f"비교 분석 결과 저장: {comparison_file}")
    
    logger.info(f"\n{'='*60}")
    logger.info("연도별 비교 데이터 수집 완료!")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()

