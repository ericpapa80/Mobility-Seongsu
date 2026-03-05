"""SBIZ scraper for collecting 소상공인시장진흥공단 상가(상권)정보."""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.base_scraper import BaseScraper
from plugins.sbiz.api_client import SBIZAPIClient
from core.logger import get_logger
from core.file_handler import FileHandler
from config.scrapers.sbiz import SBIZConfig

logger = get_logger(__name__)


class SBIZScraper(BaseScraper):
    """SBIZ scraper for collecting 상가업소 정보.
    
    소상공인시장진흥공단 상가(상권)정보 OpenAPI를 통해
    개별 업소 데이터를 수집합니다.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize SBIZ scraper.
        
        Args:
            output_dir: Base output directory for saving data
        """
        super().__init__(name="sbiz", output_dir=output_dir)
        self.api_client = SBIZAPIClient()
        self.file_handler = FileHandler()
        
        # Validate configuration
        if not SBIZConfig.validate():
            logger.warning("SBIZ configuration is incomplete. Some features may not work.")
    
    def scrape(
        self,
        adong_cd: str = None,
        adong_nm: Optional[str] = None,
        area_cd: Optional[str] = None,
        inds_lcls_cd: Optional[str] = None,
        inds_mcls_cd: Optional[str] = None,
        inds_scls_cd: Optional[str] = None,
        save_json: bool = True,
        save_csv: bool = True,
        div_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """상가업소 데이터 수집 (행정동 또는 상권 단위).
        
        Args:
            adong_cd: 행정동 코드 (예: 11545510 - 성수1동)
            adong_nm: 행정동명 또는 상권명 (로깅용)
            area_cd: 상권 번호 (예: 11040)
            inds_lcls_cd: 상권업종 대분류코드 (옵션)
            inds_mcls_cd: 상권업종 중분류코드 (옵션)
            inds_scls_cd: 상권업종 소분류코드 (옵션)
            save_json: JSON 저장 여부
            save_csv: CSV 저장 여부
            div_id: 구분ID (adongCd, signguCd, ctprvnCd) - adong_cd 사용 시
            
        Returns:
            Dictionary containing scraped data with 'data', 'files', and 'timestamp' keys
            
        Example:
            >>> scraper = SBIZScraper()
            >>> result = scraper.scrape(area_cd="11040", adong_nm="형곡2동주민센터")
        """
        if area_cd:
            logger.info(f"Starting SBIZ 상가업소 데이터 수집 (상권)")
            logger.info(f"상권: {adong_nm or area_cd} (번호: {area_cd})")
            target_cd = area_cd
            target_type = "상권"
        else:
            logger.info(f"Starting SBIZ 상가업소 데이터 수집 (행정동)")
            logger.info(f"행정동: {adong_nm or adong_cd} (코드: {adong_cd})")
            target_cd = adong_cd
            target_type = "행정동"
        
        try:
            # Fetch all stores from API
            if area_cd:
                stores = self.api_client.get_all_stores_by_area(
                    area_cd=area_cd,
                    inds_lcls_cd=inds_lcls_cd,
                    inds_mcls_cd=inds_mcls_cd,
                    inds_scls_cd=inds_scls_cd
                )
            else:
                stores = self.api_client.get_all_stores_by_dong(
                    adong_cd=adong_cd,
                    inds_lcls_cd=inds_lcls_cd,
                    inds_mcls_cd=inds_mcls_cd,
                    inds_scls_cd=inds_scls_cd,
                    div_id=div_id
                )
            
            if not stores:
                logger.warning(f"No stores found for {target_type}={target_cd}")
                return {
                    'data': [],
                    'files': {},
                    'timestamp': datetime.now().isoformat(),
                    'count': 0
                }
            
            # Prepare data structure
            metadata = {
                'collected_at': datetime.now().isoformat(),
                'total_count': len(stores),
                'inds_lcls_cd': inds_lcls_cd,
                'inds_mcls_cd': inds_mcls_cd,
                'inds_scls_cd': inds_scls_cd
            }
            
            if area_cd:
                metadata.update({
                    'area_cd': area_cd,
                    'area_nm': adong_nm
                })
            else:
                metadata.update({
                    'adong_cd': adong_cd,
                    'adong_nm': adong_nm,
                    'div_id': div_id
                })
            
            data = {
                'metadata': metadata,
                'stores': stores
            }
            
            # Validate data
            if not self.validate(data):
                raise ValueError("Invalid data structure")
            
            # Generate timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name_safe = (adong_nm or target_cd).replace(" ", "_").replace("/", "_")
            prefix = "area" if area_cd else "dong"
            filename_base = f"sbiz_stores_{prefix}_{name_safe}_{timestamp}"
            
            # Save files
            files = {}
            timestamp_dir = self.raw_dir / f"{filename_base}"
            timestamp_dir.mkdir(parents=True, exist_ok=True)
            
            if save_json:
                json_path = timestamp_dir / f"{filename_base}.json"
                self.file_handler.save_json(data, json_path)
                files['json'] = str(json_path)
                logger.info(f"Saved JSON: {json_path}")
            
            if save_csv:
                # Flatten stores data for CSV
                csv_data = stores
                csv_path = timestamp_dir / f"{filename_base}.csv"
                self.file_handler.save_csv(csv_data, csv_path)
                files['csv'] = str(csv_path)
                logger.info(f"Saved CSV: {csv_path}")
            
            logger.info(f"Successfully collected {len(stores)} stores")
            
            return {
                'data': data,
                'files': files,
                'timestamp': timestamp,
                'count': len(stores)
            }
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}", exc_info=True)
            raise
    
    def close(self):
        """Close API client and cleanup."""
        self.api_client.close()
        logger.info("SBIZ scraper closed")

