#!/usr/bin/env python3
"""
공공데이터 getStnPsgr (B553766) 역별 시간대별 승하차인원 수집

- 성수역, 뚝섬역, 건대입구역 (2호선)
- 한 시간 간격, 전 시간대 (00~23시)
- 기본: 승차/하차 집계 | --detail: 교통카드·승객구분 상세
- CSV 출력

코드 의미: Docs/Public_Data_api/getStnPsgr_코드_참조.md
"""

import os
import sys
import csv
import time
import argparse
from collections import defaultdict
from pathlib import Path

try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("필요 패키지 설치: pip install -r Collect/requirements.txt")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

API_URL = "https://apis.data.go.kr/B553766/psgr/getStnPsgr"

STATIONS = [
    {"stnNm": "성수", "lineNm": "2"},
    {"stnNm": "뚝섬", "lineNm": "2"},
    {"stnNm": "건대입구", "lineNm": "2"},
]


def fetch_station(date_ymd: str, stn_nm: str, line_nm: str, service_key: str) -> list[dict]:
    """getStnPsgr API 호출 (전 시간대)"""
    params = {
        "serviceKey": service_key,
        "numOfRows": 50000,
        "pasngYmd": date_ymd,
        "stnNm": stn_nm,
        "lineNm": line_nm,
        "dataType": "JSON",
    }
    try:
        r = requests.get(API_URL, params=params, timeout=60)
        r.raise_for_status()
        r.encoding = "utf-8"
        data = r.json()
    except Exception as e:
        print(f"  오류: {e}")
        return []

    body = data.get("response", {}).get("body", {})
    items = body.get("items")
    if not items:
        return []

    item_list = items.get("item")
    if not item_list:
        return []
    return item_list if isinstance(item_list, list) else [item_list]


def aggregate_by_hour(items: list[dict]) -> list[dict]:
    """시간대별 승차/하차 집계 (카드·권종 구분 합산), 전시간대(00~23) 보장"""
    by_hour = defaultdict(lambda: {"ride": 0, "gff": 0})
    for it in items:
        hr = str(it.get("pasngHr", "")).zfill(2)  # 5 -> 05
        ride = int(it.get("rideNope", 0) or 0)
        gff = int(it.get("gffNope", 0) or 0)
        by_hour[hr]["ride"] += ride
        by_hour[hr]["gff"] += gff

    return [
        {"hour": f"{h:02d}", "rideNope": by_hour[f"{h:02d}"]["ride"], "gffNope": by_hour[f"{h:02d}"]["gff"]}
        for h in range(24)
    ]


def to_detail_rows(items: list[dict], stn_nm: str) -> list[dict]:
    """원본 API 행을 상세 CSV 행으로 변환 (교통카드·승객구분 포함)"""
    rows = []
    for it in items:
        rows.append({
            "date": f"{it.get('pasngDe','')[:4]}-{it.get('pasngDe','')[4:6]}-{it.get('pasngDe','')[6:8]}",
            "hour": str(it.get("pasngHr", "")).zfill(2),
            "stationName": stn_nm + "역",
            "lineNm": it.get("lineNm", ""),
            "stnCd": it.get("stnCd", ""),
            "stnNo": it.get("stnNo", ""),
            "trnscdSeCd": it.get("trnscdSeCd", ""),
            "trnscdSeCdNm": it.get("trnscdSeCdNm", ""),
            "trnscdUserSeCd": it.get("trnscdUserSeCd", ""),
            "trnscdUserSeCdNm": it.get("trnscdUserSeCdNm", ""),
            "rideNope": it.get("rideNope", 0),
            "gffNope": it.get("gffNope", 0),
            "totalNope": int(it.get("rideNope", 0) or 0) + int(it.get("gffNope", 0) or 0),
        })
    return rows


def run(date: str, output_dir: Path, detail: bool = False):
    """수집 실행"""
    key = os.environ.get("PUBLIC_DATA_KEY")
    if not key:
        print("환경변수 PUBLIC_DATA_KEY 필요 (.env)")
        sys.exit(1)

    date_ymd = date.replace("-", "")
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "_상세_카드권종별" if detail else ""
    output_file = output_dir / f"public_{date_ymd}_성수뚝섬건대_시간대별_승하차{suffix}.csv"

    all_rows = []
    for i, st in enumerate(STATIONS):
        if i > 0:
            time.sleep(1)  # API 부하 완화
        print(f"수집 중: {st['stnNm']}역 ({st['lineNm']}호선)...")
        items = fetch_station(date_ymd, st["stnNm"], st["lineNm"], key)

        if detail:
            rows = to_detail_rows(items, st["stnNm"])
            all_rows.extend(rows)
            print(f"  → {len(rows)}건 (카드·권종별)")
        else:
            agg = aggregate_by_hour(items)
            for row in agg:
                all_rows.append({
                    "date": f"{date_ymd[:4]}-{date_ymd[4:6]}-{date_ymd[6:8]}",
                    "hour": row["hour"],
                    "stationName": st["stnNm"] + "역",
                    "lineNm": st["lineNm"] + "호선",
                    "rideNope": row["rideNope"],
                    "gffNope": row["gffNope"],
                    "totalNope": row["rideNope"] + row["gffNope"],
                })
            print(f"  → {len(agg)}시간대")

    if not all_rows:
        print("수집된 데이터 없음")
        sys.exit(1)

    if detail:
        fieldnames = ["date", "hour", "stationName", "lineNm", "stnCd", "stnNo",
                      "trnscdSeCd", "trnscdSeCdNm", "trnscdUserSeCd", "trnscdUserSeCdNm",
                      "rideNope", "gffNope", "totalNope"]
    else:
        fieldnames = ["date", "hour", "stationName", "lineNm", "rideNope", "gffNope", "totalNope"]

    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n저장: {output_file} ({len(all_rows)}행)")


def main():
    parser = argparse.ArgumentParser(description="공공데이터 getStnPsgr - 성수/뚝섬/건대입구 시간대별 승하차")
    parser.add_argument("-d", "--date", default="20260225", help="YYYYMMDD (기본: 20260225)")
    parser.add_argument("-o", "--output", type=Path, default=ROOT / "Collect" / "raw")
    parser.add_argument("--detail", action="store_true",
                        help="교통카드·승객구분 상세 (trnscdSeCdNm, trnscdUserSeCdNm 등)")
    args = parser.parse_args()
    run(args.date, args.output, detail=args.detail)


if __name__ == "__main__":
    main()
