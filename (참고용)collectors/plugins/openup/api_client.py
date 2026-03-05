"""OpenUp API client for collecting store sales data."""

import requests
from typing import Dict, Any, Optional, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config.scrapers.openup import OpenUpConfig
from core.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)


class OpenUpAPIClient:
    """Client for OpenUp API."""
    
    BASE_URL = "https://api.openub.com"
    
    def __init__(self):
        """Initialize OpenUp API client."""
        self.access_token = OpenUpConfig.get_access_token()
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
        self.session.mount("https://", adapter)
        
        # Set default headers (access-token은 각 요청마다 개별적으로 전달)
        # accept-encoding을 제거하거나 간단하게 설정 (requests가 자동으로 처리)
        self.session.headers.update({
            'accept': '*/*',
            'accept-language': 'ko,en;q=0.9,en-US;q=0.8',
            'content-type': 'application/json',
            'origin': 'https://pro.openub.com',
            'referer': 'https://pro.openub.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
            'sec-ch-ua': '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'cache-control': 'no-cache',
            'pragma': 'no-cache'
        })
    
    def check_coord(self, bbox: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """좌표 기반 지역 확인.
        
        Args:
            bbox: 경계 박스 정보
                {
                    "ne": {"lng": float, "lat": float},
                    "sw": {"lng": float, "lat": float}
                }
        
        Returns:
            API 응답 데이터 ({"result": "지역명"})
        """
        endpoint = f"{self.BASE_URL}/v2/pro/coord"
        
        payload = {"bbox": bbox}
        
        try:
            logger.debug(f"Checking coordinates: {bbox}")
            response = self.session.post(
                endpoint,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            raise
    
    def get_store_sales(self, store_id: str) -> Dict[str, Any]:
        """매장별 매출액 자료 조회.
        
        Args:
            store_id: 매장 ID
        
        Returns:
            매장 매출 데이터
        """
        endpoint = f"{self.BASE_URL}/v2/pro/store/sales"
        
        payload = {"storeId": store_id}
        
        headers = {
            'access-token': self.access_token
        }
        
        try:
            logger.info(f"Fetching store sales for store_id={store_id}")
            logger.debug(f"Endpoint: {endpoint}")
            logger.debug(f"Payload: {payload}")
            logger.debug(f"Access token: {self.access_token[:20] if self.access_token else 'None'}...")
            
            response = self.session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            logger.info(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            # HTTP 상태 코드 확인
            response.raise_for_status()
            
            # Content-Encoding 확인
            content_encoding = response.headers.get('Content-Encoding', '').lower()
            logger.debug(f"Content-Encoding: {content_encoding}")
            
            # 응답 내용 확인 - requests가 자동으로 압축 해제해야 함
            try:
                # response.text는 자동으로 압축 해제됨
                response_text = response.text
            except UnicodeDecodeError:
                # 압축 해제가 안 된 경우 수동 처리
                logger.warning("Response text decode failed, trying manual decompression")
                import gzip
                import zlib
                
                content = response.content
                if content_encoding == 'gzip':
                    response_text = gzip.decompress(content).decode('utf-8')
                elif content_encoding == 'deflate':
                    response_text = zlib.decompress(content).decode('utf-8')
                else:
                    # 압축 형식이 명시되지 않았지만 압축된 것 같으면 gzip 시도
                    try:
                        response_text = gzip.decompress(content).decode('utf-8')
                    except:
                        response_text = content.decode('utf-8', errors='ignore')
            
            logger.info(f"Response text length: {len(response_text)}")
            
            if not response_text or not response_text.strip():
                logger.error(f"Empty response for store_id={store_id}")
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response headers: {dict(response.headers)}")
                raise ValueError(f"Empty response from API for store_id={store_id}")
            
            # 응답 내용 로깅 (처음 200자만 - JSON 시작 확인용)
            logger.debug(f"Response text (first 200 chars): {response_text[:200]}")
            
            # JSON 파싱 시도
            try:
                # response.json() 사용 (이미 압축 해제된 text 사용)
                return response.json()
            except ValueError as json_error:
                # response.json() 실패 시 수동 파싱 시도
                try:
                    import json
                    return json.loads(response_text)
                except ValueError:
                    logger.error(f"JSON parsing failed for store_id={store_id}")
                    logger.error(f"Response status: {response.status_code}")
                    logger.error(f"Content-Encoding: {content_encoding}")
                    logger.error(f"Response text (first 500 chars): {response_text[:500]}")
                    # 원본 content도 확인
                    logger.error(f"Response content (first 100 bytes): {response.content[:100]}")
                    raise ValueError(f"Invalid JSON response: {json_error}. Response preview: {response_text[:200]}")
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for store_id={store_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response headers: {dict(e.response.headers)}")
                logger.error(f"Response text: {e.response.text[:1000]}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for store_id={store_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:1000]}")
            raise
        except ValueError as e:
            # JSON 파싱 오류
            logger.error(f"JSON parsing error for store_id={store_id}: {e}")
            raise
    
    def get_building_hash(self, cell_tokens: List[str]) -> Dict[str, Any]:
        """cellTokens를 사용하여 건물 목록 조회.
        
        Args:
            cell_tokens: 셀 토큰 리스트 (예: ["357ca4b9", "357ca4bf"])
        
        Returns:
            건물 정보 딕셔너리 (bd 키에 건물 정보 포함)
        """
        endpoint = f"{self.BASE_URL}/v2/pro/bd/hash"
        
        payload = {"cellTokens": cell_tokens}
        
        # 문서에 명시된 헤더와 정확히 일치시키기
        headers = {
            'access-token': self.access_token,
            'cache-control': 'no-cache',
            'pragma': 'no-cache'
        }
        
        try:
            logger.debug(f"Fetching building hash for cell_tokens={cell_tokens}")
            logger.debug(f"Access token: {self.access_token[:20] if self.access_token else 'None'}...")
            response = self.session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for cell_tokens={cell_tokens}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
                logger.error(f"Request headers: {headers}")
            raise
    
    def get_building_sales_by_hash(self, building_hash_key: str) -> Dict[str, Any]:
        """건물 해시 키를 사용하여 건물 단위 매출 데이터 조회.
        
        Args:
            building_hash_key: 건물 해시 키 (예: "MqR-GKWxrwNmmK")
        
        Returns:
            건물 내 매장 목록 및 매출 데이터
        """
        endpoint = f"{self.BASE_URL}/v2/pro/bd/sales"
        
        # 건물 해시 키를 사용하여 요청
        payload = {"bdHash": building_hash_key}
        
        headers = {
            'access-token': self.access_token
        }
        
        try:
            logger.debug(f"Fetching building sales for hash_key={building_hash_key}")
            response = self.session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for hash_key={building_hash_key}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            raise
    
    def get_building_sales_by_rdnu(self, rdnu: str) -> Dict[str, Any]:
        """rdnu를 사용하여 건물 단위 매출 데이터 조회.
        
        [f12 콘솔과 수집의 흐름].txt 문서에 따르면:
        - /v2/pro/bd/sales API는 rdnu 파라미터를 사용합니다
        - 건물 해시 키를 rdnu로 사용할 수 있습니다
        
        Args:
            rdnu: rdnu 값 (건물 해시 키 또는 변환된 값)
        
        Returns:
            건물 내 매장 목록 및 매출 데이터
        """
        endpoint = f"{self.BASE_URL}/v2/pro/bd/sales"
        
        # rdnu 파라미터 사용
        payload = {"rdnu": rdnu}
        
        headers = {
            'access-token': self.access_token,
            'cache-control': 'no-cache',
            'pragma': 'no-cache'
        }
        
        try:
            logger.debug(f"Fetching building sales for rdnu={rdnu}")
            response = self.session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # 응답 본문 확인
            if not response.text or not response.text.strip():
                logger.warning(f"Empty response for rdnu={rdnu}")
                return {}
            
            # JSON 파싱
            try:
                json_data = response.json()
                # None 체크
                if json_data is None:
                    logger.warning(f"Response JSON is None for rdnu={rdnu}")
                    return {}
                return json_data
            except ValueError as json_error:
                logger.error(f"JSON decode error for rdnu={rdnu}: {json_error}")
                logger.error(f"Response text (first 500 chars): {response.text[:500]}")
                return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for rdnu={rdnu}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            raise
    
    def get_building_sales(self, building_address: str) -> Dict[str, Any]:
        """건물단위 매출액 자료 조회.
        
        Note: 실제 API 요청 형식은 문서를 참조하여 확인 필요.
        현재는 주소 기반으로 요청하는 것으로 추정됩니다.
        
        Args:
            building_address: 건물 주소
        
        Returns:
            건물 내 매장 목록 및 매출 데이터
        """
        endpoint = f"{self.BASE_URL}/v2/pro/bd/sales"
        
        # 문서 확인 결과, 실제 요청 형식은 주소나 다른 파라미터일 수 있음
        # 일단 주소를 사용하도록 구현 (실제 API 동작 확인 후 수정 필요)
        payload = {"address": building_address}
        
        headers = {
            'access-token': self.access_token
        }
        
        try:
            logger.debug(f"Fetching building sales for address={building_address}")
            response = self.session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for address={building_address}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            raise
    
    def get_building_gp(self, hash_keys: List[str]) -> Dict[str, Any]:
        """건물 해시 키를 사용하여 건물별 매출 정보 조회.
        
        Args:
            hash_keys: 건물 해시 키 리스트 (예: ["357ca4b9", "357ca4bf"])
        
        Returns:
            건물별 매출 정보 (sales, count, isNewOpen)
        """
        endpoint = f"{self.BASE_URL}/v2/pro/gp"
        
        payload = {"hashKeys": hash_keys}
        
        headers = {
            'access-token': self.access_token
        }
        
        try:
            logger.debug(f"Fetching building gp for hash_keys={hash_keys}")
            response = self.session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for hash_keys={hash_keys}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            raise
    
    def create_district_rank(
        self,
        epa: str,
        center: Dict[str, float],
        prompt_id: int = 182
    ) -> Dict[str, Any]:
        """지역 랭킹 생성.
        
        Args:
            epa: 인코딩된 폴리곤 데이터
            center: 중심 좌표 {"lng": float, "lat": float}
            prompt_id: 프롬프트 ID (기본값: 182)
        
        Returns:
            랭킹 생성 결과 ({"rankId": int, "status": bool})
        """
        endpoint = f"{self.BASE_URL}/v2/pro/district/rank/create"
        
        payload = {
            "epa": epa,
            "center": center,
            "promptId": prompt_id
        }
        
        headers = {
            'access-token': self.access_token
        }
        
        try:
            logger.debug(f"Creating district rank for center={center}")
            response = self.session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            raise
    
    def close(self):
        """Close the session."""
        if hasattr(self, 'session'):
            self.session.close()
