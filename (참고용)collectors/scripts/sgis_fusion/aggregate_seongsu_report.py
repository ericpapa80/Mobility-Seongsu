#!/usr/bin/env python3
"""성수동 집계구만 추출해 공급(multi_0_150)·수요(1person_20_49) 데이터를 집계하고 리포트용 요약을 출력한다."""
import json
import sys
from pathlib import Path

COLLECTORS = Path(__file__).resolve().parents[2]
MULTI_PATH = COLLECTORS / "data/raw/sgis_fusion/sgis_fusion_multi_0_150_20260203_030953/tract_multi_0_150.geojson"
ONEPERSON_PATH = COLLECTORS / "data/raw/sgis_fusion/sgis_fusion_1person_20_49_20260203_033203/tract_1person_20_49.geojson"


def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_seongsu(props):
    adm = props.get("adm_nm", "")
    return adm.startswith("성수")


def sum_numeric(props, keys=None):
    if keys is None:
        return {k: v for k, v in props.items() if isinstance(v, (int, float))}
    return {k: props.get(k, 0) for k in keys if isinstance(props.get(k), (int, float))}


def aggregate_features(fc, filter_fn, numeric_keys=None):
    agg = {}
    for feat in fc.get("features", []):
        p = feat.get("properties", {})
        if not filter_fn(p):
            continue
        for k, v in sum_numeric(p, numeric_keys).items():
            agg[k] = agg.get(k, 0) + v
    return agg


def main():
    multi = load_geojson(MULTI_PATH)
    oneperson = load_geojson(ONEPERSON_PATH)

    # 성수동만 필터 (adm_nm이 '성수'로 시작)
    supply = aggregate_features(multi, is_seongsu)
    demand = aggregate_features(oneperson, is_seongsu)

    # 집계구 수
    n_supply = sum(1 for f in multi["features"] if is_seongsu(f.get("properties", {})))
    n_demand = sum(1 for f in oneperson["features"] if is_seongsu(f.get("properties", {})))

    out = {
        "n_tracts": n_supply,
        "supply": supply,
        "demand": demand,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
