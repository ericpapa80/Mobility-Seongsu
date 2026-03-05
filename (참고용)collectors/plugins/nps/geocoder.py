"""Geocoding module for converting addresses to coordinates."""

import sys
import time
import requests
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Tuple
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.logger import get_logger

logger = get_logger(__name__)


class Geocoder:
    """Geocoder for converting Korean addresses to coordinates.
    
    Supports multiple geocoding services:
    - Kakao Local API (default)
    - Vworld API (public data)
    - Naver Local Search API
    """
    
    def __init__(self, service: str = "kakao"):
        """Initialize geocoder.
        
        Args:
            service: Geocoding service to use ("kakao", "vworld", or "naver")
        """
        self.service = service
        self.session = requests.Session()
        
        # Retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        if service == "kakao":
            self._init_kakao()
        elif service == "vworld":
            self._init_vworld()
        elif service == "naver":
            self._init_naver()
        else:
            raise ValueError(f"Unsupported geocoding service: {service}")
    
    def _init_kakao(self):
        """Initialize Kakao Local API."""
        import os
        # Try KAKAO_REST_API_KEY first, then fallback to KAKAO_API_KEY
        self.api_key = os.getenv("KAKAO_REST_API_KEY", "")
        
        # If not found, try KAKAO_API_KEY and remove "KakaoAK " prefix if present
        if not self.api_key:
            kakao_key = os.getenv("KAKAO_API_KEY", "")
            if kakao_key:
                # Remove "KakaoAK " prefix if present
                self.api_key = kakao_key.replace("KakaoAK ", "").strip()
        
        self.base_url = "https://dapi.kakao.com/v2/local/search/address.json"
        
        if not self.api_key:
            logger.warning("Kakao API key not found (KAKAO_REST_API_KEY or KAKAO_API_KEY). Geocoding may not work.")
        
        self.session.headers.update({
            "Authorization": f"KakaoAK {self.api_key}",
            "Content-Type": "application/json"
        })
    
    def _init_vworld(self):
        """Initialize Vworld API."""
        import os
        self.api_key = os.getenv("VWORLD_API_KEY", "")
        self.base_url = "http://api.vworld.kr/req/address"
        
        if not self.api_key:
            logger.warning("VWORLD_API_KEY not found. Geocoding may not work.")
    
    def _init_naver(self):
        """Initialize Naver Local Search API."""
        import os
        self.client_id = os.getenv("NAVER_CLIENT_ID", "")
        self.client_secret = os.getenv("NAVER_CLIENT_SECRET", "")
        self.base_url = "https://openapi.naver.com/v1/search/local.json"
        
        if not self.client_id or not self.client_secret:
            logger.warning("NAVER_CLIENT_ID or NAVER_CLIENT_SECRET not found. Geocoding may not work.")
        
        self.session.headers.update({
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        })
    
    def geocode(self, address: str, keyword: Optional[str] = None, delay: float = 0.1) -> Optional[Dict[str, float]]:
        """Convert address to coordinates.
        
        Args:
            address: Address string to geocode
            keyword: Optional keyword (business name) to improve accuracy
            delay: Delay between requests (seconds) to avoid rate limiting
            
        Returns:
            Dictionary with 'x' (longitude) and 'y' (latitude) keys, or None if failed
        """
        if not address or pd.isna(address):
            return None
        
        address = str(address).strip()
        if not address:
            return None
        
        time.sleep(delay)  # Rate limiting
        
        if self.service == "kakao":
            return self._geocode_kakao(address, keyword=keyword)
        elif self.service == "vworld":
            return self._geocode_vworld(address)
        elif self.service == "naver":
            return self._geocode_naver(address, keyword=keyword)
    
    def _geocode_kakao(self, address: str, keyword: Optional[str] = None) -> Optional[Dict[str, float]]:
        """Geocode using Kakao Local API.
        
        주소가 불완전한 경우(번지 없음) 상호명을 우선 활용하여 더 정확한 위치를 찾습니다.
        
        Args:
            address: Address string (may be incomplete without building number)
            keyword: Business name/keyword (preferred for better accuracy)
            
        Returns:
            Dictionary with 'x' (longitude) and 'y' (latitude) keys, or None
        """
        if not self.api_key:
            logger.warning("Kakao API key not configured")
            return None
        
        # Strategy 1: If keyword (business name) provided, prioritize keyword search
        # 주소가 불완전하므로 상호명을 우선 활용
        if keyword:
            keyword = str(keyword).strip()
            
            # Strategy 1-1: Keyword + Address combination (most accurate)
            try:
                keyword_url = "https://dapi.kakao.com/v2/local/search/keyword.json"
                # 상호명과 주소를 함께 검색하여 정확도 향상
                query = f"{keyword} {address}".strip()
                params = {"query": query, "size": 15}  # 여러 결과 확인
                
                response = self.session.get(keyword_url, params=params, timeout=5)
                response.raise_for_status()
                
                data = response.json()
                documents = data.get("documents", [])
                
                if documents:
                    # 주소가 일치하는 결과를 우선 선택
                    best_match = None
                    best_score = 0
                    
                    for doc in documents:
                        # 도로명 주소 또는 지번 주소 확인
                        road_addr = doc.get("road_address", {}).get("address_name", "")
                        jibun_addr = doc.get("address", {}).get("address_name", "")
                        doc_address = road_addr or jibun_addr
                        
                        # 주소 일치도 계산
                        score = 0
                        address_parts = address.split()
                        for part in address_parts:
                            if part in doc_address:
                                score += 1
                        
                        # 상호명도 확인 (place_name에 포함되는지)
                        place_name = doc.get("place_name", "")
                        if keyword in place_name or place_name in keyword:
                            score += 2  # 상호명 일치 시 가중치 증가
                        
                        if score > best_score:
                            best_score = score
                            best_match = doc
                    
                    # 최고 점수 결과 사용
                    if best_match:
                        x = float(best_match.get("x", 0))
                        y = float(best_match.get("y", 0))
                        
                        if x != 0 and y != 0:
                            return {"x": x, "y": y, "lon": x, "lat": y}
                    
                    # 매칭 실패 시 첫 번째 결과라도 사용
                    if documents:
                        result = documents[0]
                        x = float(result.get("x", 0))
                        y = float(result.get("y", 0))
                        if x != 0 and y != 0:
                            return {"x": x, "y": y, "lon": x, "lat": y}
            except Exception as e:
                logger.debug(f"Keyword+Address search failed for '{keyword} {address}': {e}")
            
            # Strategy 1-2: Keyword only (if address is incomplete)
            try:
                keyword_url = "https://dapi.kakao.com/v2/local/search/keyword.json"
                params = {"query": keyword, "size": 10}
                
                response = self.session.get(keyword_url, params=params, timeout=5)
                response.raise_for_status()
                
                data = response.json()
                documents = data.get("documents", [])
                
                if documents:
                    # 주소가 포함된 결과를 우선 선택
                    for doc in documents:
                        road_addr = doc.get("road_address", {}).get("address_name", "")
                        jibun_addr = doc.get("address", {}).get("address_name", "")
                        doc_address = road_addr or jibun_addr
                        
                        # 주소의 주요 부분(시군구, 동)이 일치하는지 확인
                        if address and any(part in doc_address for part in address.split()[:3]):
                            x = float(doc.get("x", 0))
                            y = float(doc.get("y", 0))
                            if x != 0 and y != 0:
                                return {"x": x, "y": y, "lon": x, "lat": y}
                    
                    # 주소 매칭 실패 시 첫 번째 결과 사용
                    result = documents[0]
                    x = float(result.get("x", 0))
                    y = float(result.get("y", 0))
                    if x != 0 and y != 0:
                        return {"x": x, "y": y, "lon": x, "lat": y}
            except Exception as e:
                logger.debug(f"Keyword-only search failed for '{keyword}': {e}")
        
        # Strategy 2: Fallback to address search (if keyword not available or failed)
        try:
            params = {"query": address}
            response = self.session.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            documents = data.get("documents", [])
            
            if documents:
                result = documents[0]
                x = float(result.get("x", 0))
                y = float(result.get("y", 0))
                
                if x != 0 and y != 0:
                    return {"x": x, "y": y, "lon": x, "lat": y}
        except Exception as e:
            logger.debug(f"Address search failed for '{address}': {e}")
        
        logger.debug(f"No geocoding results for address: {address}, keyword: {keyword}")
        return None
    
    def _geocode_vworld(self, address: str) -> Optional[Dict[str, float]]:
        """Geocode using Vworld API.
        
        Vworld API는 주소 기반 지오코딩이므로 더 정확할 수 있습니다.
        
        Args:
            address: Address string
            
        Returns:
            Dictionary with 'x' (longitude) and 'y' (latitude) keys, or None
        """
        if not self.api_key:
            logger.warning("Vworld API key not configured")
            return None
        
        # Strategy 1: 도로명 주소로 시도
        try:
            params = {
                "service": "address",
                "request": "getcoord",
                "version": "2.0",
                "crs": "epsg:4326",
                "address": address,
                "format": "json",
                "type": "road",  # 도로명 주소
                "key": self.api_key
            }
            
            response = self.session.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            response_data = data.get("response", {})
            
            if response_data.get("status") == "OK":
                result = response_data.get("result", {})
                point = result.get("point", {})
                
                x = float(point.get("x", 0))
                y = float(point.get("y", 0))
                
                if x != 0 and y != 0:
                    return {"x": x, "y": y, "lon": x, "lat": y}
        except Exception as e:
            logger.debug(f"Vworld road address geocoding failed for '{address}': {e}")
        
        # Strategy 2: 지번 주소로 시도
        try:
            params = {
                "service": "address",
                "request": "getcoord",
                "version": "2.0",
                "crs": "epsg:4326",
                "address": address,
                "format": "json",
                "type": "parcel",  # 지번 주소
                "key": self.api_key
            }
            
            response = self.session.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            response_data = data.get("response", {})
            
            if response_data.get("status") == "OK":
                result = response_data.get("result", {})
                point = result.get("point", {})
                
                x = float(point.get("x", 0))
                y = float(point.get("y", 0))
                
                if x != 0 and y != 0:
                    return {"x": x, "y": y, "lon": x, "lat": y}
        except Exception as e:
            logger.debug(f"Vworld parcel address geocoding failed for '{address}': {e}")
        
        logger.debug(f"Vworld geocoding failed for '{address}'")
        return None
    
    def _geocode_naver(self, address: str, keyword: Optional[str] = None) -> Optional[Dict[str, float]]:
        """Geocode using Naver Local Search API.
        
        네이버 Local Search API는 장소 검색 API이므로 상호명과 주소를 함께 사용합니다.
        
        Args:
            address: Address string
            keyword: Business name/keyword (preferred for better accuracy)
            
        Returns:
            Dictionary with 'x' (longitude) and 'y' (latitude) keys, or None
        """
        if not self.client_id or not self.client_secret:
            logger.warning("Naver API credentials not configured")
            return None
        
        # Strategy 1: Keyword + Address combination (most accurate)
        if keyword:
            keyword = str(keyword).strip()
            try:
                # 상호명과 주소를 함께 검색
                query = f"{keyword} {address}".strip()
                params = {
                    "query": query,
                    "display": 10,  # 최대 10개 결과 확인
                    "sort": "random"  # 정확도 순
                }
                
                response = self.session.get(self.base_url, params=params, timeout=5)
                response.raise_for_status()
                
                data = response.json()
                items = data.get("items", [])
                
                if items:
                    # 주소가 일치하는 결과를 우선 선택
                    best_match = None
                    best_score = 0
                    
                    for item in items:
                        # 주소 정보 확인
                        road_addr = item.get("roadAddress", "")
                        jibun_addr = item.get("address", "")
                        doc_address = road_addr or jibun_addr
                        
                        # 주소 일치도 계산
                        score = 0
                        address_parts = address.split()
                        for part in address_parts:
                            if part in doc_address:
                                score += 1
                        
                        # 상호명 확인
                        title = item.get("title", "").replace("<b>", "").replace("</b>", "")
                        if keyword in title or title in keyword:
                            score += 2
                        
                        # 성수동 지역 확인 (주소에 성수동 포함)
                        if "성수동" in doc_address or "성수" in doc_address:
                            score += 3  # 성수동 지역 가중치
                        
                        if score > best_score:
                            best_score = score
                            best_match = item
                    
                    # 최고 점수 결과 사용
                    if best_match:
                        mapx = best_match.get("mapx", "")
                        mapy = best_match.get("mapy", "")
                        
                        if mapx and mapy:
                            # 네이버 좌표는 KATEC 좌표계이므로 WGS84로 변환 필요
                            # 간단한 변환 (정확도는 약간 떨어질 수 있음)
                            try:
                                x = float(mapx) / 10000000.0  # 경도
                                y = float(mapy) / 10000000.0  # 위도
                                
                                if x != 0 and y != 0:
                                    return {"x": x, "y": y, "lon": x, "lat": y}
                            except (ValueError, TypeError):
                                pass
                    
                    # 매칭 실패 시 첫 번째 결과 사용
                    if items:
                        item = items[0]
                        mapx = item.get("mapx", "")
                        mapy = item.get("mapy", "")
                        if mapx and mapy:
                            try:
                                x = float(mapx) / 10000000.0
                                y = float(mapy) / 10000000.0
                                if x != 0 and y != 0:
                                    return {"x": x, "y": y, "lon": x, "lat": y}
                            except (ValueError, TypeError):
                                pass
            except Exception as e:
                logger.debug(f"Naver keyword+address search failed for '{keyword} {address}': {e}")
            
            # Strategy 2: Keyword only
            try:
                params = {
                    "query": keyword,
                    "display": 10,
                    "sort": "random"
                }
                
                response = self.session.get(self.base_url, params=params, timeout=5)
                response.raise_for_status()
                
                data = response.json()
                items = data.get("items", [])
                
                if items:
                    # 주소가 포함된 결과를 우선 선택
                    for item in items:
                        road_addr = item.get("roadAddress", "")
                        jibun_addr = item.get("address", "")
                        doc_address = road_addr or jibun_addr
                        
                        # 주소의 주요 부분이 일치하는지 확인
                        if address and any(part in doc_address for part in address.split()[:3]):
                            mapx = item.get("mapx", "")
                            mapy = item.get("mapy", "")
                            if mapx and mapy:
                                try:
                                    x = float(mapx) / 10000000.0
                                    y = float(mapy) / 10000000.0
                                    if x != 0 and y != 0:
                                        return {"x": x, "y": y, "lon": x, "lat": y}
                                except (ValueError, TypeError):
                                    pass
                    
                    # 주소 매칭 실패 시 첫 번째 결과 사용
                    item = items[0]
                    mapx = item.get("mapx", "")
                    mapy = item.get("mapy", "")
                    if mapx and mapy:
                        try:
                            x = float(mapx) / 10000000.0
                            y = float(mapy) / 10000000.0
                            if x != 0 and y != 0:
                                return {"x": x, "y": y, "lon": x, "lat": y}
                        except (ValueError, TypeError):
                            pass
            except Exception as e:
                logger.debug(f"Naver keyword-only search failed for '{keyword}': {e}")
        
        # Strategy 3: Address only (with 성수동 keyword)
        try:
            # 성수동 키워드를 명시적으로 추가
            query = f"성수동 {address}".strip()
            params = {
                "query": query,
                "display": 5,
                "sort": "random"
            }
            
            response = self.session.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            items = data.get("items", [])
            
            if items:
                item = items[0]
                mapx = item.get("mapx", "")
                mapy = item.get("mapy", "")
                if mapx and mapy:
                    try:
                        x = float(mapx) / 10000000.0
                        y = float(mapy) / 10000000.0
                        if x != 0 and y != 0:
                            return {"x": x, "y": y, "lon": x, "lat": y}
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            logger.debug(f"Naver address search failed for '{address}': {e}")
        
        logger.debug(f"Naver geocoding failed for address: {address}, keyword: {keyword}")
        return None
    
    def geocode_batch(self, addresses: list, keywords: Optional[list] = None, delay: float = 0.1) -> Dict[str, Optional[Dict[str, float]]]:
        """Geocode multiple addresses.
        
        Args:
            addresses: List of address strings
            keywords: Optional list of keywords (business names) corresponding to addresses
            delay: Delay between requests (seconds)
            
        Returns:
            Dictionary mapping address to coordinates (or None if failed)
        """
        results = {}
        total = len(addresses)
        
        if keywords is None:
            keywords = [None] * total
        
        for i, (address, keyword) in enumerate(zip(addresses, keywords), 1):
            if i % 100 == 0:
                logger.info(f"Geocoding progress: {i}/{total} ({i/total*100:.1f}%)")
            
            results[address] = self.geocode(address, keyword=keyword, delay=delay)
        
        success_count = sum(1 for v in results.values() if v is not None)
        logger.info(f"Geocoding completed: {success_count}/{total} successful")
        
        return results
    
    def close(self):
        """Close session."""
        self.session.close()
        logger.info("Geocoder closed")

