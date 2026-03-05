"""SGIS API client for making requests."""

import time
import requests
from typing import Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config.scrapers.sgis import SGISConfig
from core.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)


class SGISAPIClient:
    """Client for SGIS API requests."""
    
    def __init__(self):
        """Initialize SGIS API client."""
        self.base_url = SGISConfig.get_base_url()
        self.timeout = settings.request_timeout
        self.max_retries = settings.max_retries
        self.retry_delay = settings.retry_delay
        
        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers and cookies
        self._update_session_auth()
    
    def _update_session_auth(self):
        """Update session with authentication headers and credentials."""
        headers = SGISConfig.get_headers()
        credentials = SGISConfig.get_credentials()
        
        self.session.headers.update(headers)
        
        # Store credentials for OAuth or other authentication methods
        self.consumer_key = credentials.get('consumer_key', '')
        self.consumer_secret = credentials.get('consumer_secret', '')
    
    def _generate_timestamp(self) -> str:
        """Generate timestamp for requests.
        
        Returns:
            Timestamp string in format: YYYYMMDDHHMMSSmmm
        """
        return str(int(time.time() * 1000))
    
    def get_poi_company_density(
        self,
        theme_cd: int = 0,
        year: int = 2023,
        adm_cd: str = "11040",
        data_type: int = 3,
        params: Optional[Dict[str, Any]] = None,
        bounds: Optional[Dict[str, float]] = None,
        zoom_level: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get POI company density data for technical business map.
        
        Args:
            theme_cd: 테마 코드 (기본값: 0)
            year: 연도 (기본값: 2023)
            adm_cd: 행정구역 코드 (기본값: "11040" - 서울시 종로구)
            data_type: 데이터 타입 (기본값: 3)
            params: 추가 요청 파라미터
            bounds: Map bounds (north, south, east, west)
            zoom_level: Map zoom level
            
        Returns:
            API response as dictionary
        """
        endpoint = f"{self.base_url}/ServiceAPI/technicalBiz/getPoiCompanyDensity.json"
        
        # Add timestamp to headers
        headers = {
            'ts': self._generate_timestamp()
        }
        
        # 필수 파라미터 설정
        request_params = {
            'theme_cd': theme_cd,
            'year': year,
            'adm_cd': adm_cd,
            'data_type': data_type
        }
        
        # 추가 파라미터 병합
        if params:
            request_params.update(params)
        
        # Add map bounds if provided
        if bounds:
            request_params.update({
                'north': bounds.get('north', 0),
                'south': bounds.get('south', 0),
                'east': bounds.get('east', 0),
                'west': bounds.get('west', 0)
            })
        
        if zoom_level is not None:
            request_params['zoom'] = zoom_level
        
        try:
            logger.info(f"Requesting POI company density data from {endpoint}")
            logger.debug(f"Request parameters: {request_params}")
            
            response = self.session.post(
                endpoint,
                data=request_params,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            logger.info("Successfully retrieved POI company density data")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error requesting POI company density: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            raise
        except ValueError as e:
            logger.error(f"Error parsing JSON response: {e}")
            raise
    
    def make_request(
        self,
        endpoint: str,
        method: str = "POST",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a generic API request.
        
        Args:
            endpoint: API endpoint (relative or full URL)
            method: HTTP method (POST, GET, etc.)
            params: URL parameters
            data: Form data
            json_data: JSON data
            
        Returns:
            API response as dictionary
        """
        # Construct full URL if relative
        if not endpoint.startswith('http'):
            endpoint = f"{self.base_url}{endpoint}"
        
        # Add timestamp to headers
        headers = {
            'ts': self._generate_timestamp()
        }
        
        try:
            logger.info(f"Making {method} request to {endpoint}")
            
            if method.upper() == "GET":
                response = self.session.get(
                    endpoint,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )
            elif method.upper() == "POST":
                if json_data:
                    response = self.session.post(
                        endpoint,
                        json=json_data,
                        params=params,
                        headers=headers,
                        timeout=self.timeout
                    )
                else:
                    response = self.session.post(
                        endpoint,
                        data=data or params,
                        headers=headers,
                        timeout=self.timeout
                    )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # Try to parse JSON, fallback to text
            try:
                data = response.json()
            except ValueError:
                data = {"text": response.text}
            
            logger.info(f"Successfully completed {method} request to {endpoint}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to {endpoint}: {e}")
            raise
    
    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("SGIS API client session closed")

