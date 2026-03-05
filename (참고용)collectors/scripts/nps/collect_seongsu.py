# -*- coding: utf-8 -*-
"""성수동 국민연금 가입 사업장 데이터 수집 스크립트"""

import sys
import argparse
import io
from pathlib import Path
from datetime import datetime

# Windows에서 한글 출력을 위한 인코딩 설정
if sys.platform == 'win32':
    # stdout과 stderr의 인코딩을 UTF-8로 설정
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    else:
        # Python 3.6 이하 호환
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 프로젝트 루트를 sys.path에 추가
script_dir = Path(__file__).resolve().parent  # scripts/nps/
project_root = script_dir.parent.parent  # collectors/ (프로젝트 루트)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from plugins.nps.scraper import NPSScraper
from core.logger import get_logger

logger = get_logger(__name__)


def main():
    """성수동 국민연금 가입 사업장 데이터 수집"""
    
    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser(description='성수동 국민연금 가입 사업장 데이터 수집')
    parser.add_argument('--add-coordinates', '-c', action='store_true', 
                       help='주소를 좌표로 변환 (지오코딩)')
    parser.add_argument('--geocoding-service', choices=['kakao', 'naver', 'vworld'], 
                       default='kakao', help='지오코딩 서비스 선택 (기본값: kakao, 실제로는 kakao/naver 우선 사용)')
    parser.add_argument('--workers', '-w', type=int, default=10,
                       help='병렬 처리 워커 수 (기본값: 10)')
    parser.add_argument('--geocoding-delay', type=float, default=0.1,
                       help='지오코딩 API 호출 간 지연 시간(초) (기본값: 0.1)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("성수동 국민연금 가입 사업장 데이터 수집")
    print("=" * 80)
    print(f"수집 대상: 성수동 지역 사업장")
    print(f"필터 조건: 가입상태=1 (활성 사업장만)")
    if args.add_coordinates:
        print(f"좌표 추가: 활성화 ({args.geocoding_service} API 사용)")
    else:
        print(f"좌표 추가: 비활성화")
    print()
    
    scraper = NPSScraper()
    
    try:
        # 성수동 데이터 수집
        print("성수동 데이터 수집 중...")
        
        result = scraper.scrape(
            filter_address="성수동",  # 사업장지번상세주소에서 '성수동1가' 또는 '성수동2가' 우선 검색
            filter_active_only=True,
            add_coordinates=args.add_coordinates,
            geocoding_service=args.geocoding_service,
            geocoding_delay=args.geocoding_delay,
            save_json=True,
            save_csv=True
        )
        
        # 결과 출력
        data = result.get('data', {})
        total_count = result.get('total_count', 0)
        
        print(f"\n[OK] 수집 완료: {total_count:,}개 사업장")
        
        if 'files' in result:
            print("\n저장된 파일:")
            if 'json' in result['files']:
                print(f"  JSON: {result['files']['json']}")
            if 'csv' in result['files']:
                print(f"  CSV: {result['files']['csv']}")
            if 'processed' in result['files']:
                print(f"  Processed: {result['files']['processed']}")
        
        # 통계 정보 출력
        if total_count > 0 and 'records' in data:
            records = data['records']
            
            # 좌표 통계
            coords_count = sum(1 for r in records if r.get('x') is not None and r.get('y') is not None)
            if coords_count > 0:
                print(f"\n좌표 정보: {coords_count}/{total_count}개 사업장에 좌표 추가됨")
            
            # 업종별 통계
            industry_counts = {}
            total_employees = 0
            total_amount = 0
            
            for record in records:
                industry = record.get('업종코드명', '기타')
                industry_counts[industry] = industry_counts.get(industry, 0) + 1
                total_employees += record.get('가입자수', 0)
                total_amount += record.get('금액', 0)
            
            print("\n" + "=" * 80)
            print("수집 데이터 통계")
            print("=" * 80)
            print(f"총 사업장 수: {total_count:,}개")
            print(f"총 가입자 수: {total_employees:,}명")
            print(f"총 고지금액: {total_amount:,}원")
            
            print("\n주요 업종 (상위 10개):")
            sorted_industries = sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)
            for i, (industry, count) in enumerate(sorted_industries[:10], 1):
                print(f"  {i}. {industry}: {count}개 사업장")
        
        print("\n" + "=" * 80)
        print("저장 위치")
        print("=" * 80)
        print("원본 데이터: data/raw/nps/{timestamp}/")
        print("가공 데이터: data/processed/nps/{timestamp}/")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"성수동 데이터 수집 실패: {e}")
        print(f"\n[ERROR] 수집 실패: {e}")
        raise
    
    finally:
        scraper.close()


if __name__ == "__main__":
    main()

