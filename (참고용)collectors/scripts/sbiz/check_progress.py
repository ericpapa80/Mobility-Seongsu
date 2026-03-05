"""시계열 데이터 수집 진행 상황 확인."""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.logger import get_logger

logger = get_logger(__name__)


def check_timeseries_progress():
    """시계열 데이터 수집 진행 상황 확인."""
    print("=" * 60)
    print("시계열 데이터 수집 진행 상황 확인")
    print("=" * 60)
    
    # 중간 저장 파일 확인
    timeseries_dir = Path('data/raw/sbiz/timeseries')
    if not timeseries_dir.exists():
        print("\n시계열 데이터 디렉토리가 아직 생성되지 않았습니다.")
        return
    
    # 중간 저장 파일 찾기
    intermediate_files = sorted(timeseries_dir.glob('intermediate_*.json'))
    
    if intermediate_files:
        print(f"\n발견된 중간 저장 파일: {len(intermediate_files)}개")
        
        # 가장 최근 파일 확인
        latest_file = intermediate_files[-1]
        print(f"\n가장 최근 중간 저장 파일: {latest_file.name}")
        print(f"  수정 시간: {datetime.fromtimestamp(latest_file.stat().st_mtime)}")
        
        # 파일 내용 확인
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            total_stores = len(data)
            print(f"  추적 중인 업소 수: {total_stores:,}개")
            
            # 통계
            with_open = sum(1 for h in data.values() if h.get('openDate'))
            with_close = sum(1 for h in data.values() if h.get('closeDate'))
            print(f"  개업일 확인: {with_open:,}개")
            print(f"  폐업일 확인: {with_close:,}개")
            
            # 파일명에서 날짜 추출
            date_str = latest_file.stem.replace('intermediate_', '')
            if len(date_str) == 8:  # YYYYMMDD 형식
                date_obj = datetime.strptime(date_str, "%Y%m%d")
                print(f"  진행 날짜: {date_str} ({date_obj.strftime('%Y-%m-%d')})")
                
        except Exception as e:
            print(f"  파일 읽기 오류: {e}")
    else:
        print("\n중간 저장 파일이 없습니다.")
    
    # 최종 저장 파일 확인
    final_files = sorted(timeseries_dir.glob('timeseries_*.json'))
    if final_files:
        print(f"\n완료된 시계열 데이터 파일: {len(final_files)}개")
        for f in final_files[-3:]:  # 최근 3개만
            print(f"  - {f.name}")
            print(f"    수정 시간: {datetime.fromtimestamp(f.stat().st_mtime)}")
            print(f"    파일 크기: {f.stat().st_size / 1024 / 1024:.2f} MB")


def estimate_remaining_time(current_page: int = None, total_pages: int = None):
    """남은 시간 추정."""
    if current_page and total_pages:
        remaining_pages = total_pages - current_page
        print(f"\n{'='*60}")
        print(f"진행 상황 추정")
        print(f"{'='*60}")
        print(f"현재 페이지: {current_page:,}")
        print(f"전체 페이지: {total_pages:,}")
        print(f"진행률: {current_page / total_pages * 100:.1f}%")
        print(f"남은 페이지: {remaining_pages:,}")
        
        # API 호출 시간 추정 (페이지당 약 0.1초 가정)
        estimated_seconds = remaining_pages * 0.1
        estimated_minutes = estimated_seconds / 60
        estimated_hours = estimated_minutes / 60
        
        if estimated_hours < 1:
            print(f"예상 남은 시간: 약 {estimated_minutes:.1f}분")
        else:
            print(f"예상 남은 시간: 약 {estimated_hours:.1f}시간 ({estimated_minutes:.1f}분)")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='시계열 데이터 수집 진행 상황 확인')
    parser.add_argument('--current-page', type=int, help='현재 페이지 번호')
    parser.add_argument('--total-pages', type=int, help='전체 페이지 수')
    
    args = parser.parse_args()
    
    check_timeseries_progress()
    
    if args.current_page and args.total_pages:
        estimate_remaining_time(args.current_page, args.total_pages)

