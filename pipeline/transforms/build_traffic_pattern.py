"""
과거 TOPIS 차량통행속도 XLSX(월별) → 성수 시간대별 패턴 JSON

입력:  pipeline/source/topis/YYYY년 M월 서울시 차량통행속도.xlsx  (14개월)
참조:  pipeline/ref/topis_seongsu_links.json  (252개 LINK_ID)
출력:  pipeline/ref/topis_traffic_pattern.json

집계 키: all, weekday, weekend, 월, 화, 수, 목, 금, 토, 일
"""

from pathlib import Path
from datetime import datetime
import json
import glob
import openpyxl

BASE = Path(__file__).resolve().parent.parent
SOURCE_DIR = BASE / "source" / "topis"
REF_DIR = BASE / "ref"

DAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]
WEEKDAY_NAMES = {"월", "화", "수", "목", "금"}
WEEKEND_NAMES = {"토", "일"}
ALL_KEYS = ["all", "weekday", "weekend"] + DAY_NAMES

HOUR_COLS = list(range(12, 36))  # col indices 12..35 = ~01시..~24시


def load_seongsu_links():
    with open(REF_DIR / "topis_seongsu_links.json", encoding="utf-8") as f:
        data = json.load(f)
    link_set = set(data["link_ids"])
    link_road = {}
    for link in data["links"]:
        link_road[link["link_id"]] = link.get("road_name", "")
    return link_set, link_road


def empty_hours():
    return {h: [] for h in range(24)}


def parse_xlsx(path: Path, link_set: set, link_road: dict):
    """한 개 XLSX에서 성수 링크만 추출, 요일별·평일/주말·전체 기준 시간대별 속도 누적."""
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    ws = wb.active

    # accum[key][road_name] = { hour_idx: [speeds...] }
    accum = {k: {} for k in ALL_KEYS}
    row_count = 0
    match_count = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        row_count += 1
        lid = str(row[3])
        if lid not in link_set:
            continue
        match_count += 1

        day_name = row[1]  # 요일 (월,화,...일)
        if day_name not in DAY_NAMES:
            continue

        road = link_road.get(lid, row[2] or "")

        speeds_raw = []
        for ci, col_idx in enumerate(HOUR_COLS):
            val = row[col_idx]
            if val is not None and isinstance(val, (int, float)) and val > 0:
                speeds_raw.append((ci, float(val)))

        targets = ["all", day_name]
        if day_name in WEEKDAY_NAMES:
            targets.append("weekday")
        else:
            targets.append("weekend")

        for key in targets:
            if road not in accum[key]:
                accum[key][road] = empty_hours()
            for ci, speed in speeds_raw:
                accum[key][road][ci].append(speed)

    wb.close()
    return accum, row_count, match_count


def merge_accum(total, part):
    for key in ALL_KEYS:
        if key not in part:
            continue
        if key not in total:
            total[key] = {}
        for road, hours in part[key].items():
            if road not in total[key]:
                total[key][road] = empty_hours()
            for h in range(24):
                total[key][road][h].extend(hours.get(h, []))


def avg_list(vals):
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def build_pattern(accum, key):
    """accum[key] 전체 도로의 시간대별 평균."""
    bucket = {h: [] for h in range(24)}
    for road_hours in accum.get(key, {}).values():
        for h in range(24):
            bucket[h].extend(road_hours.get(h, []))
    return [avg_list(bucket[h]) for h in range(24)]


def build_road_pattern(accum, road, key):
    hours_data = accum.get(key, {}).get(road, {})
    return [avg_list(hours_data.get(h, [])) for h in range(24)]


def main():
    link_set, link_road = load_seongsu_links()
    print(f"성수 링크: {len(link_set)}개")

    files = sorted(glob.glob(str(SOURCE_DIR / "*서울시 차량통행속도.xlsx")))
    print(f"XLSX 파일: {len(files)}개")

    total_accum = {}
    months = []
    total_rows = 0
    total_matches = 0

    for fpath in files:
        fname = Path(fpath).name
        print(f"  처리: {fname} ... ", end="", flush=True)
        accum, rc, mc = parse_xlsx(Path(fpath), link_set, link_road)
        merge_accum(total_accum, accum)
        total_rows += rc
        total_matches += mc
        month_str = fname.split("서울시")[0].strip()
        months.append(month_str)
        print(f"{mc:,}/{rc:,}행 매칭")

    print(f"\n총 처리: {total_matches:,}/{total_rows:,}행")

    # Build overall patterns for each key
    overall_out = {}
    for key in ALL_KEYS:
        overall_out[key] = build_pattern(total_accum, key)

    # Build per-road patterns
    all_roads = set()
    for key in ALL_KEYS:
        if key in total_accum:
            all_roads.update(total_accum[key].keys())

    roads_out = {}
    for road in sorted(all_roads):
        if not road:
            continue
        entry = {}
        for key in ALL_KEYS:
            entry[key] = build_road_pattern(total_accum, road, key)
        roads_out[road] = entry

    output = {
        "meta": {
            "months": months,
            "link_count": len(link_set),
            "total_samples": total_matches,
            "day_keys": ALL_KEYS,
            "source": "TOPIS 도로별 일자별 통행속도",
            "generated_at": datetime.now().isoformat(),
        },
        "overall": overall_out,
        "roads": roads_out,
    }

    out_path = REF_DIR / "topis_traffic_pattern.json"
    REF_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    print(f"\n출력: {out_path.name}")
    print(f"  도로 수: {len(roads_out)}")
    for key in ALL_KEYS:
        speeds = overall_out[key]
        print(f"  {key:>8s}: {min(speeds):.1f} ~ {max(speeds):.1f} km/h")


if __name__ == "__main__":
    main()
