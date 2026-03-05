"""VWorld scraper for collecting WFS 2.0 data."""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.base_scraper import BaseScraper
from plugins.vworld.api_client import VWorldAPIClient
from plugins.vworld.normalizer import VWorldNormalizer
from core.logger import get_logger
from core.file_handler import FileHandler
from core.storage.file_storage import FileStorage
from config.scrapers.vworld import VWorldConfig, WFS_LAYER_PROPERTY_NAMES

logger = get_logger(__name__)


class VWorldScraper(BaseScraper):
    """VWorld scraper for collecting WFS 2.0 data.
    
    This scraper collects geographic features from VWorld WFS 2.0 API.
    Supports both Data API (req/data) and WFS API (req/wfs).
    Data API is recommended for better performance.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize VWorld scraper.
        
        Args:
            output_dir: Base output directory for saving data
        """
        super().__init__(name="vworld", output_dir=output_dir)
        self.api_client = VWorldAPIClient()
        self.file_handler = FileHandler()
        self.normalizer = VWorldNormalizer()
        self.storage = FileStorage(
            base_dir=self.output_dir / "processed",
            config={'source_name': 'vworld', 'save_json': True, 'save_csv': True}
        )
        
        # Validate configuration
        if not VWorldConfig.validate():
            logger.warning("VWorld configuration is incomplete. Some features may not work.")
    
    def scrape(
        self,
        layer_id: str,
        bbox: List[float],
        use_data_api: bool = True,
        size: int = 100,
        page: int = 1,
        geometry: bool = True,
        attribute: bool = True,
        crs: str = "EPSG:3857",
        save_json: bool = True,
        save_csv: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Scrape geographic features from VWorld WFS 2.0 API.
        
        Args:
            layer_id: Layer ID (e.g., 'LT_C_LANDINFOBASEMAP' for Data API, 
                     'lt_c_landinfobasemap' for WFS API)
            bbox: Bounding box [minX, minY, maxX, maxY] in CRS coordinates
            use_data_api: Use Data API if True, WFS API if False (default: True)
            size: Number of features per page (Data API only, default: 100)
            page: Page number (Data API only, default: 1)
            geometry: Include geometry (Data API only, default: True)
            attribute: Include attributes (Data API only, default: True)
            crs: Coordinate reference system (default: EPSG:3857)
            save_json: Whether to save as JSON
            save_csv: Whether to save as CSV
            **kwargs: Additional parameters for API requests
            
        Returns:
            Dictionary containing scraped data with 'data', 'files', and 'timestamp' keys
            
        Example:
            >>> scraper = VWorldScraper()
            >>> result = scraper.scrape(
            ...     layer_id='LT_C_LANDINFOBASEMAP',
            ...     bbox=[14134500, 4518600, 14136500, 4520600],
            ...     use_data_api=True
            ... )
        """
        logger.info("Starting VWorld WFS 2.0 data scraping")
        logger.info(f"Parameters: layer_id={layer_id}, bbox={bbox}, use_data_api={use_data_api}")
        
        try:
            # 토지(LX맵)·건물(도로명주소) 레이어는 WFS로 요청 (Data API 미사용)
            layer_upper = (layer_id or "").upper()
            wfs_property_names = WFS_LAYER_PROPERTY_NAMES.get(layer_upper)
            use_wfs = wfs_property_names is not None

            if use_wfs:
                kwargs_wfs = {**kwargs}
                kwargs_wfs.setdefault("max_features", 1000)  # VWorld WFS 허용 상한 1000
                kwargs_wfs.setdefault("property_names", wfs_property_names)
                data = self.api_client.get_features_wfs(
                    layer_id=layer_id,
                    bbox=bbox,
                    **kwargs_wfs
                )
            elif use_data_api:
                data = self.api_client.get_features_data_api(
                    layer_id=layer_id,
                    bbox=bbox,
                    size=size,
                    page=page,
                    geometry=geometry,
                    attribute=attribute,
                    crs=crs,
                    **kwargs
                )
            else:
                data = self.api_client.get_features_wfs(
                    layer_id=layer_id,
                    bbox=bbox,
                    **kwargs
                )
            
            # Validate data
            if not self.validate(data):
                logger.warning("Data validation failed, but continuing...")
            
            # Save raw data
            saved_files = {}
            timestamp = self._get_timestamp()
            
            # Create folder name with layer ID and timestamp
            layer_name = layer_id.lower().replace('_', '-')
            folder_name = f"vworld_{layer_name}_{timestamp}"
            output_dir = self.raw_dir / folder_name
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if save_json:
                json_path = output_dir / f"vworld_{layer_name}_{timestamp}.json"
                saved_files['json'] = self.file_handler.save_json(data, json_path)
                logger.info(f"Raw data saved as JSON: {saved_files['json']}")
            
            if save_csv:
                csv_path = output_dir / f"vworld_{layer_name}_{timestamp}.csv"
                # Convert to list format for CSV
                csv_data = self._prepare_csv_data(data, layer_id=layer_id)
                saved_files['csv'] = self.file_handler.save_csv(csv_data, csv_path)
                logger.info(f"Raw data saved as CSV: {saved_files['csv']}")
            
            # Normalize and save processed data
            actual_api = 'wfs' if use_wfs else ('data' if use_data_api else 'wfs')
            metadata = {
                'layer_id': layer_id,
                'bbox': bbox,
                'api_type': actual_api,
                'crs': crs,
                'timestamp': timestamp,
                'folder_name': folder_name,
                'size': size if use_data_api else None,
                'page': page if use_data_api else None
            }
            normalized_data = self.normalizer.normalize(data, metadata)
            processed_path = self.storage.save(normalized_data, metadata)
            saved_files['processed'] = processed_path
            logger.info(f"Normalized data saved to: {processed_path}")
            
            logger.info("VWorld WFS 2.0 data scraping completed successfully")
            return {
                'data': data,
                'files': saved_files,
                'timestamp': timestamp,
                'layer_id': layer_id,
                'bbox': bbox,
                'use_data_api': use_data_api and not use_wfs,
                'crs': crs
            }
            
        except Exception as e:
            logger.error(f"Error during VWorld scraping: {e}")
            raise
    
    def _prepare_csv_data(self, data: Dict[str, Any], layer_id: str = None) -> list:
        """Prepare data for CSV export.
        
        Args:
            data: Raw data dictionary
            layer_id: Layer ID for reference
            
        Returns:
            List of dictionaries suitable for CSV export
        """
        items = []
        
        # Extract features from Data API response
        if 'response' in data:
            response = data['response']
            if response.get('status') == 'OK':
                result = response.get('result', {})
                feature_collection = result.get('featureCollection', {})
                features = feature_collection.get('features', [])
                
                for feature in features:
                    item = feature.get('properties', {})
                    # Add geometry info if available
                    if 'geometry' in feature:
                        item['geometry_type'] = feature['geometry'].get('type')
                    items.append(item)
        
        # Extract features from WFS GeoJSON format
        elif 'features' in data:
            for feature in data['features']:
                item = feature.get('properties', {})
                # Add geometry info if available
                if 'geometry' in feature:
                    item['geometry_type'] = feature['geometry'].get('type')
                items.append(item)
        
        # Handle direct feature list
        elif isinstance(data, list):
            items = data
        
        # Add layer_id to each item
        if layer_id:
            for item in items:
                if isinstance(item, dict):
                    item['layer_id'] = layer_id
        
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
        logger.info("VWorld scraper closed")
