"""성동구(또는 지정 시군구) 건축Hub 수집: 건축물대장/건축인허가 시군구·법정동 단위.

사용 예:
  # 성수동 전용: 성수동1가·성수동2가 수집 후 대장/인허가 별로 병합, 한 폴더에만 저장 (raw/processed 없음)
  python scripts/archhub/collect_seongsu.py --seongsu-only

  # 지정 법정동만 수집
  python scripts/archhub/collect_seongsu.py --bjdong 11400 11500
  python scripts/archhub/collect_seongsu.py --service archpms --operation getApBasisOulnInfo --bjdong 11400
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from plugins.archhub import ArchHubScraper
from plugins.archhub.api_client import ArchHubAPIClient
from core.logger import get_logger
from core.file_handler import FileHandler
from config.scrapers.archhub import BLD_RGST_OPERATIONS, ARCH_PMS_OPERATIONS

logger = get_logger(__name__)

# 성동구 시군구코드 (첨부2 시군구코드 목록 기준)
SEONGDONG_GU_CD = "11200"

# 성수동 법정동코드(5자리 bjdongCd). 행정표준코드 10자리 기준 성수동1가·성수동2가 하위 5자리.
# 확인: https://www.code.go.kr → 코드검색 → 법정동코드목록조회
SEONGSU_BJDONG_CODES = ["11400", "11500"]  # 성수동1가, 성수동2가

# 성수동 전용 모드에서 수집할 (서비스, 오퍼레이션) — 건축물대장·건축인허가 전체 오퍼레이션. 대장/인허가 별로 병합 산출.
SEONGSU_DEFAULT_OPS: List[tuple] = [
    ("bldrgst", op[0]) for op in BLD_RGST_OPERATIONS
] + [
    ("archpms", op[0]) for op in ARCH_PMS_OPERATIONS
]


def run_seongsu_only(
    output_base: Path,
    delay_seconds: float = 0.3,
    operations: Optional[List[tuple]] = None,
) -> Dict[str, Any]:
    """성수동 전용 수집: 시군구 11200, 성수동1가·2가 수집 후 대장/인허가별로 병합해 output_base에만 저장 (raw/processed 폴더 없음)."""
    operations = operations or SEONGSU_DEFAULT_OPS
    output_base.mkdir(parents=True, exist_ok=True)
    api_client = ArchHubAPIClient()
    file_handler = FileHandler()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary = {
        "sigungu_cd": SEONGDONG_GU_CD,
        "bjdong_codes": SEONGSU_BJDONG_CODES,
        "collected_at": datetime.now().isoformat(),
        "by_bjdong": {b: {} for b in SEONGSU_BJDONG_CODES},
        "by_operation": {},
        "files": [],
        "total_items": 0,
    }
    try:
        for service, operation in operations:
            merged_items: List[Dict[str, Any]] = []
            for bjdong_cd in SEONGSU_BJDONG_CODES:
                logger.info(f"Collecting sigungu={SEONGDONG_GU_CD} bjdong={bjdong_cd} ({service}/{operation})")
                if service == "bldrgst":
                    items = api_client.get_bldrgst_all_pages(
                        operation, SEONGDONG_GU_CD, bjdong_cd,
                        num_of_rows=100, delay_seconds=delay_seconds,
                    )
                else:
                    items = api_client.get_archpms_all_pages(
                        operation, SEONGDONG_GU_CD, bjdong_cd,
                        num_of_rows=100, delay_seconds=delay_seconds,
                    )
                summary["by_bjdong"][bjdong_cd][f"{service}/{operation}"] = len(items)
                merged_items.extend(items)
                logger.info(f"  -> {len(items)}건")
            key = f"{service}/{operation}"
            summary["by_operation"][key] = len(merged_items)
            summary["total_items"] += len(merged_items)
            if not merged_items:
                continue
            name = f"{service}_{operation}_11200_seongsu_{ts}"
            metadata = {
                "service": service,
                "operation": operation,
                "sigungu_cd": SEONGDONG_GU_CD,
                "bjdong_codes": SEONGSU_BJDONG_CODES,
                "merged": True,
            }
            json_path = output_base / f"{name}.json"
            file_handler.save_json(
                {"metadata": metadata, "totalCount": len(merged_items), "items": merged_items},
                json_path,
                ensure_ascii=False,
            )
            summary["files"].append(str(json_path))
            csv_path = output_base / f"{name}.csv"
            rows = [x if isinstance(x, dict) else {} for x in merged_items]
            file_handler.save_csv(rows, csv_path)
            summary["files"].append(str(csv_path))
        summary_path = output_base / f"seongsu_collection_summary_{ts}.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        logger.info(f"Summary written: {summary_path}")
        return summary
    finally:
        api_client.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="건축Hub 성동구(또는 지정 시군구) 법정동별 수집. --seongsu-only 시 성수동 전용 일괄 수집.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--seongsu-only", action="store_true", help="성수동 전용: 성수동1가·2가, 건축물대장/건축인허가 기본개요 수집 후 한 폴더·요약 생성")
    parser.add_argument("--sigungu", default=SEONGDONG_GU_CD, help=f"시군구코드 (기본: {SEONGDONG_GU_CD} 성동구)")
    parser.add_argument("--bjdong", nargs="+", default=None, help="법정동코드 (공백 구분). --seongsu-only 사용 시 무시")
    parser.add_argument(
        "--service",
        choices=("bldrgst", "archpms"),
        default="bldrgst",
        help="bldrgst=건축물대장, archpms=건축인허가 (일반 모드)",
    )
    parser.add_argument(
        "--operation",
        default="getBrBasisOulnInfo",
        help="오퍼레이션명 (건축물대장 기본: getBrBasisOulnInfo, 건축인허가 기본: getApBasisOulnInfo)",
    )
    parser.add_argument("--output-dir", type=str, default=None, help="출력 디렉터리 (기본: data/raw/archhub 또는 성수동 전용 시 data/raw/archhub/archhub_seongsu_타임스탬프)")
    parser.add_argument("--delay", type=float, default=0.3, help="페이지 간 대기(초)")
    args = parser.parse_args()

    if args.seongsu_only:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = Path(args.output_dir) if args.output_dir else (project_root / "data" / "raw" / "archhub" / f"archhub_seongsu_{ts}")
        run_seongsu_only(output_base=base, delay_seconds=args.delay)
        return

    if not args.bjdong:
        parser.error("--bjdong이 필요합니다. 성수동 일괄 수집은 --seongsu-only 를 사용하세요.")
        return

    if args.service == "archpms" and args.operation == "getBrBasisOulnInfo":
        args.operation = "getApBasisOulnInfo"

    output_dir = Path(args.output_dir) if args.output_dir else project_root / "data" / "raw" / "archhub"
    output_dir.mkdir(parents=True, exist_ok=True)

    scraper = ArchHubScraper(output_dir=output_dir)
    results = []
    try:
        for bjdong_cd in args.bjdong:
            logger.info(f"Collecting sigungu={args.sigungu} bjdong={bjdong_cd} ({args.service}/{args.operation})")
            r = scraper.scrape(
                service=args.service,
                operation=args.operation,
                sigungu_cd=args.sigungu,
                bjdong_cd=bjdong_cd.strip(),
                delay_seconds=args.delay,
                save_json=True,
                save_csv=True,
            )
            results.append({"bjdong_cd": bjdong_cd, "total_count": r["total_count"], "files": r.get("files", {})})
            logger.info(f"  -> {r['total_count']}건, files: {list(r.get('files', {}).keys())}")
        logger.info(f"Done. {len(results)} bjdong(s) collected.")
    finally:
        scraper.close()

    return results


if __name__ == "__main__":
    main()
