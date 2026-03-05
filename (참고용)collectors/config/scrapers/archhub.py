"""건축Hub(건축서비스산업 정보체계) OpenAPI 설정.

- 건축물대장: BldRgstHubService
- 건축인허가: ArchPmsHubService
- .env: 건축Hub_API_KEY (공공데이터포털 서비스 Key → 요청 시 serviceKey 파라미터로 사용)
"""

import os
from typing import Dict, List, Tuple

# Base URL (공공데이터포털 건축Hub)
BASE_URL_BLD_RGST = "https://apis.data.go.kr/1613000/BldRgstHubService"
BASE_URL_ARCH_PMS = "https://apis.data.go.kr/1613000/ArchPmsHubService"

# 건축물대장 오퍼레이션 (영문명 → 국문)
BLD_RGST_OPERATIONS: List[Tuple[str, str]] = [
    ("getBrBasisOulnInfo", "건축물대장 기본개요"),
    ("getBrRecapTitleInfo", "건축물대장 총괄표제부"),
    ("getBrTitleInfo", "건축물대장 표제부"),
    ("getBrFlrOulnInfo", "건축물대장 층별개요"),
    ("getBrAtchJibunInfo", "건축물대장 부속지번"),
    ("getBrExposPubuseAreaInfo", "건축물대장 전유공용면적"),
    ("getBrWclfInfo", "건축물대장 오수정화시설"),
    ("getBrHsprcInfo", "건축물대장 주택가격"),
    ("getBrExposInfo", "건축물대장 전유부"),
    ("getBrJijiguInfo", "건축물대장 지역지구구역"),
]

# 건축인허가 오퍼레이션
ARCH_PMS_OPERATIONS: List[Tuple[str, str]] = [
    ("getApBasisOulnInfo", "건축인허가 기본개요"),
    ("getApDongOulnInfo", "건축인허가 동별개요"),
    ("getApFlrOulnInfo", "건축인허가 층별개요"),
    ("getApHoOulnInfo", "건축인허가 호별개요"),
    ("getApImprprInfo", "건축인허가 대수선"),
    ("getApHdcrMgmRgstInfo", "건축인허가 공작물관리대장"),
    ("getApDemolExtngMgmRgstInfo", "건축인허가 철거멸실관리대장"),
    ("getApTmpBldInfo", "건축인허가 가설건축물"),
    ("getApWclfInfo", "건축인허가 오수정화시설"),
    ("getApPklotInfo", "건축인허가 주차장"),
    ("getApAtchPklotInfo", "건축인허가 부설주차장"),
    ("getApExposPubuseAreaInfo", "건축인허가 전유공용면적"),
    ("getApHoExposPubuseAreaInfo", "건축인허가 호별전유공용면적"),
    ("getApJijiguInfo", "건축인허가 지역지구구역"),
    ("getApRoadRgstInfo", "건축인허가 도로명대장"),
    ("getApPlatPlcInfo", "건축인허가 대지위치"),
    ("getApHsTpInfo", "건축인허가 주택유형"),
]

# 서비스별 오퍼레이션 맵 (영문명만)
BLD_RGST_OP_NAMES: List[str] = [op[0] for op in BLD_RGST_OPERATIONS]
ARCH_PMS_OP_NAMES: List[str] = [op[0] for op in ARCH_PMS_OPERATIONS]

# 페이지당 최대 건수 (API 제한)
MAX_NUM_OF_ROWS = 100


class ArchHubConfig:
    """건축Hub OpenAPI 설정."""

    @staticmethod
    def get_api_key() -> str:
        """건축Hub API 키 (.env: 건축Hub_API_KEY). 공공데이터포털 서비스 키."""
        return os.getenv("건축Hub_API_KEY", "").strip() or os.getenv("ARCHHUB_API_KEY", "").strip()

    @staticmethod
    def get_bldrgst_base_url() -> str:
        """건축물대장 서비스 Base URL."""
        return os.getenv("ARCHHUB_BLD_RGST_URL", BASE_URL_BLD_RGST)

    @staticmethod
    def get_archpms_base_url() -> str:
        """건축인허가 서비스 Base URL."""
        return os.getenv("ARCHHUB_ARCH_PMS_URL", BASE_URL_ARCH_PMS)

    @staticmethod
    def validate() -> bool:
        """설정 유효 여부 (API 키 필수)."""
        return bool(ArchHubConfig.get_api_key())
