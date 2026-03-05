#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
서울 전역 교통속도 GeoJSON → 성수 bbox 필터링 + 시간대별 속도 배열 정규화

입력: pipeline/ref/ss_pl_traffic.geojson
출력: pipeline/silver/traffic_seongsu.json
"""

import json
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PIPELINE = Path(__file__).resolve().parent.parent
REF_DIR = PIPELINE / "ref"
SILVER_DIR = PIPELINE / "silver"

BBOX_MIN_LNG, BBOX_MIN_LAT = 127.035, 37.533
BBOX_MAX_LNG, BBOX_MAX_LAT = 127.070, 37.557

HOUR_KEYS = [f"~{h:02d}시" for h in range(1, 25)]


def coords_in_bbox(coordinates: list) -> bool:
    for coord in coordinates:
        lng, lat = coord[0], coord[1]
        if BBOX_MIN_LNG <= lng <= BBOX_MAX_LNG and BBOX_MIN_LAT <= lat <= BBOX_MAX_LAT:
            return True
    return False


def main():
    src = REF_DIR / "ss_pl_traffic.geojson"
    print(f"1. 로딩: {src.name}")
    with open(src, encoding="utf-8") as f:
        geo = json.load(f)

    total = len(geo["features"])
    print(f"   → 전체 {total}개 링크")

    segments = []
    for feat in geo["features"]:
        coords = feat["geometry"]["coordinates"]
        if not coords_in_bbox(coords):
            continue

        props = feat["properties"]
        speeds = [props.get(k, 0.0) for k in HOUR_KEYS]

        segments.append({
            "link_id": str(props.get("LINK_ID", "")),
            "road_name": props.get("도로명", ""),
            "direction": props.get("방향", ""),
            "distance": props.get("거리", 0),
            "lanes": props.get("차선수", 1),
            "road_type": props.get("기능유형구분", ""),
            "area_type": props.get("도심/외곽구분", ""),
            "speeds": [round(s, 1) for s in speeds],
            "coordinates": [[round(c[0], 6), round(c[1], 6)] for c in coords],
        })

    output = {
        "meta": {
            "bbox": [BBOX_MIN_LNG, BBOX_MIN_LAT, BBOX_MAX_LNG, BBOX_MAX_LAT],
            "segment_count": len(segments),
            "date": str(geo["features"][0]["properties"].get("일자", "")) if segments else "",
        },
        "segments": segments,
    }

    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SILVER_DIR / "traffic_seongsu.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    print(f"2. 필터 완료: {len(segments)}/{total}개 링크 → {out_path.name}")


if __name__ == "__main__":
    main()
