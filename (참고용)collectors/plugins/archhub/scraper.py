"""건축Hub 스크래퍼 (건축물대장·건축인허가 OpenAPI 수집)."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from typing import Dict, Any, Optional, List
from core.base_scraper import BaseScraper
from plugins.archhub.api_client import ArchHubAPIClient
from plugins.archhub.normalizer import ArchHubNormalizer
from core.logger import get_logger
from core.file_handler import FileHandler
from config.scrapers.archhub import ArchHubConfig, BLD_RGST_OP_NAMES, ARCH_PMS_OP_NAMES

logger = get_logger(__name__)


class ArchHubScraper(BaseScraper):
    """건축Hub OpenAPI 스크래퍼 (시군구·법정동 단위, 페이징 자동)."""

    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(name="archhub", output_dir=output_dir)
        self.api_client = ArchHubAPIClient()
        self.file_handler = FileHandler()
        self.normalizer = ArchHubNormalizer()
        if not ArchHubConfig.validate():
            logger.warning("건축Hub 설정 불완전: .env에 건축Hub_API_KEY 설정 필요.")

    def scrape(
        self,
        service: str,
        operation: str,
        sigungu_cd: str,
        bjdong_cd: str,
        num_of_rows: int = 100,
        delay_seconds: float = 0.3,
        save_json: bool = True,
        save_csv: bool = True,
        plat_gb_cd: Optional[str] = None,
        bun: Optional[str] = None,
        ji: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """건축물대장 또는 건축인허가 수집 (해당 동 전체 페이지).

        Args:
            service: 'bldrgst' | 'archpms'
            operation: 오퍼레이션 영문명 (예: getBrTitleInfo, getApBasisOulnInfo)
            sigungu_cd: 시군구코드 (5자리, 예: 11200 성동구)
            bjdong_cd: 법정동코드
            num_of_rows: 페이지당 건수 (최대 100)
            delay_seconds: 페이지 간 대기(초)
            save_json, save_csv: 저장 여부
            plat_gb_cd, bun, ji, start_date, end_date: API 옵션 파라미터

        Returns:
            {'data': raw_response용 리스트, 'items': 추출 item 리스트, 'files': 저장 경로, 'total_count': 총 건수}
        """
        service = (service or "").lower()
        if service not in ("bldrgst", "archpms"):
            raise ValueError("service must be 'bldrgst' or 'archpms'")

        if service == "bldrgst" and operation not in BLD_RGST_OP_NAMES:
            logger.warning(f"Operation {operation} not in BldRgst list")
        if service == "archpms" and operation not in ARCH_PMS_OP_NAMES:
            logger.warning(f"Operation {operation} not in ArchPms list")

        logger.info(f"ArchHub scrape: service={service}, operation={operation}, sigungu={sigungu_cd}, bjdong={bjdong_cd}")

        if service == "bldrgst":
            items = self.api_client.get_bldrgst_all_pages(
                operation, sigungu_cd, bjdong_cd,
                num_of_rows=num_of_rows,
                delay_seconds=delay_seconds,
                plat_gb_cd=plat_gb_cd, bun=bun, ji=ji,
                start_date=start_date, end_date=end_date,
            )
        else:
            items = self.api_client.get_archpms_all_pages(
                operation, sigungu_cd, bjdong_cd,
                num_of_rows=num_of_rows,
                delay_seconds=delay_seconds,
                plat_gb_cd=plat_gb_cd, bun=bun, ji=ji,
                start_date=start_date, end_date=end_date,
            )

        total_count = len(items)
        logger.info(f"Collected {total_count} items")

        metadata = {
            "service": service,
            "operation": operation,
            "sigungu_cd": sigungu_cd,
            "bjdong_cd": bjdong_cd,
        }
        normalized = self.normalizer.normalize(items, metadata)
        saved_files: Dict[str, Any] = {}

        if total_count > 0 and (save_json or save_csv):
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            name_safe = f"{service}_{operation}_{sigungu_cd}_{bjdong_cd}_{ts}"

            if save_json:
                raw_payload = {
                    "metadata": metadata,
                    "totalCount": total_count,
                    "items": items,
                }
                json_path = self.raw_dir / f"{name_safe}.json"
                self.file_handler.save_json(raw_payload, json_path)
                saved_files["json"] = str(json_path)

            if save_csv and items:
                rows = [i if isinstance(i, dict) else {} for i in items]
                csv_path = self.raw_dir / f"{name_safe}.csv"
                self.file_handler.save_csv(rows, csv_path)
                saved_files["csv"] = str(csv_path)

        return {
            "data": items,
            "items": items,
            "total_count": total_count,
            "normalized": normalized,
            "files": saved_files,
            "metadata": metadata,
        }

    def close(self):
        self.api_client.close()
        logger.info("ArchHub scraper closed")
