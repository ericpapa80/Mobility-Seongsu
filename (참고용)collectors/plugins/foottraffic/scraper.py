"""Foottraffic scraper for collecting 골목길 유동인구 data."""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.base_scraper import BaseScraper
from plugins.foottraffic.api_client import FoottrafficAPIClient
from plugins.foottraffic.normalizer import FoottrafficNormalizer
from core.logger import get_logger
from core.file_handler import FileHandler
from core.storage.file_storage import FileStorage
from config.scrapers.foottraffic import FoottrafficConfig

logger = get_logger(__name__)


class FoottrafficScraper(BaseScraper):
    """Foottraffic scraper for collecting 골목길 유동인구 data.
    
    This scraper collects foot traffic data from 서울시 골목길 유동인구 API.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize Foottraffic scraper.
        
        Args:
            output_dir: Base output directory for saving data
        """
        super().__init__(name="foottraffic", output_dir=output_dir)
        self.api_client = FoottrafficAPIClient()
        self.file_handler = FileHandler()
        self.normalizer = FoottrafficNormalizer()
        self.storage = FileStorage(
            base_dir=self.output_dir / "processed",
            config={'source_name': 'foottraffic', 'save_json': True, 'save_csv': True}
        )
        
        # Validate configuration
        if not FoottrafficConfig.validate():
            logger.warning("Foottraffic configuration is incomplete. Some features may not work.")
    
    def scrape(
        self,
        minx: Optional[float] = None,
        miny: Optional[float] = None,
        maxx: Optional[float] = None,
        maxy: Optional[float] = None,
        wkt: str = "",
        dayweek: int = 1,
        agrde: str = "00",
        tmzon: str = "06",
        ext: str = "ext",
        signguCd: int = 11,
        use_seongsu_bounds: bool = True,
        save_json: bool = True,
        save_csv: bool = True
    ) -> Dict[str, Any]:
        """Scrape 골목길 유동인구 data.
        
        Args:
            minx: 최소 X 좌표 (use_seongsu_bounds=True일 때 무시됨)
            miny: 최소 Y 좌표 (use_seongsu_bounds=True일 때 무시됨)
            maxx: 최대 X 좌표 (use_seongsu_bounds=True일 때 무시됨)
            maxy: 최대 Y 좌표 (use_seongsu_bounds=True일 때 무시됨)
            wkt: WKT 형식의 공간 정보 (기본값: 빈 문자열)
            dayweek: 요일 구분 (1: 주중, 2: 주말, 기본값: 1)
            agrde: 연령대 ("00": 전체, "10": 10대, "20": 20대, "30": 30대, "40": 40대, "50": 50대, "60": 60대이상, 기본값: "00")
            tmzon: 시간대 (00: 종일, 01: 00~05, 02: 06~10, 03: 11~13, 04: 14~16, 05: 17~20, 06: 21~23, 기본값: 06)
            ext: 확장 파라미터 (기본값: "ext")
            signguCd: 시군구 코드 (기본값: 11 - 서울시)
            use_seongsu_bounds: 성수동 좌표 범위 사용 여부 (기본값: True)
            save_json: Whether to save as JSON
            save_csv: Whether to save as CSV
            
        Returns:
            Dictionary containing scraped data with 'data', 'files', and 'timestamp' keys
            
        Example:
            >>> scraper = FoottrafficScraper()
            >>> result = scraper.scrape(use_seongsu_bounds=True, dayweek=1, tmzon="06")
        """
        logger.info("Starting 골목길 유동인구 data scraping")
        
        try:
            # Determine bounds
            if use_seongsu_bounds:
                bounds = FoottrafficConfig.get_seongsu_bounds()
                minx = bounds['minx']
                miny = bounds['miny']
                maxx = bounds['maxx']
                maxy = bounds['maxy']
                logger.info(f"Using 성수동 bounds: minx={minx}, miny={miny}, maxx={maxx}, maxy={maxy}")
            else:
                if minx is None or miny is None or maxx is None or maxy is None:
                    raise ValueError("Bounds (minx, miny, maxx, maxy) must be provided when use_seongsu_bounds=False")
                bounds = {'minx': minx, 'miny': miny, 'maxx': maxx, 'maxy': maxy}
            
            logger.info(f"Parameters: dayweek={dayweek}, agrde={agrde}, tmzon={tmzon}, signguCd={signguCd}")
            
            # Fetch data from API
            if use_seongsu_bounds:
                api_data = self.api_client.get_seongsu_foottraffic(
                    dayweek=dayweek,
                    agrde=agrde,
                    tmzon=tmzon
                )
            else:
                api_data = self.api_client.get_foottraffic_data(
                    minx=minx,
                    miny=miny,
                    maxx=maxx,
                    maxy=maxy,
                    wkt=wkt,
                    dayweek=dayweek,
                    agrde=agrde,
                    tmzon=tmzon,
                    ext=ext,
                    signguCd=signguCd
                )
            
            # Wrap in dict format for consistency
            data = {
                'records': api_data
            }
            
            # Validate data
            if not self.validate(data):
                logger.warning("Data validation failed, but continuing...")
            
            # Save raw data (only if save_json or save_csv is True)
            saved_files = {}
            timestamp = self._get_timestamp()
            
            # 폴더명에 지역 및 파라미터 포함
            location = "seongsu" if use_seongsu_bounds else "custom"
            folder_name = f"foottraffic_{location}_{timestamp}"
            
            # 폴더는 실제로 파일을 저장할 때만 생성
            if save_json or save_csv:
                output_dir = self.raw_dir / folder_name
                output_dir.mkdir(parents=True, exist_ok=True)
                
                if save_json:
                    json_path = output_dir / f"foottraffic_{location}_{timestamp}.json"
                    saved_files['json'] = self.file_handler.save_json(data, json_path)
                    logger.info(f"Raw data saved as JSON: {saved_files['json']}")
                
                if save_csv:
                    csv_path = output_dir / f"foottraffic_{location}_{timestamp}.csv"
                    # Convert records to CSV format
                    csv_data = api_data if isinstance(api_data, list) else [api_data]
                    saved_files['csv'] = self.file_handler.save_csv(csv_data, csv_path)
                    logger.info(f"Raw data saved as CSV: {saved_files['csv']}")
            
            # Normalize and save processed data (only if save_json or save_csv is True)
            if save_json or save_csv:
                metadata = {
                    'bounds': bounds,
                    'wkt': wkt,
                    'dayweek': dayweek,
                    'agrde': agrde,
                    'tmzon': tmzon,
                    'ext': ext,
                    'signguCd': signguCd,
                    'use_seongsu_bounds': use_seongsu_bounds,
                    'timestamp': timestamp,
                    'folder_name': folder_name,
                    'total_count': len(api_data)
                }
                normalized_data = self.normalizer.normalize(data, metadata)
                processed_path = self.storage.save(normalized_data, metadata)
                saved_files['processed'] = processed_path
                logger.info(f"Normalized data saved to: {processed_path}")
            
            logger.info("골목길 유동인구 data scraping completed successfully")
            return {
                'data': data,
                'files': saved_files,
                'timestamp': timestamp,
                'bounds': bounds,
                'dayweek': dayweek,
                'agrde': agrde,
                'tmzon': tmzon,
                'total_count': len(api_data)
            }
            
        except Exception as e:
            logger.error(f"Error during 골목길 유동인구 scraping: {e}")
            raise
    
    def _get_timestamp(self) -> str:
        """Get current timestamp string.
        
        Returns:
            Timestamp string in format: YYYYMMDD_HHMMSS
        """
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def close(self):
        """Close API client, storage, and cleanup."""
        self.api_client.close()
        self.storage.close()
        logger.info("Foottraffic scraper closed")

