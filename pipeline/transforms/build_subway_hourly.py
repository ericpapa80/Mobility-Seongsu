#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
성수권역 지하철 시간대별 승하차 데이터 결합 → JSON 출력

입력 (bronze):
  1) subway__sk__{date}.csv          — SK API 출구별 이용인구
  2) subway__public__{date}__detail.csv — 공공데이터 역별 승하차 (카드권종 상세)

참조 (ref):
  - ss_pt_subway_statn.geojson      — 역 중심 좌표

출력 (silver):
  - subway_stations_hourly.json
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

PIPELINE = Path(__file__).resolve().parent.parent
BRONZE_DIR = PIPELINE / "bronze"
SILVER_DIR = PIPELINE / "silver"
REF_DIR = PIPELINE / "ref"


def load_station_coords() -> dict[str, dict]:
    """ss_pt_subway_statn.geojson → {역명: {lat, lng, sub_sta_sn}}"""
    geo_path = REF_DIR / "ss_pt_subway_statn.geojson"
    with open(geo_path, encoding="utf-8") as f:
        geo = json.load(f)

    stations = {}
    for feat in geo["features"]:
        name = feat["properties"]["KOR_SUB_NM"]
        coords = feat["geometry"]["coordinates"]
        stations[name] = {
            "lat": round(coords[1], 6),
            "lng": round(coords[0], 6),
            "sub_sta_sn": feat["properties"]["SUB_STA_SN"],
        }
    return stations


def load_sk_data(csv_path: Path) -> dict:
    """SK CSV → {역명: {exit_hourly: {출구번호: [0]*24}, hourly_total: [0]*24}}"""
    result: dict = defaultdict(lambda: {
        "exit_hourly": defaultdict(lambda: [0] * 24),
        "hourly_total": [0] * 24,
    })

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["stationName"]
            hour = int(row["hour"])
            exit_no = int(row["exit"])
            count = int(row["userCount"] or 0)
            if 0 <= hour < 24:
                result[name]["exit_hourly"][exit_no][hour] += count
                result[name]["hourly_total"][hour] += count

    return dict(result)


USER_GROUP_MAP = {
    "일반": "domestic", "기타": "domestic",
    "청소년": "youth", "중고생": "youth",
    "어린이": "child",
    "우대권": "senior",
    "영어 일반": "foreign", "영어 어린이": "foreign",
    "일어 일반": "foreign", "일어 어린이": "foreign",
    "중국어 일반": "foreign", "중국어 어린이": "foreign",
}
USER_GROUPS = ["domestic", "youth", "child", "senior", "foreign"]


def _empty_groups():
    return {g: [0] * 24 for g in USER_GROUPS}


def load_public_data(csv_path: Path) -> dict:
    """Public CSV → {역명: {ride, alight, by_user_group, _has_detail}}"""
    result: dict = defaultdict(lambda: {
        "ride": [0] * 24, "alight": [0] * 24,
        "by_user_group": _empty_groups(),
        "_totals_ride": [0] * 24, "_totals_alight": [0] * 24,
        "_has_detail": False,
    })

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["stationName"]
            hour = int(row["hour"])
            ride = int(row["rideNope"])
            alight = int(row["gffNope"])
            user_label = row.get("trnscdUserSeCdNm", "").strip()

            if not (0 <= hour < 24):
                continue

            if user_label == "전체":
                result[name]["_totals_ride"][hour] += ride
                result[name]["_totals_alight"][hour] += alight
                continue

            result[name]["_has_detail"] = True
            result[name]["ride"][hour] += ride
            result[name]["alight"][hour] += alight

            group = USER_GROUP_MAP.get(user_label)
            if group:
                result[name]["by_user_group"][group][hour] += ride + alight

    for name, data in result.items():
        if not data["_has_detail"]:
            data["ride"] = data["_totals_ride"]
            data["alight"] = data["_totals_alight"]
            data["by_user_group"]["domestic"] = [
                r + a for r, a in zip(data["_totals_ride"], data["_totals_alight"])
            ]
        del data["_totals_ride"]
        del data["_totals_alight"]
        del data["_has_detail"]

    return dict(result)


def main(sk_csv: Path, public_csv: Path, output_path: Path):
    print("1. 역 좌표 로드 (GeoJSON)...")
    coords = load_station_coords()
    print(f"   → {len(coords)}개 역: {', '.join(coords.keys())}")

    print(f"\n2. SK 출구별 데이터 로드: {sk_csv.name}")
    sk = load_sk_data(sk_csv)
    for name, data in sk.items():
        total = sum(data["hourly_total"])
        exits = len(data["exit_hourly"])
        print(f"   {name}: {exits}개 출구, 총 {total:,}명")

    print(f"\n3. 공공데이터 승하차 로드: {public_csv.name}")
    pub = load_public_data(public_csv)
    for name, data in pub.items():
        ride_total = sum(data["ride"])
        alight_total = sum(data["alight"])
        print(f"   {name}: 승차 {ride_total:,} / 하차 {alight_total:,}")

    all_names = set(coords.keys()) | set(sk.keys()) | set(pub.keys())
    stations = []
    for name in sorted(all_names):
        coord = coords.get(name, {"lat": 0, "lng": 0, "sub_sta_sn": 0})
        sk_data = sk.get(name, {"exit_hourly": {}, "hourly_total": [0] * 24})
        pub_data = pub.get(name, {"ride": [0] * 24, "alight": [0] * 24})

        exit_hourly = {str(k): v for k, v in sorted(sk_data["exit_hourly"].items())}

        by_user_group = pub_data.get("by_user_group", _empty_groups())

        entry = {
            "name": name,
            "lat": coord["lat"],
            "lng": coord["lng"],
            "sub_sta_sn": coord["sub_sta_sn"],
            "ridership": {
                "ride": pub_data["ride"],
                "alight": pub_data["alight"],
            },
            "by_user_group": by_user_group,
            "exit_traffic": {
                "hourly_total": sk_data["hourly_total"],
                "by_exit": exit_hourly,
            },
            "total_ride": sum(pub_data["ride"]),
            "total_alight": sum(pub_data["alight"]),
            "total_exit_traffic": sum(sk_data["hourly_total"]),
        }
        stations.append(entry)

    stations.sort(key=lambda s: s["total_ride"] + s["total_alight"], reverse=True)

    date_label = sk_csv.stem.split("__")[-1] if sk_csv.exists() else "unknown"

    output = {
        "meta": {
            "date": date_label,
            "station_count": len(stations),
            "sources": {
                "sk": sk_csv.name,
                "public": public_csv.name,
            },
            "description": "성수권역 지하철역 시간대별 승하차 + 출구별 이용인구",
        },
        "stations": stations,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n4. Silver JSON 저장: {output_path}")
    print(f"   → {len(stations)}개 역")
    for s in stations:
        print(f"     {s['name']:8s} | 승차: {s['total_ride']:>6,} | 하차: {s['total_alight']:>6,} | 출구: {s['total_exit_traffic']:>6,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="성수권역 지하철 시간대별 승하차 데이터 결합")
    parser.add_argument(
        "--sk", type=Path,
        default=BRONZE_DIR / "subway__sk__20260225.csv",
        help="SK 출구별 이용인구 CSV (bronze)",
    )
    parser.add_argument(
        "--public", type=Path,
        default=BRONZE_DIR / "subway__public__20260225__detail.csv",
        help="공공데이터 승하차 CSV (bronze)",
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        default=SILVER_DIR / "subway_stations_hourly.json",
        help="출력 JSON 경로 (silver)",
    )
    args = parser.parse_args()
    main(args.sk, args.public, args.output)
