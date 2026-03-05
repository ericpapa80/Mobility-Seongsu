"""SGIS scraper for collecting POI company density data."""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.base_scraper import BaseScraper
from plugins.sgis.api_client import SGISAPIClient
from plugins.sgis.normalizer import SGISNormalizer
from core.logger import get_logger
from core.file_handler import FileHandler
from core.storage.file_storage import FileStorage
from config.scrapers.sgis import SGISConfig

logger = get_logger(__name__)


class SGISScraper(BaseScraper):
    """SGIS scraper for collecting technical business data.
    
    This scraper collects POI company density data from SGIS API.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize SGIS scraper.
        
        Args:
            output_dir: Base output directory for saving data
        """
        super().__init__(name="sgis", output_dir=output_dir)
        self.api_client = SGISAPIClient()
        self.file_handler = FileHandler()
        self.normalizer = SGISNormalizer()
        self.storage = FileStorage(
            base_dir=self.output_dir / "processed",
            config={'source_name': 'sgis', 'save_json': True, 'save_csv': True}
        )
        
        # Validate configuration
        if not SGISConfig.validate():
            logger.warning("SGIS configuration is incomplete. Some features may not work.")
    
    def scrape(
        self,
        theme_cd: int = 0,
        year: int = 2023,
        adm_cd: str = "11040",
        data_type: int = 3,
        params: Optional[Dict[str, Any]] = None,
        bounds: Optional[Dict[str, float]] = None,
        zoom_level: Optional[int] = None,
        save_json: bool = True,
        save_csv: bool = True
    ) -> Dict[str, Any]:
        """Scrape technical business map data from SGIS.
        
        기술업종 통계지도에서 POI 회사 밀도 데이터를 수집합니다.
        
        Args:
            theme_cd: 테마 코드 (기본값: 0)
            year: 연도 (기본값: 2023)
            adm_cd: 행정구역 코드 (기본값: "11040" - 서울시 종로구)
            data_type: 데이터 타입 (기본값: 3)
            params: 추가 API request parameters
            bounds: Map bounds dictionary with 'north', 'south', 'east', 'west' keys
            zoom_level: Map zoom level (optional)
            save_json: Whether to save as JSON
            save_csv: Whether to save as CSV
            
        Returns:
            Dictionary containing scraped data with 'data', 'files', and 'timestamp' keys
            
        Example:
            >>> scraper = SGISScraper()
            >>> result = scraper.scrape(
            ...     year=2023,
            ...     adm_cd="11040",
            ...     bounds={'north': 37.6, 'south': 37.4, 'east': 127.1, 'west': 126.9},
            ...     zoom_level=10
            ... )
        """
        logger.info("Starting SGIS technical business map data scraping")
        logger.info(f"Parameters: theme_cd={theme_cd}, year={year}, adm_cd={adm_cd}, data_type={data_type}")
        
        try:
            # Fetch data from API
            data = self.api_client.get_poi_company_density(
                theme_cd=theme_cd,
                year=year,
                adm_cd=adm_cd,
                data_type=data_type,
                params=params,
                bounds=bounds,
                zoom_level=zoom_level
            )
            
            # Validate data
            if not self.validate(data):
                logger.warning("Data validation failed, but continuing...")
            
            # Save raw data
            saved_files = {}
            timestamp = self._get_timestamp()
            
            # 폴더명에 연도 포함: sgis_technical_biz_{year}_{timestamp}
            folder_name = f"sgis_technical_biz_{year}_{timestamp}"
            output_dir = self.raw_dir / folder_name
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if save_json:
                json_path = output_dir / f"sgis_technical_biz_{year}_{timestamp}.json"
                saved_files['json'] = self.file_handler.save_json(data, json_path)
                logger.info(f"Raw data saved as JSON: {saved_files['json']}")
            
            if save_csv:
                csv_path = output_dir / f"sgis_technical_biz_{year}_{timestamp}.csv"
                # Convert to list format if needed for CSV
                csv_data = self._prepare_csv_data(data, year=year)
                saved_files['csv'] = self.file_handler.save_csv(csv_data, csv_path)
                logger.info(f"Raw data saved as CSV: {saved_files['csv']}")
            
            # Normalize and save processed data
            metadata = {
                'theme_cd': theme_cd,
                'year': year,
                'adm_cd': adm_cd,
                'data_type': data_type,
                'timestamp': timestamp,
                'folder_name': folder_name
            }
            normalized_data = self.normalizer.normalize(data, metadata)
            processed_path = self.storage.save(normalized_data, metadata)
            saved_files['processed'] = processed_path
            logger.info(f"Normalized data saved to: {processed_path}")
            
            logger.info("SGIS technical business map data scraping completed successfully")
            return {
                'data': data,
                'files': saved_files,
                'timestamp': timestamp,
                'theme_cd': theme_cd,
                'year': year,
                'adm_cd': adm_cd,
                'data_type': data_type,
                'bounds': bounds,
                'zoom_level': zoom_level
            }
            
        except Exception as e:
            logger.error(f"Error during SGIS scraping: {e}")
            raise
    
    def _prepare_csv_data(self, data: Dict[str, Any], year: int = None) -> list:
        """Prepare data for CSV export.
        
        Args:
            data: Raw data dictionary
            year: Year to add as a column
            
        Returns:
            List of dictionaries suitable for CSV export
        """
        items = []
        
        # If data contains a list, use it directly
        if isinstance(data, list):
            items = data
        # If data contains a 'result' or 'data' key with a list
        elif isinstance(data, dict):
            # Check common keys for data arrays
            for key in ['result', 'data', 'items', 'list']:
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break
            
            # If no list found, return as single-item list
            if not items:
                items = [data]
        
        # Add year column to each item
        if year is not None:
            for item in items:
                if isinstance(item, dict):
                    item['year'] = year
        
        return items
    
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
        logger.info("SGIS scraper closed")

