"""
VWorld lt-c-spbd GeoJSON에서 성수동(성수동1가, 성수동2가)만 남기고 나머지 행정동 제거.
"""
import json
import sys
from pathlib import Path

KEEP_GU = ("성수동1가", "성수동2가")


def main():
    geojson_path = Path(
        "collectors/data/raw/vworld/vworld_seongsu_20260127_134933/"
        "seongsu_lt-c-spbd_20260127_134933.geojson"
    )
    if len(sys.argv) > 1:
        geojson_path = Path(sys.argv[1])

    if not geojson_path.exists():
        print("File not found:", geojson_path)
        return 1

    print("Loading:", geojson_path)
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features") or []
    total = len(features)
    filtered = [f for f in features if (f.get("properties") or {}).get("gu") in KEEP_GU]
    removed = total - len(filtered)

    data["features"] = filtered
    if "total_features" in data:
        data["total_features"] = len(filtered)

    print("Total features:", total)
    print("Kept (성수동1가, 성수동2가):", len(filtered))
    print("Removed:", removed)

    with open(geojson_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Written:", geojson_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
