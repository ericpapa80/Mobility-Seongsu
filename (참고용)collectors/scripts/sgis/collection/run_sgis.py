"""Script to run SGIS technical business map scraper."""

import sys
import argparse
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
# 스크립트 위치: scripts/sgis/collection/run_sgis.py
# 프로젝트 루트: scripts/sgis/collection/ -> scripts/sgis/ -> scripts/ -> 프로젝트 루트
script_dir = Path(__file__).resolve().parent  # scripts/sgis/collection/
project_root = script_dir.parent.parent.parent.parent  # 프로젝트 루트 (4단계 위)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.scraper_registry import registry
from core.runner import ScraperRunner
from core.logger import get_logger

logger = get_logger(__name__)


def main():
    """Main function to run SGIS scraper."""
    parser = argparse.ArgumentParser(
        description="SGIS 기술업종 통계지도 데이터 수집 스크립트"
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='데이터 저장 디렉토리 (기본값: data/)'
    )
    parser.add_argument(
        '--json-only',
        action='store_true',
        help='JSON 형식으로만 저장'
    )
    parser.add_argument(
        '--csv-only',
        action='store_true',
        help='CSV 형식으로만 저장'
    )
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='파일로 저장하지 않음 (콘솔 출력만)'
    )
    parser.add_argument(
        '--bounds',
        type=str,
        help='지도 범위 (형식: "north,south,east,west" 예: "37.6,37.4,127.1,126.9")'
    )
    parser.add_argument(
        '--zoom',
        type=int,
        help='줌 레벨 (선택사항)'
    )
    parser.add_argument(
        '--theme-cd',
        type=int,
        default=0,
        help='테마 코드 (기본값: 0)'
    )
    parser.add_argument(
        '--year',
        type=int,
        default=2023,
        help='연도 (기본값: 2023)'
    )
    parser.add_argument(
        '--adm-cd',
        type=str,
        default='11040',
        help='행정구역 코드 (기본값: 11040 - 서울시 종로구)'
    )
    parser.add_argument(
        '--data-type',
        type=int,
        default=3,
        help='데이터 타입 (기본값: 3)'
    )
    
    args = parser.parse_args()
    
    # Parse bounds if provided
    bounds = None
    if args.bounds:
        try:
            coords = [float(x.strip()) for x in args.bounds.split(',')]
            if len(coords) == 4:
                bounds = {
                    'north': coords[0],
                    'south': coords[1],
                    'east': coords[2],
                    'west': coords[3]
                }
            else:
                logger.error("Bounds must have 4 values: north,south,east,west")
                sys.exit(1)
        except ValueError as e:
            logger.error(f"Invalid bounds format: {e}")
            sys.exit(1)
    
    # Determine save options
    save_json = not args.csv_only and not args.no_save
    save_csv = not args.json_only and not args.no_save
    
    # Determine output directory
    output_dir = None
    if args.output_dir:
        output_dir = Path(args.output_dir)
    
    try:
        # Use unified runner
        runner = ScraperRunner()
        
        # Prepare parameters
        scraper_params = {
            'theme_cd': args.theme_cd,
            'year': args.year,
            'adm_cd': args.adm_cd,
            'data_type': args.data_type
        }
        if bounds:
            scraper_params['bounds'] = bounds
        if args.zoom is not None:
            scraper_params['zoom_level'] = args.zoom
        
        # Run scraper
        logger.info("SGIS 기술업종 통계지도 데이터 수집 시작...")
        result = runner.run_scraper(
            name="sgis",
            output_dir=output_dir,
            save_json=save_json,
            save_csv=save_csv,
            **scraper_params
        )
        
        if result:
            # Print results
            if args.no_save:
                import json
                print("\n=== 수집된 데이터 ===")
                print(json.dumps(result.get('data', {}), ensure_ascii=False, indent=2))
            else:
                print("\n=== 수집 완료 ===")
                print(f"타임스탬프: {result.get('timestamp', 'N/A')}")
                if 'files' in result:
                    if 'json' in result['files']:
                        print(f"JSON 파일: {result['files']['json']}")
                    if 'csv' in result['files']:
                        print(f"CSV 파일: {result['files']['csv']}")
                if bounds:
                    print(f"수집 범위: {bounds}")
                if args.zoom:
                    print(f"줌 레벨: {args.zoom}")
        else:
            logger.error("스크래이핑 실패")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"스크래이핑 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

