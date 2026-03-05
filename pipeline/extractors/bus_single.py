#!/usr/bin/env python3
"""
서울열린데이터광장 CardBusTimeNew API - 버스노선별 정류장별 시간대별 승하차 수집

- 월별 데이터 (USE_YM: YYYYMM)
- 노선번호 지정 시 해당 노선만, 생략 시 전체(1~5건만 sample 한계)
- HR_0~HR_23 승차/하차 → (정류장, hour, rideNope, gffNope) 행으로 변환
- 출력: pipeline/bronze/seoul_bus_{YYYYMM}_노선{RTE}_정류장별_시간대별_승하차.csv

참고: Docs/서울열린데이터광장/서울시 버스노선별 정류장별 시간대별 승하차 인원 정보

사용 예:
  python pipeline/extractors/bus_single.py -m 202601 -r 7730
  python pipeline/extractors/bus_single.py -m 202601 -o pipeline/bronze
"""

import os
import sys
import csv
import time
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("필요 패키지 설치: pip install -r pipeline/requirements.txt")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent.parent
PIPELINE = ROOT / "pipeline"
BRONZE_DIR = PIPELINE / "bronze"
load_dotenv(ROOT / ".env")

API_BASE = "http://openapi.seoul.go.kr:8088"
MAX_PER_REQUEST = 1000


def _get_ride_gff(row: ET.Element, hour: int) -> tuple[int, int]:
    """HR_{h}_GET_ON_*, HR_{h}_GET_OFF_* 파싱 (NOPE/TNOPE 혼용 대응)"""
    for suffix in ("TNOPE", "NOPE"):
        ride_el = row.find(f"HR_{hour}_GET_ON_{suffix}")
        gff_el = row.find(f"HR_{hour}_GET_OFF_{suffix}")
        if ride_el is not None or gff_el is not None:
            ride = int(ride_el.text or 0) if ride_el is not None else 0
            gff = int(gff_el.text or 0) if gff_el is not None else 0
            return ride, gff
    return 0, 0


def fetch_card_bus_time(key: str, use_ym: str, rte_no: str | None, start: int, end: int) -> ET.Element | None:
    """CardBusTimeNew API 호출"""
    base = f"{API_BASE}/{key}/xml/CardBusTimeNew/{start}/{end}/{use_ym}/"
    url = f"{base}{rte_no}/" if rte_no else base
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        r.encoding = "utf-8"
        return ET.fromstring(r.text)
    except ET.ParseError as e:
        print(f"  XML 파싱 오류: {e}")
        return None
    except Exception as e:
        print(f"  오류: {e}")
        return None


def parse_bus_rows(root: ET.Element) -> list[dict]:
    """
    row 요소들 파싱 → 정류장별 × 시간대별 (hour, rideNope, gffNope)
    반환: [{"rte_no","rte_nm","stops_id","stops_ars_no","stops_nm","hour","rideNope","gffNope","totalNope"}, ...]
    """
    rows = []
    for row in root.findall(".//row"):
        rte_no = row.find("RTE_NO")
        rte_nm = row.find("RTE_NM")
        stops_id = row.find("STOPS_ID")
        stops_ars = row.find("STOPS_ARS_NO")
        sbwy_nm = row.find("SBWY_STNS_NM")

        rte_no_val = (rte_no.text or "").strip()
        rte_nm_val = (rte_nm.text or "").strip()
        stops_id_val = (stops_id.text or "").strip() if stops_id is not None else ""
        stops_ars_val = (stops_ars.text or "").strip() if stops_ars is not None else ""
        stops_nm_val = (sbwy_nm.text or "").strip() if sbwy_nm is not None else ""

        for hour in range(24):
            ride, gff = _get_ride_gff(row, hour)
            rows.append({
                "use_ym": "",
                "rte_no": rte_no_val,
                "rte_nm": rte_nm_val,
                "stops_id": stops_id_val,
                "stops_ars_no": stops_ars_val,
                "stops_nm": stops_nm_val,
                "hour": f"{hour:02d}",
                "rideNope": ride,
                "gffNope": gff,
                "totalNope": ride + gff,
            })
    return rows


def set_use_ym(rows: list[dict], use_ym: str) -> None:
    for r in rows:
        r["use_ym"] = use_ym


def run(use_ym: str, rte_no: str | None, output_dir: Path):
    """수집 실행"""
    key = os.environ.get("SEOUL_OPEN_DATA_KEY") or os.environ.get("SEOUL_OPEN_API_KEY")
    if not key:
        print("환경변수 SEOUL_OPEN_DATA_KEY 필요 (.env)")
        print("서울열린데이터광장(data.seoul.go.kr)에서 인증키 발급 후 .env에 추가하세요.")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    route_desc = f"노선 {rte_no}" if rte_no else "전체"
    print(f"수집 중: {route_desc} (USE_YM={use_ym})...")

    all_rows = []
    start = 1
    end = min(5 if key == "sample" else MAX_PER_REQUEST, 5)

    while True:
        root = fetch_card_bus_time(key, use_ym, rte_no, start, end)
        if root is None:
            break

        result = root.find(".//RESULT/CODE")
        if result is not None and result.text and result.text != "INFO-000":
            code = result.text
            msg_el = root.find(".//RESULT/MESSAGE")
            msg = msg_el.text if msg_el is not None else ""
            if code == "INFO-200":
                break
            print(f"  → API 오류: {code} {msg}")
            sys.exit(1)

        list_total = root.find(".//list_total_count")
        total = int(list_total.text) if list_total is not None and list_total.text else 0

        rows = parse_bus_rows(root)
        set_use_ym(rows, use_ym)
        all_rows.extend(rows)

        if not rows:
            break

        stops_count = len(root.findall(".//row"))
        print(f"  → {start}~{end}구간 {stops_count}정류장 ({len(rows)}행)")

        if end >= total or stops_count == 0:
            break
        start = end + 1
        end = min(end + MAX_PER_REQUEST, total)
        if key == "sample":
            break
        time.sleep(0.3)

    if not all_rows:
        print("  → 수집된 데이터 없음")
        sys.exit(1)

    # 중복 use_ym 제거 (모두 동일하므로 첫 행만)
    fieldnames = [
        "use_ym", "rte_no", "rte_nm", "stops_id", "stops_ars_no", "stops_nm",
        "hour", "rideNope", "gffNope", "totalNope",
    ]

    rte_suffix = f"노선{rte_no}" if rte_no else "전체"
    output_file = output_dir / f"seoul_bus_{use_ym}_{rte_suffix}_정류장별_시간대별_승하차.csv"
    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    stops_unique = len(set((r["stops_id"], r["stops_ars_no"]) for r in all_rows))
    print(f"\n저장: {output_file} ({len(all_rows)}행, {stops_unique}정류장)")


def main():
    parser = argparse.ArgumentParser(
        description="서울열린데이터 CardBusTimeNew - 버스노선별 정류장별 시간대별 승하차"
    )
    parser.add_argument(
        "-m", "--month",
        default="201511",
        help="USE_YM YYYYMM (기본: 201511)",
    )
    parser.add_argument(
        "-r", "--route",
        default="7730",
        help="노선번호 (기본: 7730, 생략 시 전체)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=BRONZE_DIR,
    )
    args = parser.parse_args()
    run(args.month, args.route if args.route else None, args.output)


if __name__ == "__main__":
    main()
