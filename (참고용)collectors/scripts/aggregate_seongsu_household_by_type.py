"""
성수동 전체 세대수·호실별 면적을 주거유형별로 집계

- 입력: ArchHub 폴더 (총괄표제부 getBrRecapTitleInfo, 전유공용면적 getBrExposPubuseAreaInfo)
- 집계: mainPurpsCdNm(주용도명)별 건물수, 세대수(hhldCnt), 호수(hoCnt), 호실수(전유부), 전유면적 합계, 전용면적 구간별 호수·비율
- 산출: data/raw/archhub/archhub_seongsu_*/aggregate_household_by_type.json

실행 (프로젝트 루트가 framework):
  python collectors/scripts/aggregate_seongsu_household_by_type.py
  python collectors/scripts/aggregate_seongsu_household_by_type.py --archhub-dir collectors/data/raw/archhub/archhub_seongsu_20260127_152635
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict

# 프로젝트 루트
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
raw_archhub = project_root / "collectors" / "data" / "raw" / "archhub"

# 전용면적 구간 (평): 0~4, 5~8, 9~12, 13~16, 17~20, 21~24, 25평 이상. 1평 = 3.3058 ㎡
PYUNG_PER_SQM = 1.0 / 3.3058
AREA_BRACKETS = [
    (0, 5, "0~4평"),
    (5, 9, "5~8평"),
    (9, 13, "9~12평"),
    (13, 17, "13~16평"),
    (17, 21, "17~20평"),
    (21, 25, "21~24평"),
    (25, None, "25평이상"),
]


def area_to_bracket(pyung: float) -> str:
    """전용면적(평)을 구간 라벨로 변환."""
    for lo, hi, label in AREA_BRACKETS:
        if hi is None:
            return label if pyung >= lo else "0~4평"
        if lo <= pyung < hi:
            return label
    return "25평이상"


def load_recap(recap_path: Path):
    """총괄표제부 로드. items 반환."""
    with open(recap_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("items") or []


def load_expos_pubuse(expos_path: Path):
    """전유공용면적 로드. items 반환."""
    with open(expos_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("items") or []


def aggregate_by_type(archhub_dir: Path):
    """
    주용도명(mainPurpsCdNm)별로:
    1) 총괄표제부: 건물 수, 세대수(hhldCnt) 합, 호수(hoCnt) 합
    2) 전유공용면적(전유만): 호실 수(건물·호별 1건), 전유면적 합계
    """
    recap_path = archhub_dir / "bldrgst_getBrRecapTitleInfo_11200_seongsu_20260127_152635.json"
    if not recap_path.exists():
        recap_path = next(archhub_dir.glob("bldrgst_getBrRecapTitleInfo_*.json"), None)
    expos_path = archhub_dir / "bldrgst_getBrExposPubuseAreaInfo_11200_seongsu_20260127_152635.json"
    if not expos_path.exists():
        expos_path = next(archhub_dir.glob("bldrgst_getBrExposPubuseAreaInfo_*.json"), None)

    if not recap_path or not recap_path.exists():
        raise FileNotFoundError(f"총괄표제부 없음: {archhub_dir}")
    if not expos_path or not expos_path.exists():
        raise FileNotFoundError(f"전유공용면적 없음: {archhub_dir}")

    recap_items = load_recap(recap_path)
    expos_items = load_expos_pubuse(expos_path)

    # 1) 총괄표제부: mainPurpsCdNm별 건물수, 세대수 합, 호수 합
    by_purps_recap = defaultdict(lambda: {"building_count": 0, "hhldCnt_sum": 0, "hoCnt_sum": 0})
    recap_dagagu_building_count = 0  # etcPurps에 '다가구' 포함 건물 수
    recap_dandok_building_count = 0  # etcPurps에 '단독주택' 포함 건물 수
    for it in recap_items:
        nm = (it.get("mainPurpsCdNm") or "").strip() or "(공백)"
        etc = (it.get("etcPurps") or "").strip()
        by_purps_recap[nm]["building_count"] += 1
        by_purps_recap[nm]["hhldCnt_sum"] += int(it.get("hhldCnt") or 0)
        by_purps_recap[nm]["hoCnt_sum"] += int(it.get("hoCnt") or 0)
        if "다가구" in etc:
            recap_dagagu_building_count += 1
        if "단독주택" in etc:
            recap_dandok_building_count += 1

    # 2) 전유공용면적: 전유만, 호실별 전용면적 합산 후 mainPurpsCdNm별 호실 수·면적 합·구간별 집계
    by_purps_expos = defaultdict(lambda: {"unit_count": 0, "area_sum": 0.0})
    unit_total_area = defaultdict(float)  # (nm, pk, ho) -> 전용면적 합(㎡)
    dagagu_unit_area = defaultdict(float)  # (pk, ho) -> 전용면적 합
    dandok_unit_area = defaultdict(float)
    for it in expos_items:
        if (it.get("exposPubuseGbCdNm") or "").strip() != "전유":
            continue
        nm = (it.get("mainPurpsCdNm") or "").strip() or "(공백)"
        pk = it.get("mgmBldrgstPk")
        ho = (it.get("hoNm") or "").strip()
        etc = (it.get("etcPurps") or "").strip()
        main_cd = (it.get("mainPurpsCd") or "").strip()
        try:
            area_val = float(it.get("area") or 0)
        except (TypeError, ValueError):
            area_val = 0
        key = (nm, pk, ho)
        unit_total_area[key] += area_val
        if main_cd == "01003" or "다가구" in etc:
            dagagu_unit_area[(pk, ho)] += area_val
        if main_cd == "01000" or "단독주택" in etc:
            dandok_unit_area[(pk, ho)] += area_val
    for (nm, pk, ho), area in unit_total_area.items():
        by_purps_expos[nm]["unit_count"] += 1
        by_purps_expos[nm]["area_sum"] += area
    by_purps_expos["다가구주택(확장)"] = {
        "unit_count": len(dagagu_unit_area),
        "area_sum": sum(dagagu_unit_area.values()),
    }
    by_purps_expos["단독주택(확장)"] = {
        "unit_count": len(dandok_unit_area),
        "area_sum": sum(dandok_unit_area.values()),
    }

    # 3) 주거유형별 전용면적 구간(0~4평, 5~8평, … 25평 이상) 호수·면적 비율
    unit_areas_by_type = defaultdict(list)
    for (nm, pk, ho), area in unit_total_area.items():
        unit_areas_by_type[nm].append(area)
    unit_areas_by_type["다가구주택(확장)"] = list(dagagu_unit_area.values())
    unit_areas_by_type["단독주택(확장)"] = list(dandok_unit_area.values())
    bracket_labels = [lb for _, _, lb in AREA_BRACKETS]
    by_purps_brackets = {}
    for nm in set(unit_areas_by_type):
        areas = unit_areas_by_type[nm]
        total_u = len(areas)
        total_a = sum(areas)
        count_by_bracket = {lb: 0 for lb in bracket_labels}
        area_by_bracket = {lb: 0.0 for lb in bracket_labels}
        for a in areas:
            pyung = a * PYUNG_PER_SQM
            b = area_to_bracket(pyung)
            count_by_bracket[b] += 1
            area_by_bracket[b] += a
        ratio_count = {lb: round(count_by_bracket[lb] / total_u, 4) if total_u else 0 for lb in bracket_labels}
        ratio_area = {lb: round(area_by_bracket[lb] / total_a, 4) if total_a else 0 for lb in bracket_labels}
        by_purps_brackets[nm] = {
            "unit_count": total_u,
            "area_sum_㎡": round(total_a, 2),
            "면적구간_호수": {lb: count_by_bracket[lb] for lb in bracket_labels},
            "면적구간_호수_비율": ratio_count,
            "면적구간_면적_비율": ratio_area,
        }

    # 모든 mainPurpsCdNm 통합
    all_names = set(by_purps_recap) | set(by_purps_expos)
    # 총괄표제부 기준 다가구·단독주택(건물 수) 참고용
    dagagu_note = {
        "recap_building_count_etcPurps_다가구": recap_dagagu_building_count,
        "note": "전유공용면적에는 mainPurpsCd 01003 또는 etcPurps '다가구'인 호실만 집계. 총괄표제부에서 etcPurps에 '다가구' 포함 건물은 별도 건물 수로 참고.",
    }
    dandok_note = {
        "recap_building_count_etcPurps_단독주택": recap_dandok_building_count,
        "note": "전유공용면적에는 mainPurpsCd 01000 또는 etcPurps '단독주택'인 호실만 집계. 총괄표제부에서 etcPurps에 '단독주택' 포함 건물은 별도 건물 수로 참고.",
    }
    rows = []
    for nm in sorted(all_names):
        r = by_purps_recap.get(nm, {"building_count": 0, "hhldCnt_sum": 0, "hoCnt_sum": 0})
        e = by_purps_expos.get(nm, {"unit_count": 0, "area_sum": 0.0})
        rows.append({
            "mainPurpsCdNm": nm,
            "building_count": r["building_count"],
            "hhldCnt_sum": r["hhldCnt_sum"],
            "hoCnt_sum": r["hoCnt_sum"],
            "unit_count": e["unit_count"],
            "area_sum_㎡": round(e["area_sum"], 2),
        })

    total_buildings = sum(x["building_count"] for x in rows)
    total_hhld = sum(x["hhldCnt_sum"] for x in rows)
    total_ho = sum(x["hoCnt_sum"] for x in rows)
    total_units = sum(x["unit_count"] for x in rows)
    total_area = sum(x["area_sum_㎡"] for x in rows)

    return {
        "source": {
            "recap_path": str(recap_path),
            "expos_path": str(expos_path),
            "recap_count": len(recap_items),
            "expos_count": len(expos_items),
        },
        "summary": {
            "total_buildings": total_buildings,
            "total_hhldCnt_sum": total_hhld,
            "total_hoCnt_sum": total_ho,
            "total_units_expos": total_units,
            "total_area_㎡": round(total_area, 2),
        },
        "다가구_참고": dagagu_note,
        "단독주택_참고": dandok_note,
        "전유부_참고": {
            "note": "전유부(getBrExposInfo)에는 주용도(mainPurpsCd) 필드가 없어 주거유형별 호실 수 집계 불가. 호실 수·면적은 전유공용면적(getBrExposPubuseAreaInfo) 기준만 사용.",
        },
        "by_mainPurpsCdNm": rows,
        "주거유형별_호수_구성": {
            "note": "총괄표제부: 세대수(hhldCnt)·호수(hoCnt). 전유공용면적: 호실 수(unit_count)·전유면적 합(area_sum_㎡).",
            "by_type": [{"mainPurpsCdNm": r["mainPurpsCdNm"], "hhldCnt_sum": r["hhldCnt_sum"], "hoCnt_sum": r["hoCnt_sum"], "unit_count": r["unit_count"], "area_sum_㎡": r["area_sum_㎡"]} for r in rows],
        },
        "주거유형별_면적구간_구성": {
            "note": "전용면적(전유) 기준 1평=3.3058㎡. 구간: 0~4평, 5~8평, 9~12평, 13~16평, 17~20평, 21~24평, 25평이상. 면적구간_호수_비율=해당 구간 호수/유형별 총 호수, 면적구간_면적_비율=해당 구간 면적/유형별 총 면적.",
            "by_type": by_purps_brackets,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="성수동 세대수·호실별 면적 주거유형별 집계")
    parser.add_argument(
        "--archhub-dir",
        type=str,
        default=None,
        help="ArchHub 폴더 경로 (기본: collectors/data/raw/archhub/archhub_seongsu_ 최신)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="출력 JSON 경로 (기본: archhub-dir/aggregate_household_by_type.json)",
    )
    args = parser.parse_args()

    if args.archhub_dir:
        archhub_dir = Path(args.archhub_dir)
    else:
        candidates = sorted(raw_archhub.glob("archhub_seongsu_*"), key=lambda p: p.name, reverse=True)
        if not candidates:
            print("[ERROR] archhub_seongsu_* 폴더 없음. --archhub-dir 로 지정하세요.")
            return 1
        archhub_dir = candidates[0]

    if not archhub_dir.is_dir():
        print(f"[ERROR] 폴더 없음: {archhub_dir}")
        return 1

    result = aggregate_by_type(archhub_dir)

    out_path = Path(args.out) if args.out else archhub_dir / "aggregate_household_by_type.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("ArchHub 폴더:", archhub_dir)
    print("출력:", out_path)
    print("총 건물 수(총괄표제부):", result["summary"]["total_buildings"])
    print("총 세대수(hhldCnt 합):", result["summary"]["total_hhldCnt_sum"])
    print("총 호수(hoCnt 합):", result["summary"]["total_hoCnt_sum"])
    print("총 호실 수(전유공용면적 전유):", result["summary"]["total_units_expos"])
    print("총 전유면적(㎡):", result["summary"]["total_area_㎡"])
    print("\n주용도명별:")
    for row in result["by_mainPurpsCdNm"]:
        if row["building_count"] or row["unit_count"]:
            print(
                f"  {row['mainPurpsCdNm']}: 건물 {row['building_count']}, 세대수 {row['hhldCnt_sum']}, 호수 {row['hoCnt_sum']}, "
                f"호실수 {row['unit_count']}, 전유면적 {row['area_sum_㎡']} ㎡"
            )
    return 0


if __name__ == "__main__":
    exit(main())
