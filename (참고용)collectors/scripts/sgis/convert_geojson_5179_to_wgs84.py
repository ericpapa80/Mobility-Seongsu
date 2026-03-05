"""
기존 SGIS 집계구 GeoJSON을 EPSG:5179 -> WGS84로 변환 (QGIS 등에서 표시용).

사용법:
  python scripts/sgis/convert_geojson_5179_to_wgs84.py
  python scripts/sgis/convert_geojson_5179_to_wgs84.py --dir "data/raw/sgis/sgis_seongsu_tract_boundary_1person_household_20260127_155829"
"""

import argparse
import json
import sys
from pathlib import Path

# 프로젝트 루트
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pyproj import Transformer


def _transform_coords(coords, transformer):
    if isinstance(coords[0], (int, float)):
        lon, lat = transformer.transform(coords[0], coords[1])
        return [lon, lat]
    return [_transform_coords(item, transformer) for item in coords]


def geojson_5179_to_wgs84(geojson_dict: dict) -> dict:
    transformer = Transformer.from_crs(
        "EPSG:5179", "EPSG:4326", always_xy=True
    )
    for feat in geojson_dict.get("features") or []:
        geom = feat.get("geometry")
        if geom and geom.get("coordinates") is not None:
            geom["coordinates"] = _transform_coords(
                geom["coordinates"], transformer
            )
    return geojson_dict


def main():
    parser = argparse.ArgumentParser(
        description="SGIS GeoJSON 5179 -> WGS84 변환 (QGIS 표시용)"
    )
    parser.add_argument(
        "--dir",
        type=str,
        default="data/raw/sgis/sgis_seongsu_tract_boundary_1person_household_20260127_155829",
        help="변환할 GeoJSON이 있는 폴더 (collectors 기준)",
    )
    args = parser.parse_args()

    base = project_root / args.dir
    if not base.is_dir():
        print(f"[ERROR] 폴더 없음: {base}")
        return 1

    transformer = Transformer.from_crs(
        "EPSG:5179", "EPSG:4326", always_xy=True
    )
    converted = 0
    for path in base.glob("*.geojson"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            out = geojson_5179_to_wgs84(data)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
            print(f"[OK] {path.name} -> WGS84 변환 완료")
            converted += 1
        except Exception as e:
            print(f"[ERROR] {path.name}: {e}")
    if converted == 0:
        print("변환된 파일 없음 (해당 폴더에 .geojson이 있는지 확인하세요).")
    else:
        print(f"\n총 {converted}개 GeoJSON을 WGS84로 변환했습니다. QGIS에서 다시 불러오세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
