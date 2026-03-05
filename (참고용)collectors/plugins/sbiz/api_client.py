"""SBIZ API client for 소상공인시장진흥공단 상가(상권)정보 API."""

import requests
from typing import Dict, Any, Optional, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config.scrapers.sbiz import SBIZConfig
from core.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)


class SBIZAPIClient:
    """Client for 소상공인시장진흥공단 상가(상권)정보 API."""
    
    BASE_URL = "http://apis.data.go.kr/B553077/api/open/sdsc2"
    
    def __init__(self):
        """Initialize SBIZ API client."""
        self.service_key = SBIZConfig.get_service_key()
        self.timeout = settings.request_timeout
        self.max_retries = settings.max_retries
        self.retry_delay = settings.retry_delay
        
        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def get_stores_by_area(
        self,
        area_cd: str,
        inds_lcls_cd: Optional[str] = None,
        inds_mcls_cd: Optional[str] = None,
        inds_scls_cd: Optional[str] = None,
        page_no: int = 1,
        num_of_rows: int = 1000,
        data_type: str = "json"
    ) -> Dict[str, Any]:
        """상권 내 상가업소 조회.
        
        Args:
            area_cd: 상권 번호
            inds_lcls_cd: 상권업종 대분류코드 (옵션)
            inds_mcls_cd: 상권업종 중분류코드 (옵션)
            inds_scls_cd: 상권업종 소분류코드 (옵션)
            page_no: 페이지 번호
            num_of_rows: 페이지당 건수 (최대 1000)
            data_type: 데이터 유형 (json, xml)
            
        Returns:
            API 응답 데이터
        """
        endpoint = f"{self.BASE_URL}/storeListInArea"
        
        params = {
            'serviceKey': self.service_key,
            'key': area_cd,
            'numOfRows': min(num_of_rows, 1000),
            'pageNo': page_no,
            'type': data_type
        }
        
        # 업종 필터 추가
        if inds_lcls_cd:
            params['indsLclsCd'] = inds_lcls_cd
        if inds_mcls_cd:
            params['indsMclsCd'] = inds_mcls_cd
        if inds_scls_cd:
            params['indsSclsCd'] = inds_scls_cd
        
        try:
            logger.info(f"Requesting stores for area_cd={area_cd}, page={page_no}")
            response = self.session.get(endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            if data_type == "json":
                return response.json()
            else:
                return response.text
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            raise
    
    def get_all_stores_by_area(
        self,
        area_cd: str,
        inds_lcls_cd: Optional[str] = None,
        inds_mcls_cd: Optional[str] = None,
        inds_scls_cd: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """상권의 모든 상가업소 조회 (페이지네이션 처리).
        
        Args:
            area_cd: 상권 번호
            inds_lcls_cd: 상권업종 대분류코드 (옵션)
            inds_mcls_cd: 상권업종 중분류코드 (옵션)
            inds_scls_cd: 상권업종 소분류코드 (옵션)
            
        Returns:
            모든 상가업소 데이터 리스트
        """
        all_stores = []
        page_no = 1
        
        while True:
            response = self.get_stores_by_area(
                area_cd=area_cd,
                inds_lcls_cd=inds_lcls_cd,
                inds_mcls_cd=inds_mcls_cd,
                inds_scls_cd=inds_scls_cd,
                page_no=page_no,
                num_of_rows=1000
            )
            
            # 응답 구조 확인
            if isinstance(response, dict):
                body = response.get('body', {})
                items = body.get('items', [])
                
                # items가 리스트인 경우
                if isinstance(items, list):
                    if items:
                        all_stores.extend(items)
                    else:
                        break
                elif isinstance(items, dict):
                    item = items.get('item')
                    if item:
                        if isinstance(item, list):
                            all_stores.extend(item)
                        else:
                            all_stores.append(item)
                    else:
                        break
                
                # totalCount 확인
                total_count = body.get('totalCount')
                if total_count is not None:
                    total_count = int(total_count)
                    if len(all_stores) >= total_count:
                        break
                
                if not items:
                    break
                    
                page_no += 1
            else:
                break
        
        logger.info(f"Total stores collected: {len(all_stores)}")
        return all_stores
    
    def get_stores_by_dong(
        self,
        adong_cd: str,
        inds_lcls_cd: Optional[str] = None,
        inds_mcls_cd: Optional[str] = None,
        inds_scls_cd: Optional[str] = None,
        page_no: int = 1,
        num_of_rows: int = 1000,
        data_type: str = "json",
        div_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """행정동/시군구 단위 상가업소 조회.
        
        Args:
            adong_cd: 행정동 코드 또는 시군구 코드
            inds_lcls_cd: 상권업종 대분류코드 (옵션)
            inds_mcls_cd: 상권업종 중분류코드 (옵션)
            inds_scls_cd: 상권업종 소분류코드 (옵션)
            page_no: 페이지 번호
            num_of_rows: 페이지당 건수 (최대 1000)
            data_type: 데이터 유형 (json, xml)
            div_id: 구분ID (adongCd, signguCd, ctprvnCd). None이면 자동 판단
            
        Returns:
            API 응답 데이터
        """
        endpoint = f"{self.BASE_URL}/storeListInDong"
        
        # divId 자동 판단: 코드 길이로 추정
        # 행정동: 8자리, 시군구: 5자리, 시도: 2자리
        if div_id is None:
            if len(adong_cd) == 8:
                div_id = 'adongCd'
            elif len(adong_cd) == 5:
                div_id = 'signguCd'
            elif len(adong_cd) == 2:
                div_id = 'ctprvnCd'
            else:
                div_id = 'adongCd'  # 기본값
        
        params = {
            'serviceKey': self.service_key,
            'divId': div_id,
            'key': adong_cd,
            'numOfRows': min(num_of_rows, 1000),
            'pageNo': page_no,
            'type': data_type
        }
        
        # 업종 필터 추가
        if inds_lcls_cd:
            params['indsLclsCd'] = inds_lcls_cd
        if inds_mcls_cd:
            params['indsMclsCd'] = inds_mcls_cd
        if inds_scls_cd:
            params['indsSclsCd'] = inds_scls_cd
        
        try:
            logger.info(f"Requesting stores for adong_cd={adong_cd}, page={page_no}")
            response = self.session.get(endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            if data_type == "json":
                return response.json()
            else:
                return response.text
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            raise
    
    def get_all_stores_by_dong(
        self,
        adong_cd: str,
        inds_lcls_cd: Optional[str] = None,
        inds_mcls_cd: Optional[str] = None,
        inds_scls_cd: Optional[str] = None,
        div_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """행정동/시군구의 모든 상가업소 조회 (페이지네이션 처리).
        
        Args:
            adong_cd: 행정동 코드 또는 시군구 코드
            inds_lcls_cd: 상권업종 대분류코드 (옵션)
            inds_mcls_cd: 상권업종 중분류코드 (옵션)
            inds_scls_cd: 상권업종 소분류코드 (옵션)
            div_id: 구분ID (adongCd, signguCd, ctprvnCd). None이면 자동 판단
            
        Returns:
            모든 상가업소 데이터 리스트
        """
        all_stores = []
        page_no = 1
        
        while True:
            response = self.get_stores_by_dong(
                adong_cd=adong_cd,
                inds_lcls_cd=inds_lcls_cd,
                inds_mcls_cd=inds_mcls_cd,
                inds_scls_cd=inds_scls_cd,
                page_no=page_no,
                num_of_rows=1000,
                div_id=div_id
            )
            
            # 응답 구조 확인
            if isinstance(response, dict):
                # 실제 응답 구조: response['body']['items'] (리스트)
                body = response.get('body', {})
                items = body.get('items', [])
                
                # items가 리스트인 경우
                if isinstance(items, list):
                    if items:
                        all_stores.extend(items)
                    else:
                        # items가 빈 리스트면 더 이상 데이터 없음
                        break
                elif isinstance(items, dict):
                    # items가 dict인 경우 (단일 item 또는 item 필드)
                    item = items.get('item')
                    if item:
                        if isinstance(item, list):
                            all_stores.extend(item)
                        else:
                            all_stores.append(item)
                    else:
                        # item이 없으면 더 이상 데이터 없음
                        break
                
                # totalCount 확인 (있으면 사용)
                total_count = body.get('totalCount')
                if total_count is not None:
                    total_count = int(total_count)
                    if len(all_stores) >= total_count:
                        break
                
                # items가 비어있으면 종료
                if not items:
                    break
                    
                page_no += 1
            else:
                break
        
        logger.info(f"Total stores collected: {len(all_stores)}")
        return all_stores
    
    def get_stores_by_date(
        self,
        date: str,
        inds_lcls_cd: Optional[str] = None,
        inds_mcls_cd: Optional[str] = None,
        inds_scls_cd: Optional[str] = None,
        page_no: int = 1,
        num_of_rows: int = 1000,
        data_type: str = "json"
    ) -> Dict[str, Any]:
        """수정일자기준 상가업소 조회.
        
        입력 일자를 기준으로 수정속성을 포함한 업소목록 조회(삭제된 업소 포함).
        변경구분 필드를 통해 신규 등록, 수정, 삭제 등을 구분할 수 있습니다.
        
        Args:
            date: 일자 (YYYYMMDD 형식, 예: 20221202)
            inds_lcls_cd: 상권업종 대분류코드 (옵션)
            inds_mcls_cd: 상권업종 중분류코드 (옵션)
            inds_scls_cd: 상권업종 소분류코드 (옵션)
            page_no: 페이지 번호
            num_of_rows: 페이지당 건수 (최대 1000)
            data_type: 데이터 유형 (json, xml)
            
        Returns:
            API 응답 데이터 (변경구분 필드 포함)
        """
        endpoint = f"{self.BASE_URL}/storeListByDate"
        
        params = {
            'serviceKey': self.service_key,
            'key': date,
            'numOfRows': min(num_of_rows, 1000),
            'pageNo': page_no,
            'type': data_type
        }
        
        # 업종 필터 추가
        if inds_lcls_cd:
            params['indsLclsCd'] = inds_lcls_cd
        if inds_mcls_cd:
            params['indsMclsCd'] = inds_mcls_cd
        if inds_scls_cd:
            params['indsSclsCd'] = inds_scls_cd
        
        try:
            logger.info(f"Requesting stores by date={date}, page={page_no}")
            response = self.session.get(endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            if data_type == "json":
                return response.json()
            else:
                return response.text
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            raise
    
    def get_all_stores_by_date(
        self,
        date: str,
        inds_lcls_cd: Optional[str] = None,
        inds_mcls_cd: Optional[str] = None,
        inds_scls_cd: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """수정일자기준 모든 상가업소 조회 (페이지네이션 처리).
        
        Args:
            date: 일자 (YYYYMMDD 형식)
            inds_lcls_cd: 상권업종 대분류코드 (옵션)
            inds_mcls_cd: 상권업종 중분류코드 (옵션)
            inds_scls_cd: 상권업종 소분류코드 (옵션)
            
        Returns:
            모든 상가업소 데이터 리스트 (변경구분 필드 포함)
        """
        all_stores = []
        page_no = 1
        
        while True:
            response = self.get_stores_by_date(
                date=date,
                inds_lcls_cd=inds_lcls_cd,
                inds_mcls_cd=inds_mcls_cd,
                inds_scls_cd=inds_scls_cd,
                page_no=page_no,
                num_of_rows=1000
            )
            
            # 응답 구조 확인
            if isinstance(response, dict):
                body = response.get('body', {})
                items = body.get('items', [])
                
                # items가 리스트인 경우
                if isinstance(items, list):
                    if items:
                        all_stores.extend(items)
                    else:
                        break
                elif isinstance(items, dict):
                    item = items.get('item')
                    if item:
                        if isinstance(item, list):
                            all_stores.extend(item)
                        else:
                            all_stores.append(item)
                    else:
                        break
                
                # totalCount 확인
                total_count = body.get('totalCount')
                if total_count is not None:
                    total_count = int(total_count)
                    total_pages = (total_count + 999) // 1000  # 페이지당 1000개
                    
                    # 진행 상황 로그
                    # - 첫 페이지: 항상 출력
                    # - 매 10페이지마다 출력 (페이지가 많을 때)
                    # - 매 50페이지마다 출력 (페이지가 매우 많을 때)
                    # - 마지막 페이지: 항상 출력
                    should_log = False
                    if page_no == 1:
                        logger.info(f"  [{date}] 시작: 총 {total_pages:,}페이지 ({total_count:,}개 업소)")
                        should_log = True
                    elif total_pages <= 10:
                        # 페이지가 적으면 매 페이지마다
                        should_log = True
                    elif total_pages <= 100:
                        # 페이지가 보통이면 매 10페이지마다
                        should_log = (page_no % 10 == 0)
                    else:
                        # 페이지가 많으면 매 50페이지마다
                        should_log = (page_no % 50 == 0)
                    
                    # 마지막 페이지는 항상 출력
                    if len(all_stores) >= total_count:
                        should_log = True
                    
                    if should_log:
                        progress_pct = (len(all_stores) / total_count * 100) if total_count > 0 else 0
                        logger.info(f"  [{date}] 페이지 {page_no:,}/{total_pages:,} ({len(all_stores):,}/{total_count:,}개, {progress_pct:.1f}%)")
                    
                    if len(all_stores) >= total_count:
                        logger.info(f"  [{date}] 완료: 총 {len(all_stores):,}개 업소 수집")
                        break
                
                if not items:
                    break
                    
                page_no += 1
            else:
                break
        
        logger.info(f"Total stores collected by date {date}: {len(all_stores)}")
        return all_stores
    
    def get_store_one(
        self,
        bizes_id: str,
        data_type: str = "json"
    ) -> Dict[str, Any]:
        """단일 상가업소 조회.
        
        Args:
            bizes_id: 상가업소번호
            data_type: 데이터 유형 (json, xml)
            
        Returns:
            API 응답 데이터
        """
        endpoint = f"{self.BASE_URL}/storeOne"
        
        params = {
            'serviceKey': self.service_key,
            'key': bizes_id,
            'type': data_type
        }
        
        try:
            logger.info(f"Requesting store one for bizes_id={bizes_id}")
            response = self.session.get(endpoint, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            if data_type == "json":
                return response.json()
            else:
                return response.text
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            raise
    
    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("SBIZ API client session closed")

