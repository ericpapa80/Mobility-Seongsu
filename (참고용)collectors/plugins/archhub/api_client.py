"""건축Hub OpenAPI 클라이언트 (건축물대장·건축인허가).

공공데이터포털 스타일: serviceKey, sigunguCd, bjdongCd, numOfRows(최대 100), pageNo, _type=json.
"""

import requests
from typing import Dict, Any, Optional, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.scrapers.archhub import (
    ArchHubConfig,
    BASE_URL_BLD_RGST,
    BASE_URL_ARCH_PMS,
    MAX_NUM_OF_ROWS,
    BLD_RGST_OP_NAMES,
    ARCH_PMS_OP_NAMES,
)
from core.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)


class ArchHubAPIClient:
    """건축Hub OpenAPI 클라이언트 (BldRgstHubService, ArchPmsHubService)."""

    def __init__(self):
        self.service_key = ArchHubConfig.get_api_key()
        self.bldrgst_base = ArchHubConfig.get_bldrgst_base_url()
        self.archpms_base = ArchHubConfig.get_archpms_base_url()
        self.timeout = getattr(settings, "request_timeout", 30)
        self.max_retries = getattr(settings, "max_retries", 3)
        self.retry_delay = getattr(settings, "retry_delay", 1)

        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _request(
        self,
        base_url: str,
        operation: str,
        sigungu_cd: str,
        bjdong_cd: str,
        num_of_rows: int = 100,
        page_no: int = 1,
        **extra_params,
    ) -> Dict[str, Any]:
        """공통 GET 요청 (건축물대장/건축인허가 동일 형식)."""
        num_of_rows = min(num_of_rows, MAX_NUM_OF_ROWS)
        url = f"{base_url.rstrip('/')}/{operation}"

        params: Dict[str, Any] = {
            "serviceKey": self.service_key,
            "sigunguCd": sigungu_cd,
            "bjdongCd": bjdong_cd,
            "numOfRows": num_of_rows,
            "pageNo": page_no,
            "_type": "json",
        }
        params.update({k: v for k, v in extra_params.items() if v is not None})

        try:
            logger.debug(f"Request: {operation} sigunguCd={sigungu_cd} bjdongCd={bjdong_cd} pageNo={page_no}")
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"ArchHub API request failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Status: {e.response.status_code}, text: {e.response.text[:500]}")
            raise
        except ValueError as e:
            logger.error(f"ArchHub API JSON parse error: {e}")
            raise

    @staticmethod
    def _get_items_from_response(data: Dict[str, Any]) -> tuple:
        """응답에서 items 리스트와 totalCount 추출. 공공데이터포털 response.body 형식."""
        try:
            body = (data.get("response") or {}).get("body") or {}
            items = body.get("items") or {}
            # item이 단일 객체일 수 있음
            item = items.get("item")
            if item is None:
                return [], int(body.get("totalCount") or 0)
            if isinstance(item, list):
                return item, int(body.get("totalCount") or len(item))
            return [item], int(body.get("totalCount") or 1)
        except Exception:
            return [], 0

    @staticmethod
    def _check_result_code(data: Dict[str, Any]) -> bool:
        """response.header.resultCode == '00' 인지 확인."""
        try:
            header = (data.get("response") or {}).get("header") or {}
            return header.get("resultCode") == "00"
        except Exception:
            return False

    def get_bldrgst(
        self,
        operation: str,
        sigungu_cd: str,
        bjdong_cd: str,
        num_of_rows: int = 100,
        page_no: int = 1,
        plat_gb_cd: Optional[str] = None,
        bun: Optional[str] = None,
        ji: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """건축물대장 조회 1회 (한 페이지)."""
        if operation not in BLD_RGST_OP_NAMES:
            logger.warning(f"Unknown BldRgst operation: {operation}")
        return self._request(
            self.bldrgst_base,
            operation,
            sigungu_cd,
            bjdong_cd,
            num_of_rows=num_of_rows,
            page_no=page_no,
            platGbCd=plat_gb_cd,
            bun=bun,
            ji=ji,
            startDate=start_date,
            endDate=end_date,
        )

    def get_archpms(
        self,
        operation: str,
        sigungu_cd: str,
        bjdong_cd: str,
        num_of_rows: int = 100,
        page_no: int = 1,
        plat_gb_cd: Optional[str] = None,
        bun: Optional[str] = None,
        ji: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """건축인허가 조회 1회 (한 페이지)."""
        if operation not in ARCH_PMS_OP_NAMES:
            logger.warning(f"Unknown ArchPms operation: {operation}")
        return self._request(
            self.archpms_base,
            operation,
            sigungu_cd,
            bjdong_cd,
            num_of_rows=num_of_rows,
            page_no=page_no,
            platGbCd=plat_gb_cd,
            bun=bun,
            ji=ji,
            startDate=start_date,
            endDate=end_date,
        )

    def get_bldrgst_all_pages(
        self,
        operation: str,
        sigungu_cd: str,
        bjdong_cd: str,
        num_of_rows: int = 100,
        delay_seconds: float = 0.3,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """건축물대장 전체 페이지 수집 (totalCount 기준 페이징)."""
        import time
        all_items: List[Dict[str, Any]] = []
        page_no = 1
        while True:
            data = self.get_bldrgst(
                operation, sigungu_cd, bjdong_cd,
                num_of_rows=num_of_rows, page_no=page_no, **kwargs
            )
            if not self._check_result_code(data):
                logger.warning(f"Non-OK resultCode: {data}")
                break
            items, total_count = self._get_items_from_response(data)
            all_items.extend(items)
            if not items or len(all_items) >= total_count:
                break
            page_no += 1
            if delay_seconds > 0:
                time.sleep(delay_seconds)
        return all_items

    def get_archpms_all_pages(
        self,
        operation: str,
        sigungu_cd: str,
        bjdong_cd: str,
        num_of_rows: int = 100,
        delay_seconds: float = 0.3,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """건축인허가 전체 페이지 수집."""
        import time
        all_items = []
        page_no = 1
        while True:
            data = self.get_archpms(
                operation, sigungu_cd, bjdong_cd,
                num_of_rows=num_of_rows, page_no=page_no, **kwargs
            )
            if not self._check_result_code(data):
                logger.warning(f"Non-OK resultCode: {data}")
                break
            items, total_count = self._get_items_from_response(data)
            all_items.extend(items)
            if not items or len(all_items) >= total_count:
                break
            page_no += 1
            if delay_seconds > 0:
                time.sleep(delay_seconds)
        return all_items

    def close(self):
        self.session.close()
        logger.debug("ArchHub API client session closed")
