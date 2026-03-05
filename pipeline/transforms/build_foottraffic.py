#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
보행자 통행량 GeoJSON → roadLinkId 기준 groupBy + 3차원 정규화
  차원: dayweek(평일/주말) × agrde(연령대) × tmzon(시간대)

입력: pipeline/ref/ss_pl_foottraffic.geojson  (152,978 features)
출력: pipeline/silver/foottraffic_seongsu.json

구조: 1,561 links × 2 dayweek × 7 agrde × 7 tmzon
"""

import json
import sys
import io
from pathlib import Path
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PIPELINE = Path(__file__).resolve().parent.parent
REF_DIR = PIPELINE / "ref"
SILVER_DIR = PIPELINE / "silver"

HOUR_TO_TMZON = {}
for h in range(0, 6):
    HOUR_TO_TMZON[str(h)] = "00~05"
for h in range(6, 11):
    HOUR_TO_TMZON[str(h)] = "06~10"
for h in range(11, 14):
    HOUR_TO_TMZON[str(h)] = "11~13"
for h in range(14, 17):
    HOUR_TO_TMZON[str(h)] = "14~16"
for h in range(17, 21):
    HOUR_TO_TMZON[str(h)] = "17~20"
for h in range(21, 24):
    HOUR_TO_TMZON[str(h)] = "21~23"

AGRDE_LIST = [
    {"code": "00", "label": "전체"},
    {"code": "10", "label": "10대"},
    {"code": "20", "label": "20대"},
    {"code": "30", "label": "30대"},
    {"code": "40", "label": "40대"},
    {"code": "50", "label": "50대"},
    {"code": "60", "label": "60대이상"},
]

DAYWEEK_LIST = [
    {"code": "1", "label": "평일"},
    {"code": "2", "label": "주말"},
]

TMZON_LIST = ["00~05", "06~10", "11~13", "14~16", "17~20", "21~23", "종일"]


def compute_centroid(coordinates: list) -> list:
    n = len(coordinates)
    if n == 0:
        return [0.0, 0.0]
    mid = n // 2
    return [round(coordinates[mid][0], 6), round(coordinates[mid][1], 6)]


def main():
    src = REF_DIR / "ss_pl_foottraffic.geojson"
    print(f"1. 로딩: {src.name}")
    with open(src, encoding="utf-8") as f:
        geo = json.load(f)

    total = len(geo["features"])
    print(f"   → 전체 {total}개 features")

    # grouped[link_id] = {"road_link_id":..., "coordinates":..., "centroid":..., "data":{}}
    # data[dayweek][agrde][tmzon] = {acost, cost, grade, per}
    grouped: dict[str, dict] = {}
    max_vals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for feat in geo["features"]:
        props = feat["properties"]
        link_id = str(props["roadLinkId"])
        tmzon_name = props["tmzon_name"]
        dayweek = str(props.get("dayweek", "1"))
        agrde = str(props.get("agrde", "00"))
        acost = int(props.get("acost", 0))
        cost = int(props.get("cost", 0))
        grade = int(props.get("grade", 1))
        per = float(props.get("per", 0.0))

        if link_id not in grouped:
            coords = feat["geometry"]["coordinates"]
            grouped[link_id] = {
                "road_link_id": link_id,
                "coordinates": [[round(c[0], 6), round(c[1], 6)] for c in coords],
                "centroid": compute_centroid(coords),
                "data": {},
            }

        data = grouped[link_id]["data"]
        dw = data.setdefault(dayweek, {})
        ag = dw.setdefault(agrde, {})

        entry = ag.get(tmzon_name)
        if entry is None or acost > entry["acost"]:
            ag[tmzon_name] = {
                "acost": acost,
                "cost": cost,
                "grade": grade,
                "per": round(per, 1),
            }

        dim_key = f"{dayweek}_{agrde}"
        for metric in ("acost", "cost"):
            max_vals[dim_key][f"{metric}_{tmzon_name}"] = max(
                max_vals[dim_key][f"{metric}_{tmzon_name}"],
                acost if metric == "acost" else cost,
            )

    links = sorted(grouped.values(), key=lambda x: x["road_link_id"])

    output = {
        "meta": {
            "link_count": len(links),
            "tmzon_list": TMZON_LIST,
            "hour_to_tmzon": HOUR_TO_TMZON,
            "agrde_list": AGRDE_LIST,
            "dayweek_list": DAYWEEK_LIST,
            "max_vals": {k: dict(v) for k, v in max_vals.items()},
        },
        "links": links,
    }

    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SILVER_DIR / "foottraffic_seongsu.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    file_mb = out_path.stat().st_size / 1024 / 1024
    print(f"2. 완료: {len(links)}개 링크 → {out_path.name} ({file_mb:.1f} MB)")
    print(f"   차원: {len(DAYWEEK_LIST)} dayweek × {len(AGRDE_LIST)} agrde × {len(TMZON_LIST)} tmzon")


if __name__ == "__main__":
    main()
