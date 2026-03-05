#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
성수동 사업장/급여 GeoJSON → flat JSON + 업종별 집계

입력: pipeline/ref/ss_pt_salary.geojson
출력: pipeline/silver/salary_seongsu.json
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


def main():
    src = REF_DIR / "ss_pt_salary.geojson"
    print(f"1. 로딩: {src.name}")
    with open(src, encoding="utf-8") as f:
        geo = json.load(f)

    total = len(geo["features"])
    print(f"   → 전체 {total}개 사업장")

    workplaces = []
    industry_agg: dict[str, dict] = defaultdict(lambda: {
        "count": 0, "total_employees": 0, "total_salary_sum": 0.0,
    })
    total_employees = 0

    for feat in geo["features"]:
        p = feat["properties"]
        coords = feat["geometry"]["coordinates"]

        employees = int(p.get("가입자수", 0) or 0)
        monthly_salary = float(p.get("월급여추정", 0) or 0)
        annual_salary = float(p.get("연간급여추정", 0) or 0)
        per_person = float(p.get("인당금액", 0) or 0)
        active = bool(p.get("가입상태", False))

        wp = {
            "name": p.get("사업장명", ""),
            "industry": p.get("업종코드명", "기타"),
            "employees": employees,
            "monthly_salary": round(monthly_salary),
            "annual_salary": round(annual_salary),
            "per_person": round(per_person),
            "active": active,
            "lng": round(coords[0], 6),
            "lat": round(coords[1], 6),
            "address": p.get("주소", ""),
        }
        workplaces.append(wp)

        ind = p.get("업종코드명", "기타") or "기타"
        industry_agg[ind]["count"] += 1
        industry_agg[ind]["total_employees"] += employees
        industry_agg[ind]["total_salary_sum"] += monthly_salary * employees
        total_employees += employees

    by_industry = []
    for ind, agg in industry_agg.items():
        avg_sal = agg["total_salary_sum"] / agg["total_employees"] if agg["total_employees"] > 0 else 0
        by_industry.append({
            "industry": ind,
            "count": agg["count"],
            "total_employees": agg["total_employees"],
            "avg_monthly_salary": round(avg_sal),
        })
    by_industry.sort(key=lambda x: -x["total_employees"])

    workplaces.sort(key=lambda x: -x["employees"])

    active_count = sum(1 for w in workplaces if w["active"])
    avg_salary = sum(w["monthly_salary"] for w in workplaces if w["employees"] > 0) / max(1, sum(1 for w in workplaces if w["employees"] > 0))

    output = {
        "meta": {
            "workplace_count": len(workplaces),
            "active_count": active_count,
            "total_employees": total_employees,
        },
        "summary": {
            "by_industry": by_industry[:30],
            "avg_monthly_salary": round(avg_salary),
        },
        "workplaces": workplaces,
    }

    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SILVER_DIR / "salary_seongsu.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    print(f"2. 완료: {len(workplaces)}개 사업장, {len(by_industry)}개 업종 → {out_path.name}")
    print(f"   총 종업원: {total_employees:,}명, 평균 월급여: {round(avg_salary):,}원")
    print(f"   상위 업종:")
    for ind in by_industry[:5]:
        print(f"     {ind['industry']}: {ind['count']}개소, {ind['total_employees']}명, 평균 {ind['avg_monthly_salary']:,}원")


if __name__ == "__main__":
    main()
