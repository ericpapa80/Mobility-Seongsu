"""데이터가 있는 날짜 찾기.

각 연도별로 실제 데이터가 있는 날짜를 찾아서 반환합니다.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.sbiz.api_client import SBIZAPIClient
from core.logger import get_logger

logger = get_logger(__name__)


def find_dates_with_data(year: int, max_days: int = 365) -> list:
    """특정 연도에서 데이터가 있는 날짜 찾기.
    
    Args:
        year: 연도
        max_days: 최대 검색 일수 (기본값: 365일)
        
    Returns:
        데이터가 있는 날짜 리스트 (YYYYMMDD 형식)
    """
    client = SBIZAPIClient()
    dates_with_data = []
    
    try:
        # 연도 시작일
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)
        
        # 최근 날짜부터 역순으로 검색 (더 빠름)
        current_date = min(end_date, datetime.now())
        days_checked = 0
        
        logger.info(f"[{year}년] 데이터가 있는 날짜 검색 중...")
        
        while current_date >= start_date and days_checked < max_days:
            date_str = current_date.strftime("%Y%m%d")
            
            try:
                stores = client.get_all_stores_by_date(date_str)
                if stores and len(stores) > 0:
                    dates_with_data.append(date_str)
                    logger.info(f"  {date_str}: {len(stores):,}개 업소")
                    
                    # 충분한 데이터를 찾았으면 중단 (선택적)
                    if len(dates_with_data) >= 5:
                        break
            except Exception as e:
                pass  # 에러 무시하고 계속
            
            current_date -= timedelta(days=1)
            days_checked += 1
            
            # 진행 상황 표시 (100일마다)
            if days_checked % 100 == 0:
                logger.info(f"  진행: {days_checked}일 검색, {len(dates_with_data)}개 날짜 발견")
        
        logger.info(f"  [{year}년] 총 {len(dates_with_data)}개 날짜에서 데이터 발견")
        
    finally:
        client.close()
    
    return dates_with_data


def main():
    """메인 함수."""
    import argparse
    
    parser = argparse.ArgumentParser(description='데이터가 있는 날짜 찾기')
    parser.add_argument('--years', type=str,
                       default='2024,2023,2022',
                       help='검색할 연도 리스트 (쉼표로 구분)')
    parser.add_argument('--max-days', type=int, default=365,
                       help='연도당 최대 검색 일수')
    
    args = parser.parse_args()
    
    years = [int(y.strip()) for y in args.years.split(',')]
    
    logger.info(f"검색할 연도: {years}")
    
    all_dates = {}
    for year in years:
        dates = find_dates_with_data(year, args.max_days)
        all_dates[year] = dates
    
    logger.info(f"\n{'='*60}")
    logger.info("검색 결과 요약")
    logger.info(f"{'='*60}")
    for year, dates in all_dates.items():
        logger.info(f"{year}년: {len(dates)}개 날짜")
        if dates:
            logger.info(f"  예시: {dates[:3]}")


if __name__ == "__main__":
    main()

