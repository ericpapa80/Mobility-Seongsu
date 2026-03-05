#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
성수동 상가 expanded CSV → flat JSON + summary 집계

입력: pipeline/ref/openup_seongsu_stores_20251210_153202_expanded.csv
출력: pipeline/silver/stores_seongsu.json
"""

import csv
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

SRC_CSV = "openup_seongsu_stores_20251210_153202_expanded.csv"

TIME_SLOTS = ["아침", "점심", "오후", "저녁", "밤", "심야", "새벽"]
WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]
AGES = ["20대", "30대", "40대", "50대", "60대"]
TREND_YEARS = list(range(2018, 2026))


def _int(v: str) -> int:
    try:
        return int(float(v)) if v else 0
    except (ValueError, TypeError):
        return 0


def _float(v: str, ndigits: int = 1) -> float:
    try:
        return round(float(v), ndigits) if v else 0.0
    except (ValueError, TypeError):
        return 0.0


def main():
    src = REF_DIR / SRC_CSV
    print(f"1. 로딩: {src.name}")

    with open(src, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    print(f"   → 전체 {len(rows)}개 상가")

    stores = []
    by_category: dict[str, int] = defaultdict(int)
    time_profile: dict[str, int] = defaultdict(int)
    weekday_profile: dict[str, int] = defaultdict(int)

    for r in rows:
        peco_ind = _int(r.get("peco_개인"))
        peco_corp = _int(r.get("peco_법인"))
        peco_for = _int(r.get("peco_외국인"))

        trend = []
        for yr in TREND_YEARS:
            s = _int(r.get(f"{yr}_store"))
            d = _int(r.get(f"{yr}_deli"))
            c = _int(r.get(f"{yr}_cnt"))
            if s or d or c:
                trend.append({"year": yr, "store": s, "deli": d, "cnt": c})

        store = {
            "store_id": r.get("storeId", "").lstrip("0"),
            "name": r.get("storeNm", ""),
            "road_address": r.get("road_address", ""),
            "category_bg": r.get("category_bg", ""),
            "category_mi": r.get("category_mi", ""),
            "category_sl": r.get("category_sl", ""),
            "lng": _float(r.get("x"), 7),
            "lat": _float(r.get("y"), 7),
            "peco_total": peco_ind + peco_corp + peco_for,
            "peco_individual": peco_ind,
            "peco_corporate": peco_corp,
            "peco_foreign": peco_for,
            "times": {slot: _int(r.get(f"times_{slot}")) for slot in TIME_SLOTS},
            "weekday": {day: _int(r.get(f"weekday_{day}")) for day in WEEKDAYS},
            "gender_f": {age: _int(r.get(f"gender_f_{age}")) for age in AGES},
            "gender_m": {age: _int(r.get(f"gender_m_{age}")) for age in AGES},
            "fam": {
                "미혼": _int(r.get("fam_미혼")),
                "기혼": _int(r.get("fam_기혼")),
                "유자녀": _int(r.get("fam_유자녀")),
            },
            "wdwe": {
                "평일": _int(r.get("wdwe_평일")),
                "공휴일": _int(r.get("wdwe_공휴일")),
            },
            "revfreq_weekday": _float(r.get("revfreq_평일")),
            "revfreq_holiday": _float(r.get("revfreq_공휴일")),
            "trend": trend,
        }
        stores.append(store)

        cat = r.get("category_bg", "기타") or "기타"
        by_category[cat] += 1

        for slot in TIME_SLOTS:
            time_profile[slot] += _int(r.get(f"times_{slot}"))

        for day in WEEKDAYS:
            weekday_profile[day] += _int(r.get(f"weekday_{day}"))

    stores.sort(key=lambda x: x["peco_total"], reverse=True)

    output = {
        "meta": {"store_count": len(stores)},
        "summary": {
            "by_category": dict(sorted(by_category.items(), key=lambda x: -x[1])),
            "time_profile": dict(time_profile),
            "weekday_profile": dict(weekday_profile),
        },
        "stores": stores,
    }

    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SILVER_DIR / "stores_seongsu.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    trend_count = sum(1 for s in stores if s["trend"])
    print(f"2. 완료: {len(stores)}개 상가 → {out_path.name}")
    print(f"   카테고리: {dict(by_category)}")
    print(f"   trend 보유: {trend_count}개")


if __name__ == "__main__":
    main()
