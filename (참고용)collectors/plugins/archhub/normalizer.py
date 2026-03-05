"""건축Hub 응답 정규화 (공공데이터포털 response.body 형식 → 공통 스키마)."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from typing import Any, Dict, List
from core.normalizers import BaseNormalizer
from core.logger import get_logger

logger = get_logger(__name__)


class ArchHubNormalizer(BaseNormalizer):
    """건축Hub API 응답 정규화 (건축물대장·건축인허가)."""

    def __init__(self):
        super().__init__(source_name="archhub")

    def normalize(self, raw_data: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """raw_data: API 단일 응답(response.body.items) 또는 이미 추출한 item 리스트."""
        normalized_items: List[Dict[str, Any]] = []

        # 이미 리스트인 경우 (스크래퍼가 all_pages로 모은 경우)
        if isinstance(raw_data, list):
            for item in raw_data:
                if isinstance(item, dict):
                    normalized_items.append(self._normalize_item(item, metadata))
            return self._build_output(normalized_items, metadata)

        # response.body.items 형식
        if "response" in raw_data:
            body = raw_data["response"].get("body") or {}
            items = body.get("items") or {}
            item = items.get("item")
            if item is None:
                pass
            elif isinstance(item, list):
                for i in item:
                    normalized_items.append(self._normalize_item(i, metadata))
            else:
                normalized_items.append(self._normalize_item(item, metadata))
        elif "item" in raw_data:
            normalized_items.append(self._normalize_item(raw_data["item"], metadata))
        else:
            normalized_items.append(self._normalize_item(raw_data, metadata))

        return self._build_output(normalized_items, metadata)

    def _normalize_item(self, item: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """단일 item을 공통 필드 + raw 보존."""
        out = {
            "properties": item,
            "raw": item,
        }
        # 자주 쓰는 필드 상위로 (있는 경우)
        for key in ("mgmBldrgstPk", "platPlc", "newPlatPlc", "bldNm", "sigunguCd", "bjdongCd", "crtnDay"):
            if key in item and item.get(key) is not None:
                out[key] = item[key]
        return out

    def _build_output(
        self,
        items: List[Dict[str, Any]],
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        return {
            "metadata": self._get_common_metadata(metadata),
            "source_specific": {
                "service": (metadata or {}).get("service"),
                "operation": (metadata or {}).get("operation"),
                "sigungu_cd": (metadata or {}).get("sigungu_cd"),
                "bjdong_cd": (metadata or {}).get("bjdong_cd"),
            },
            "data": {
                "items": items,
                "count": len(items),
            },
        }
