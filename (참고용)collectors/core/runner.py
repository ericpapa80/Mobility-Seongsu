"""Unified runner for executing scrapers."""

import sys
import argparse
from pathlib import Path
from typing import List, Optional, Dict, Any
from core.scraper_registry import registry
from core.logger import get_logger

logger = get_logger(__name__)


class ScraperRunner:
    """Unified runner for executing scrapers."""
    
    def __init__(self):
        """Initialize runner."""
        self.registry = registry
    
    def list_scrapers(self) -> List[str]:
        """List all available scrapers.
        
        Returns:
            List of scraper names
        """
        return self.registry.list_scrapers()
    
    def run_scraper(
        self,
        name: str,
        output_dir: Optional[Path] = None,
        save_json: bool = True,
        save_csv: bool = True,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Run a specific scraper.
        
        Args:
            name: Scraper name
            output_dir: Output directory for data
            save_json: Whether to save as JSON
            save_csv: Whether to save as CSV
            **kwargs: Additional arguments for scraper
            
        Returns:
            Scraper result dictionary or None if failed
        """
        logger.info(f"Running scraper: {name}")
        
        # Create scraper instance
        scraper = self.registry.create_scraper_instance(
            name=name,
            output_dir=output_dir
        )
        
        if scraper is None:
            logger.error(f"Failed to create scraper instance: {name}")
            return None
        
        try:
            # Run scraper
            result = scraper.scrape(
                save_json=save_json,
                save_csv=save_csv,
                **kwargs
            )
            
            logger.info(f"Scraper {name} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error running scraper {name}: {e}")
            return None
        finally:
            # Cleanup if scraper has close method
            if hasattr(scraper, 'close'):
                try:
                    scraper.close()
                except Exception as e:
                    logger.warning(f"Error closing scraper {name}: {e}")
    
    def run_multiple(
        self,
        names: List[str],
        output_dir: Optional[Path] = None,
        save_json: bool = True,
        save_csv: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Run multiple scrapers.
        
        Args:
            names: List of scraper names
            output_dir: Output directory for data
            save_json: Whether to save as JSON
            save_csv: Whether to save as CSV
            **kwargs: Additional arguments for scrapers
            
        Returns:
            Dictionary mapping scraper names to results
        """
        results = {}
        
        for name in names:
            result = self.run_scraper(
                name=name,
                output_dir=output_dir,
                save_json=save_json,
                save_csv=save_csv,
                **kwargs
            )
            results[name] = result
        
        return results


def main():
    """Main entry point for unified runner."""
    parser = argparse.ArgumentParser(
        description="통합 스크래이퍼 실행기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 모든 스크래이퍼 목록 보기
  python -m core.runner list
  
  # 특정 스크래이퍼 실행
  python -m core.runner run sgis
  
  # 여러 스크래이퍼 실행
  python -m core.runner run sgis publicdata
  
  # JSON만 저장
  python -m core.runner run sgis --json-only
  
  # 출력 디렉토리 지정
  python -m core.runner run sgis --output-dir /path/to/output
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='명령어')
    
    # List command
    list_parser = subparsers.add_parser('list', help='사용 가능한 스크래이퍼 목록 보기')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='스크래이퍼 실행')
    run_parser.add_argument(
        'scrapers',
        nargs='+',
        help='실행할 스크래이퍼 이름'
    )
    run_parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='데이터 저장 디렉토리'
    )
    run_parser.add_argument(
        '--json-only',
        action='store_true',
        help='JSON 형식으로만 저장'
    )
    run_parser.add_argument(
        '--csv-only',
        action='store_true',
        help='CSV 형식으로만 저장'
    )
    run_parser.add_argument(
        '--no-save',
        action='store_true',
        help='파일로 저장하지 않음'
    )
    
    args = parser.parse_args()
    
    runner = ScraperRunner()
    
    if args.command == 'list':
        scrapers = runner.list_scrapers()
        if scrapers:
            print("\n사용 가능한 스크래이퍼:")
            for name in scrapers:
                info = registry.get_scraper_info(name)
                description = info.get('description', '')
                print(f"  - {name}: {description}")
        else:
            print("사용 가능한 스크래이퍼가 없습니다.")
    
    elif args.command == 'run':
        # Determine save options
        save_json = not args.csv_only and not args.no_save
        save_csv = not args.json_only and not args.no_save
        
        # Determine output directory
        output_dir = None
        if args.output_dir:
            output_dir = Path(args.output_dir)
        
        # Run scrapers
        results = runner.run_multiple(
            names=args.scrapers,
            output_dir=output_dir,
            save_json=save_json,
            save_csv=save_csv
        )
        
        # Print results
        print("\n=== 실행 결과 ===")
        for name, result in results.items():
            if result:
                print(f"\n{name}: 성공")
                if 'files' in result:
                    if 'json' in result['files']:
                        print(f"  JSON: {result['files']['json']}")
                    if 'csv' in result['files']:
                        print(f"  CSV: {result['files']['csv']}")
            else:
                print(f"\n{name}: 실패")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

