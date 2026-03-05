#!/usr/bin/env python3
"""
tract_1person_20_49.geojson 에서 1인가구 현황 분석:
- 주거유형별(ht01~ht07) 1인가구 호수 구성
- 면적 구간별(ha01~ha10) 1인가구 호수 구성 비율
"""
import json
import sys
import io
from pathlib import Path

# Windows 콘솔 UTF-8 출력
if sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# run_fusion_gui.py 와 동일한 라벨
HOUSE_TYPE_LABELS = {
    "ht01": "단독주택",
    "ht02": "아파트",
    "ht03": "연립주택",
    "ht04": "다세대주택",
    "ht05": "비거주용건물내주택",
    "ht06": "주택이외의거처",
    "ht07": "오피스텔(추정)",
}
HOUSE_AREA_LABELS = {
    "ha01": "20㎡이하(약6평이하)",
    "ha02": "20~40㎡(약6~12평)",
    "ha03": "40~60㎡(약12~18평)",
    "ha04": "60~85㎡(약18~26평)",
    "ha05": "85~100㎡(약26~30평)",
    "ha06": "100~130㎡(약30~39평)",
    "ha07": "130~165㎡(약39~50평)",
    "ha08": "165~230㎡(약50~70평)",
    "ha09": "230㎡초과(약70평초과)",
    "ha10": "오피스텔(추정)",
}


def main():
    geojson_path = Path(__file__).resolve().parents[2] / (
        "data/raw/sgis_fusion/sgis_fusion_1person_20_49_20260130_230909/tract_1person_20_49.geojson"
    )
    if len(sys.argv) > 1:
        geojson_path = Path(sys.argv[1])

    with open(geojson_path, "r", encoding="utf-8") as f:
        gj = json.load(f)

    ht_keys = [f"ht{i:02d}" for i in range(1, 8)]   # ht01 ~ ht07
    ha_keys = [f"ha{i:02d}" for i in range(1, 11)]  # ha01 ~ ha10

    ht_sum = {k: 0 for k in ht_keys}
    ha_sum = {k: 0 for k in ha_keys}

    for feat in gj.get("features") or []:
        props = feat.get("properties") or {}
        for k in ht_keys:
            ht_sum[k] += props.get(k) or 0
        for k in ha_keys:
            ha_sum[k] += props.get(k) or 0

    total_ht = sum(ht_sum.values())
    total_ha = sum(ha_sum.values())

    # 결과 출력
    print("=" * 60)
    print("1인가구(20~49세) 현황 - tract_1person_20_49.geojson 기준")
    print("=" * 60)
    print()
    print("■ 주거유형별 1인가구 호수 구성")
    print("-" * 60)
    print(f"{'주거유형':<28} {'호수':>10} {'비율(%)':>10}")
    print("-" * 60)
    for k in ht_keys:
        n = ht_sum[k]
        pct = (n / total_ht * 100) if total_ht else 0
        label = HOUSE_TYPE_LABELS.get(k, k)
        print(f"{label:<28} {n:>10,} {pct:>9.1f}%")
    print("-" * 60)
    print(f"{'합계':<28} {total_ht:>10,} {100.0:>9.1f}%")
    print()
    print("■ 면적 구간별 1인가구 호수 구성 비율")
    print("-" * 60)
    print(f"{'면적 구간':<28} {'호수':>10} {'비율(%)':>10}")
    print("-" * 60)
    for k in ha_keys:
        n = ha_sum[k]
        pct = (n / total_ha * 100) if total_ha else 0
        label = HOUSE_AREA_LABELS.get(k, k)
        print(f"{label:<28} {n:>10,} {pct:>9.1f}%")
    print("-" * 60)
    print(f"{'합계':<28} {total_ha:>10,} {100.0:>9.1f}%")
    print()

    # JSON 요약 저장 (선택)
    out_dir = geojson_path.parent
    summary = {
        "source": str(geojson_path.name),
        "total_households_ht": total_ht,
        "total_households_ha": total_ha,
        "by_house_type": {
            HOUSE_TYPE_LABELS.get(k, k): {"count": ht_sum[k], "pct": round(ht_sum[k] / total_ht * 100, 1) if total_ht else 0}
            for k in ht_keys
        },
        "by_house_area": {
            HOUSE_AREA_LABELS.get(k, k): {"count": ha_sum[k], "pct": round(ha_sum[k] / total_ha * 100, 1) if total_ha else 0}
            for k in ha_keys
        },
    }
    summary_path = out_dir / "1person_household_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"요약 저장: {summary_path}")


if __name__ == "__main__":
    main()
