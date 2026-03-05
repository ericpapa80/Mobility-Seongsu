"""Foottraffic API client for making requests."""

import time
import requests
from typing import Dict, Any, Optional, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config.scrapers.foottraffic import FoottrafficConfig
from core.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)


class FoottrafficAPIClient:
    """Client for 골목길 유동인구 API requests."""
    
    def __init__(self):
        """Initialize Foottraffic API client."""
        self.base_url = FoottrafficConfig.get_base_url()
        self.endpoint = FoottrafficConfig.get_endpoint()
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
        
        # Set default headers
        self._update_session_headers()
        
        # Initialize session by visiting main page first
        self._initialize_session()
    
    def _update_session_headers(self):
        """Update session with request headers."""
        headers = FoottrafficConfig.get_headers()
        self.session.headers.update(headers)
    
    def _initialize_session(self):
        """Initialize session by visiting the main page to get cookies."""
        try:
            logger.debug("Initializing session by visiting main page...")
            main_page_url = f"{self.base_url}/commercialArea/commercialArea.do"
            response = self.session.get(main_page_url, timeout=self.timeout)
            response.raise_for_status()
            logger.debug("Session initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize session: {e}. Continuing anyway...")
    
    def get_foottraffic_data(
        self,
        minx: float,
        miny: float,
        maxx: float,
        maxy: float,
        wkt: str = "",
        dayweek: int = 1,
        agrde: str = "00",
        tmzon: str = "06",
        ext: str = "ext",
        signguCd: int = 11
    ) -> List[Dict[str, Any]]:
        """Get 골목길 유동인구 data.
        
        Args:
            minx: 최소 X 좌표
            miny: 최소 Y 좌표
            maxx: 최대 X 좌표
            maxy: 최대 Y 좌표
            wkt: WKT 형식의 공간 정보 (기본값: 빈 문자열)
            dayweek: 요일 구분 (1: 주중, 2: 주말, 기본값: 1)
            agrde: 연령대 ("00": 전체, "10": 10대, "20": 20대, "30": 30대, "40": 40대, "50": 50대, "60": 60대이상, 기본값: "00")
            tmzon: 시간대 ("00": 종일, "01": 00~05, "02": 06~10, "03": 11~13, "04": 14~16, "05": 17~20, "06": 21~23, 기본값: "06")
            ext: 확장 파라미터 (기본값: "ext")
            signguCd: 시군구 코드 (기본값: 11 - 서울시)
            
        Returns:
            API response as list of dictionaries
        """
        url = f"{self.base_url}{self.endpoint}"
        
        # Prepare form data
        # agrde는 문자열 형식으로 전송 ("00", "10", "20", etc.)
        form_data = {
            'minx': str(minx),
            'miny': str(miny),
            'maxx': str(maxx),
            'maxy': str(maxy),
            'wkt': wkt,
            'dayweek': str(dayweek),
            'agrde': agrde,  # 문자열 그대로 사용
            'tmzon': tmzon,
            'ext': ext,
            'signguCd': str(signguCd)
        }
        
        try:
            logger.info(f"Requesting 골목길 유동인구 data from {url}")
            logger.debug(f"Request parameters: {form_data}")
            
            response = self.session.post(
                url,
                data=form_data,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Check content type and parse response
            content_type = response.headers.get('content-type', '').lower()
            logger.debug(f"Response content-type: {content_type}")
            logger.debug(f"Response status code: {response.status_code}")
            
            # Try to parse JSON response
            try:
                data = response.json()
            except ValueError as json_error:
                # If JSON parsing fails, log the response text
                response_text = response.text[:1000]  # First 1000 chars
                logger.error(f"Failed to parse JSON response. Response text (first 1000 chars): {response_text}")
                logger.error(f"Full response headers: {dict(response.headers)}")
                raise ValueError(f"Invalid JSON response: {json_error}. Response text: {response_text[:200]}")
            
            # Ensure data is a list
            if isinstance(data, dict):
                # If response is wrapped in a dict, try to extract list
                if 'data' in data:
                    data = data['data']
                elif 'result' in data:
                    data = data['result']
                else:
                    # If no list found, wrap in list
                    data = [data]
            elif not isinstance(data, list):
                data = [data]
            
            logger.info(f"Successfully retrieved {len(data)} 골목길 유동인구 records")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error requesting 골목길 유동인구 data: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            raise
        except ValueError as e:
            logger.error(f"Error parsing JSON response: {e}")
            raise
    
    def get_seongsu_foottraffic(
        self,
        dayweek: int = 1,
        agrde: str = "00",
        tmzon: str = "06"
    ) -> List[Dict[str, Any]]:
        """Get 성수동 골목길 유동인구 data.
        
        Args:
            dayweek: 요일 구분 (1: 주중, 2: 주말, 기본값: 1)
            agrde: 연령대 ("00": 전체, "10": 10대, "20": 20대, "30": 30대, "40": 40대, "50": 50대, "60": 60대이상, 기본값: "00")
            tmzon: 시간대 ("00": 종일, "01": 00~05, "02": 06~10, "03": 11~13, "04": 14~16, "05": 17~20, "06": 21~23, 기본값: "06")
            
        Returns:
            API response as list of dictionaries
        """
        bounds = FoottrafficConfig.get_seongsu_bounds()
        return self.get_foottraffic_data(
            minx=bounds['minx'],
            miny=bounds['miny'],
            maxx=bounds['maxx'],
            maxy=bounds['maxy'],
            dayweek=dayweek,
            agrde=agrde,
            tmzon=tmzon
        )
    
    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("Foottraffic API client session closed")

