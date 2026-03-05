"""VWorld API client for making WFS 2.0 requests."""

import requests
from typing import Dict, Any, Optional, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config.scrapers.vworld import VWorldConfig
from core.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)


class VWorldAPIClient:
    """Client for VWorld WFS 2.0 API requests.
    
    Supports both Data API (req/data) and WFS API (req/wfs).
    Data API is recommended for better performance and features.
    """
    
    def __init__(self):
        """Initialize VWorld API client."""
        self.base_url = VWorldConfig.get_base_url()
        self.api_key = VWorldConfig.get_api_key()
        self.domain = VWorldConfig.get_domain()
        self.timeout = settings.request_timeout
        self.max_retries = settings.max_retries
        self.retry_delay = settings.retry_delay
        
        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def get_features_data_api(
        self,
        layer_id: str,
        bbox: List[float],
        size: int = 100,
        page: int = 1,
        geometry: bool = True,
        attribute: bool = True,
        crs: str = "EPSG:3857"
    ) -> Dict[str, Any]:
        """Get features using Data API (req/data) - Recommended.
        
        Args:
            layer_id: Layer ID (uppercase, e.g., 'LT_C_LANDINFOBASEMAP')
            bbox: Bounding box [minX, minY, maxX, maxY] in CRS coordinates
            size: Number of features per page (default: 100)
            page: Page number (default: 1)
            geometry: Include geometry (default: True)
            attribute: Include attributes (default: True)
            crs: Coordinate reference system (default: EPSG:3857)
            
        Returns:
            API response as dictionary
            
        Example:
            >>> client = VWorldAPIClient()
            >>> result = client.get_features_data_api(
            ...     layer_id='LT_C_LANDINFOBASEMAP',
            ...     bbox=[14134500, 4518600, 14136500, 4520600]
            ... )
        """
        endpoint = VWorldConfig.get_data_api_url()
        
        # Validate bbox
        if len(bbox) != 4:
            raise ValueError("bbox must be a list of 4 values: [minX, minY, maxX, maxY]")
        
        minX, minY, maxX, maxY = bbox
        
        # Create geomfilter BOX string
        geomfilter = f"BOX({minX},{minY},{maxX},{maxY})"
        
        params = {
            'key': self.api_key,
            'domain': self.domain,
            'service': 'data',
            'version': '2.0',
            'request': 'GetFeature',
            'format': 'json',
            'size': size,
            'page': page,
            'geometry': 'true' if geometry else 'false',
            'attribute': 'true' if attribute else 'false',
            'crs': crs,
            'data': layer_id.upper(),  # Data API requires uppercase
            'geomfilter': geomfilter
        }
        
        try:
            logger.info(f"Requesting features from Data API: {layer_id}")
            logger.debug(f"Request parameters: {params}")
            
            response = self.session.get(
                endpoint,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'response' in data:
                if data['response'].get('status') != 'OK':
                    error_msg = data['response'].get('error', {}).get('text', 'Unknown error')
                    logger.error(f"VWorld API error: {error_msg}")
                    raise ValueError(f"VWorld API error: {error_msg}")
            
            logger.info("Successfully retrieved features from Data API")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error requesting features from Data API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            raise
        except ValueError as e:
            logger.error(f"Error parsing response: {e}")
            raise
    
    def get_features_wfs(
        self,
        layer_id: str,
        bbox: List[float],
        max_features: int = 100,
        version: str = "1.1.0",
        srs_name: str = "EPSG:900913",
        output: str = "json",
        property_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get features using WFS API (req/wfs).
        
        Args:
            layer_id: Layer ID (lowercase, e.g., 'lt_c_landinfobasemap')
            bbox: Bounding box [minX, minY, maxX, maxY] in CRS coordinates
            max_features: Maximum number of features (default: 100)
            version: WFS version (default: 1.1.0)
            srs_name: Spatial reference system (default: EPSG:900913)
            output: Output format (default: json)
            property_names: List of property names to retrieve (optional)
            
        Returns:
            API response as dictionary
            
        Example:
            >>> client = VWorldAPIClient()
            >>> result = client.get_features_wfs(
            ...     layer_id='lt_c_landinfobasemap',
            ...     bbox=[14134500, 4518600, 14136500, 4520600]
            ... )
        """
        endpoint = VWorldConfig.get_wfs_api_url()
        
        # Validate bbox
        if len(bbox) != 4:
            raise ValueError("bbox must be a list of 4 values: [minX, minY, maxX, maxY]")
        
        minX, minY, maxX, maxY = bbox
        bbox_str = f"{minX},{minY},{maxX},{maxY}"
        
        params = {
            'SERVICE': 'WFS',
            'REQUEST': 'GetFeature',
            'TYPENAME': layer_id.lower(),  # WFS requires lowercase
            'BBOX': bbox_str,
            'VERSION': version,
            'MAXFEATURES': max_features,
            'SRSNAME': srs_name,
            'OUTPUT': output,
            'KEY': self.api_key,
            'DOMAIN': self.domain
        }
        
        # Add property names if specified
        if property_names:
            params['PROPERTYNAME'] = ','.join(property_names)
        
        try:
            logger.info(f"Requesting features from WFS API: {layer_id}")
            logger.debug(f"Request parameters: {params}")
            
            response = self.session.get(
                endpoint,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Parse response based on output format
            if output == 'json':
                try:
                    data = response.json()
                except ValueError as e:
                    logger.error(f"WFS response is not JSON. status={response.status_code}, "
                                f"content-type={response.headers.get('Content-Type')}")
                    logger.error(f"Response text (first 1500 chars): {response.text[:1500]}")
                    raise ValueError(f"WFS API returned non-JSON: {e}") from e
            else:
                # For GML or other formats, return as text
                data = {'text': response.text, 'content_type': response.headers.get('Content-Type')}
            
            logger.info("Successfully retrieved features from WFS API")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error requesting features from WFS API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            raise
        except ValueError as e:
            logger.error(f"Error parsing response: {e}")
            raise
    
    def get_features(
        self,
        layer_id: str,
        bbox: List[float],
        use_data_api: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Get features using either Data API or WFS API.
        
        Args:
            layer_id: Layer ID
            bbox: Bounding box [minX, minY, maxX, maxY]
            use_data_api: Use Data API if True, WFS API if False (default: True)
            **kwargs: Additional parameters for the selected API
            
        Returns:
            API response as dictionary
        """
        if use_data_api:
            return self.get_features_data_api(layer_id, bbox, **kwargs)
        else:
            return self.get_features_wfs(layer_id, bbox, **kwargs)
    
    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("VWorld API client session closed")
