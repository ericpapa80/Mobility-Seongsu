#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
성수동 버스정류장 위치정보 + 시간대별 승하차 데이터 결합 → JSON 출력

입력:
  1) 성수동_정류장정보.csv  (위치·노선·정류소명)
  2) seoul_bus_{YYYYMM}_성수동노선_정류장별_시간대별_승하차.csv (시간대별 승하차)

결합 키: NODE_ID = stops_id (보조: ARS_ID = stops_ars_no)

출력: Collect/raw/seongsu_bus_stops_hourly.json
"""

import csv
import json
import sys
import io
import argparse
from pathlib import Path
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
LOCATION_CSV = ROOT / "Docs" / "서울열린데이터광장" / "서울시 버스노선별 정류장별 시간대별 승하차 인원 정보" / "성수동_정류장정보.csv"
RAW_DIR = ROOT / "Collect" / "raw"


def normalize_ars(ars_id: str) -> str:
    return ars_id.lstrip("0") if ars_id else ""


def load_stop_locations(csv_path: Path) -> dict:
    """성수동_정류장정보.csv → NODE_ID 기준 고유 정류장 dict"""
    stops = {}
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            node_id = row["NODE_ID"].strip()
            ars_id = normalize_ars(row["ARS_ID"].strip())
            name = row["정류소명"].strip()
            lng = float(row["X좌표"])
            lat = float(row["Y좌표"])
            route_name = row["노선명"].strip()

            if node_id not in stops:
                stops[node_id] = {
                    "node_id": node_id,
                    "ars_id": ars_id,
                    "name": name,
                    "lat": round(lat, 6),
                    "lng": round(lng, 6),
                    "routes": set(),
                }
            stops[node_id]["routes"].add(route_name)
    return stops


def load_ridership(csv_path: Path, valid_node_ids: set, ars_to_node: dict) -> dict:
    """
    승하차 CSV → 정류장(NODE_ID)×시간대 합산
    valid_node_ids: 성수동 정류장 NODE_ID 집합
    ars_to_node: ARS_ID(정규화) → NODE_ID 매핑 (NODE_ID 매칭 실패 시 fallback)
    """
    hourly = defaultdict(lambda: {"ride": [0]*24, "alight": [0]*24})
    total_rows = 0

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            stops_id = row["stops_id"].strip()
            stops_ars = normalize_ars(row["stops_ars_no"].strip())
            hour = int(row["hour"])
            ride = int(row["rideNope"])
            gff = int(row["gffNope"])

            key = None
            if stops_id in valid_node_ids:
                key = stops_id
            elif stops_ars in ars_to_node:
                key = ars_to_node[stops_ars]

            if key:
                hourly[key]["ride"][hour] += ride
                hourly[key]["alight"][hour] += gff

    print(f"  승하차 CSV: {total_rows}행 중 {len(hourly)}개 정류장 매칭")
    return dict(hourly)


def main(ridership_csv: Path, output_path: Path):
    global _stop_cache

    print("1. 정류장 위치정보 로드...")
    stops = load_stop_locations(LOCATION_CSV)
    _stop_cache = stops
    print(f"   → {len(stops)}개 고유 정류장 (NODE_ID 기준)")

    route_set = set()
    for s in stops.values():
        route_set.update(s["routes"])
    print(f"   → {len(route_set)}개 노선: {sorted(route_set, key=lambda x: (not x[0].isdigit(), x))}")

    valid_node_ids = set(stops.keys())
    ars_to_node = {s["ars_id"]: nid for nid, s in stops.items() if s["ars_id"]}

    print(f"\n2. 승하차 데이터 로드: {ridership_csv.name}")
    hourly = load_ridership(ridership_csv, valid_node_ids, ars_to_node)

    result_stops = []
    for node_id, stop in stops.items():
        entry = {
            "ars_id": stop["ars_id"],
            "node_id": stop["node_id"],
            "name": stop["name"],
            "lat": stop["lat"],
            "lng": stop["lng"],
            "routes": sorted(stop["routes"], key=lambda x: (not x[0].isdigit(), x)),
        }
        if node_id in hourly:
            entry["hourly"] = hourly[node_id]
        else:
            entry["hourly"] = {"ride": [0]*24, "alight": [0]*24}
        entry["total_ride"] = sum(entry["hourly"]["ride"])
        entry["total_alight"] = sum(entry["hourly"]["alight"])
        entry["total"] = entry["total_ride"] + entry["total_alight"]
        result_stops.append(entry)

    result_stops.sort(key=lambda x: x["total"], reverse=True)

    use_ym = "201511"
    try:
        with open(ridership_csv, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            first = next(reader)
            use_ym = first.get("use_ym", "201511")
    except Exception:
        pass

    output = {
        "meta": {
            "use_ym": use_ym,
            "stop_count": len(result_stops),
            "route_count": len(route_set),
            "routes": sorted(route_set, key=lambda x: (not x[0].isdigit(), x)),
            "description": "성수동 버스정류장별 시간대별 승하차 인원 (월 합산)",
        },
        "stops": result_stops,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n3. JSON 저장: {output_path}")
    print(f"   → {len(result_stops)}개 정류장")
    matched = sum(1 for s in result_stops if s["total"] > 0)
    print(f"   → 승하차 데이터 매칭: {matched}개 정류장")

    if result_stops:
        print("\n   상위 10개 정류장 (총 승하차 기준):")
        for s in result_stops[:10]:
            print(f"     {s['name']:20s} | 승차: {s['total_ride']:>6,} | 하차: {s['total_alight']:>6,} | 합계: {s['total']:>6,} | 노선: {', '.join(s['routes'][:5])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="성수동 버스정류장 위치+승하차 데이터 결합")
    parser.add_argument(
        "-r", "--ridership",
        type=Path,
        default=RAW_DIR / "seoul_bus_201511_성수동노선_정류장별_시간대별_승하차.csv",
        help="승하차 CSV 파일 경로",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=RAW_DIR / "seongsu_bus_stops_hourly.json",
        help="출력 JSON 경로",
    )
    args = parser.parse_args()
    main(args.ridership, args.output)
