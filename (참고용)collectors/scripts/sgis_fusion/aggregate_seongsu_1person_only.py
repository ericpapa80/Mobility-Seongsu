#!/usr/bin/env python3
"""성수동 20~49세 1인가구(수요) 데이터만 집계·동별 집계. 수요측면 전용 리포트용."""
import json
from pathlib import Path

COLLECTORS = Path(__file__).resolve().parents[2]
ONEPERSON_PATH = COLLECTORS / "data/raw/sgis_fusion/sgis_fusion_1person_20_49_20260203_033203/tract_1person_20_49.geojson"


def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_seongsu(props):
    return (props.get("adm_nm") or "").startswith("성수")


def aggregate_by_dong(fc):
    """adm_nm별로 수치 필드 합산."""
    by_dong = {}
    for feat in fc.get("features", []):
        p = feat.get("properties", {})
        if not is_seongsu(p):
            continue
        dong = p.get("adm_nm", "")
        if dong not in by_dong:
            by_dong[dong] = {}
        for k, v in p.items():
            if isinstance(v, (int, float)):
                by_dong[dong][k] = by_dong[dong].get(k, 0) + v
    return by_dong


def aggregate_total(fc):
    """성수동 전체 합산."""
    total = {}
    for feat in fc.get("features", []):
        p = feat.get("properties", {})
        if not is_seongsu(p):
            continue
        for k, v in p.items():
            if isinstance(v, (int, float)):
                total[k] = total.get(k, 0) + v
    return total


def main():
    data = load_geojson(ONEPERSON_PATH)
    total = aggregate_total(data)
    by_dong = aggregate_by_dong(data)
    n_tracts = sum(1 for f in data["features"] if is_seongsu(f.get("properties", {})))

    out = {
        "n_tracts": n_tracts,
        "total": total,
        "by_dong": by_dong,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
