#!/usr/bin/env python3
"""
2단계: 성수동 경유 노선별 CardBusTimeNew 수집

- 1단계(fetch_seongsu_bus_stops.py) 또는 정적 노선목록(seongsu_bus_routes_static.txt) 사용
- 각 노선에 대해 CardBusTimeNew 호출 → 성수동 관련 정류장만 필터(선택) 또는 전 노선 정류장 수집
- 출력: seoul_bus_{YYYYMM}_성수동노선_정류장별_시간대별_승하차.csv

사용:
  python Collect/collect_seoul_bus_seongsu.py -m 202601
  python Collect/collect_seoul_bus_seongsu.py -m 202601 --routes Collect/raw/seongsu_bus_routes_static.txt
"""

import os
import sys
import csv
import json
import time
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("필요 패키지: pip install -r Collect/requirements.txt")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

API_BASE = "http://openapi.seoul.go.kr:8088"
MAX_PER_REQUEST = 1000
RAW_DIR = ROOT / "Collect" / "raw"


def _get_ride_gff(row: ET.Element, hour: int) -> tuple[int, int]:
    for suffix in ("TNOPE", "NOPE"):
        ride_el = row.find(f"HR_{hour}_GET_ON_{suffix}")
        gff_el = row.find(f"HR_{hour}_GET_OFF_{suffix}")
        if ride_el is not None or gff_el is not None:
            ride = int(ride_el.text or 0) if ride_el is not None else 0
            gff = int(gff_el.text or 0) if gff_el is not None else 0
            return ride, gff
    return 0, 0


def fetch_card_bus_time(key: str, use_ym: str, rte_no: str, start: int, end: int) -> ET.Element | None:
    url = f"{API_BASE}/{key}/xml/CardBusTimeNew/{start}/{end}/{use_ym}/{rte_no}/"
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        r.encoding = "utf-8"
        return ET.fromstring(r.text)
    except Exception as e:
        return None


def parse_bus_rows(root: ET.Element, use_ym: str) -> list[dict]:
    rows = []
    for row in root.findall(".//row"):
        rte_no_el = row.find("RTE_NO")
        rte_nm_el = row.find("RTE_NM")
        stops_id_el = row.find("STOPS_ID")
        stops_ars_el = row.find("STOPS_ARS_NO")
        sbwy_el = row.find("SBWY_STNS_NM")

        rte_no_val = (rte_no_el.text or "").strip() if rte_no_el is not None else ""
        rte_nm_val = (rte_nm_el.text or "").strip() if rte_nm_el is not None else ""
        stops_id_val = (stops_id_el.text or "").strip() if stops_id_el is not None else ""
        stops_ars_val = (stops_ars_el.text or "").strip() if stops_ars_el is not None else ""
        stops_nm_val = (sbwy_el.text or "").strip() if sbwy_el is not None else ""

        for hour in range(24):
            ride, gff = _get_ride_gff(row, hour)
            rows.append({
                "use_ym": use_ym,
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


def load_route_list(routes_file: Path) -> list[str]:
    """노선 목록 로드 (주석/공백 제외)"""
    if not routes_file.exists():
        return []
    routes = []
    with open(routes_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            routes.append(line)
    return routes


def run(use_ym: str, routes_file: Path, filter_stops: set[str] | None, output_dir: Path) -> None:
    key = os.environ.get("SEOUL_OPEN_DATA_KEY") or os.environ.get("SEOUL_OPEN_API_KEY")
    if not key:
        print("환경변수 SEOUL_OPEN_DATA_KEY 필요 (.env)")
        sys.exit(1)

    routes = load_route_list(routes_file) if routes_file.exists() else []
    if not routes:
        default_static = RAW_DIR / "seongsu_bus_routes_static.txt"
        routes = load_route_list(default_static)
    if not routes:
        # 1단계 결과에서 로드
        json_file = RAW_DIR / "seongsu_bus_stops_routes.json"
        if json_file.exists():
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
            routes = list(data.get("route_ids", []))[:20]
        else:
            txt_file = RAW_DIR / "seongsu_bus_routes.txt"
            routes = load_route_list(txt_file)

    if not routes:
        print("노선 목록 없음. fetch_seongsu_bus_stops.py 실행 또는 seongsu_bus_routes_static.txt 확인")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"2단계: 성수동 경유 {len(routes)}개 노선 CardBusTimeNew 수집 (USE_YM={use_ym})...")

    all_rows = []
    limit = 5 if key == "sample" else MAX_PER_REQUEST

    for i, rte_no in enumerate(routes):
        rte_no = str(rte_no).strip()
        if not rte_no:
            continue
        time.sleep(0.3)
        start, end = 1, limit
        route_rows = []
        while True:
            root = fetch_card_bus_time(key, use_ym, rte_no, start, end)
            if root is None:
                break
            result = root.find(".//RESULT/CODE")
            if result is not None and result.text and result.text not in ("INFO-000",):
                if result.text == "INFO-200":
                    break
                print(f"  {rte_no}: API 오류 {result.text}")
                break
            rows = parse_bus_rows(root, use_ym)
            if filter_stops:
                rows = [r for r in rows if r["stops_ars_no"] in filter_stops or r["stops_id"] in filter_stops]
            route_rows.extend(rows)
            list_total = root.find(".//list_total_count")
            total = int(list_total.text or 0) if list_total is not None and list_total.text else 0
            if not rows or end >= total or key == "sample":
                break
            start = end + 1
            end = min(end + MAX_PER_REQUEST, total)

        if route_rows:
            all_rows.extend(route_rows)
            stops_u = len(set((r["stops_ars_no"], r["stops_id"]) for r in route_rows))
            print(f"  {rte_no}: {stops_u}정류장 {len(route_rows)}행")

    if not all_rows:
        print("  → 수집된 데이터 없음")
        sys.exit(1)

    fieldnames = ["use_ym", "rte_no", "rte_nm", "stops_id", "stops_ars_no", "stops_nm",
                  "hour", "rideNope", "gffNope", "totalNope"]
    out_file = output_dir / f"seoul_bus_{use_ym}_성수동노선_정류장별_시간대별_승하차.csv"
    with open(out_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    stops_u = len(set((r["stops_id"], r["stops_ars_no"]) for r in all_rows))
    print(f"\n저장: {out_file} ({len(all_rows)}행, {stops_u}정류장)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="성수동 노선별 버스 승하차 수집")
    parser.add_argument("-m", "--month", default="202601", help="USE_YM YYYYMM")
    parser.add_argument("--routes", type=Path, default=None,
                        help="노선 목록 파일 (없으면 seongsu_bus_routes.txt → seongsu_bus_routes_static.txt)")
    parser.add_argument("--filter-stops", type=Path, default=None,
                        help="성수동 정류장만 필터 시 seongsu_bus_stops_routes.json 경로")
    parser.add_argument("-o", "--output", type=Path, default=RAW_DIR)
    args = parser.parse_args()

    routes_file = args.routes or RAW_DIR / "seongsu_bus_routes.txt"
    filter_set = None
    if args.filter_stops and args.filter_stops.exists():
        with open(args.filter_stops, encoding="utf-8") as f:
            data = json.load(f)
        stops = data.get("stops", [])
        filter_set = set()
        for s in stops:
            filter_set.add(s.get("stops_ars_no", ""))
            filter_set.add(s.get("stops_id", ""))

    run(args.month, routes_file, filter_set, args.output)
