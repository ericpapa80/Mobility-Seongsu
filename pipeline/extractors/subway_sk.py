#!/usr/bin/env python3
"""
성수권역 지하철 역별 시간대별 승하차인원 수집 스크립트

추천 방식 (Docs/Public_Data_api/역별승하차_시간대별_API_검토.md):
- SK Open API (Puzzle): 성수역, 뚝섬역, 서울숲역, 건대입구역 (4역 모두 지원)
- date=latest 또는 date=YYYYMMDD

출력: pipeline/bronze/YYYYMMDD_성수권역_역별_시간대별_승하차인구.csv

사용 예:
  python pipeline/extractors/subway_sk.py -d 20260225
  python pipeline/extractors/subway_sk.py -d latest
"""

import os
import sys
import csv
import time
import argparse
from datetime import datetime
from pathlib import Path

try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("필요 패키지 설치: pip install -r pipeline/requirements.txt")
    sys.exit(1)

# 프로젝트 루트 기준 .env 로드
ROOT = Path(__file__).resolve().parent.parent.parent
PIPELINE = ROOT / "pipeline"
BRONZE_DIR = PIPELINE / "bronze"
load_dotenv(ROOT / ".env")

# 성수권역 4역 (역코드: SK Open API station code)
STATIONS = [
    {"code": "211", "name": "성수역"},
    {"code": "210", "name": "뚝섬역"},
    {"code": "K211", "name": "서울숲역"},
    {"code": "212", "name": "건대입구역"},
]

SK_API_BASE = "https://apis.openapi.sk.com/puzzle/subway/exit/raw/hourly/stations"
EXIT_LABELS = {"1": "승차", "2": "하차", "3": "환승"}


def fetch_station_hourly(station_code: str, date: str, api_key: str, retries: int = 3) -> dict | None:
    """SK Open API로 역별 시간대별 데이터 조회 (429 시 재시도)"""
    url = f"{SK_API_BASE}/{station_code}"
    params = {"date": date}
    headers = {"appkey": api_key}

    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=30)
            if r.status_code == 429:
                wait = (attempt + 1) * 5
                print(f"  속도제한(429) → {wait}초 후 재시도...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if attempt == retries - 1:
                print(f"  오류: {e}")
                return None
            time.sleep((attempt + 1) * 3)
    return None


def parse_response(data: dict, station_info: dict) -> list[dict]:
    """API 응답을 CSV 행 리스트로 변환"""
    rows = []
    if not data:
        return rows

    status = data.get("status", {})
    contents = data.get("contents", {})
    code = status.get("code", "")
    msg = status.get("message", "success")
    total = status.get("totalCount", 0)

    subway_line = contents.get("subwayLine", "")
    station_name = contents.get("stationName", station_info["name"])
    station_code = contents.get("stationCode", station_info["code"])

    raw = contents.get("raw", [])
    for item in raw:
        dt_str = item.get("datetime", "")
        hour = dt_str[8:10] if len(dt_str) >= 10 else ""
        date_str = f"{dt_str[:4]}-{dt_str[4:6]}-{dt_str[6:8]}" if len(dt_str) >= 8 else ""

        rows.append({
            "status_code": code,
            "status_message": msg,
            "status_totalCount": total,
            "subwayLine": subway_line,
            "stationName": station_name,
            "stationCode": station_code,
            "gender": contents.get("gender", "all"),
            "ageGrp": contents.get("ageGrp", "all"),
            "exit": item.get("exit", ""),
            "userCount": item.get("userCount") if item.get("userCount") is not None else "",
            "datetime": dt_str,
            "date": date_str,
            "hour": hour,
        })
    return rows


def run(date: str = "latest", output_dir: Path | None = None):
    """수집 실행"""
    api_key = os.environ.get("PUZZLE_SUBWAY_API_KEY") or os.environ.get("PUZZLE-SUBWAY_API_KEY")
    if not api_key:
        print("환경변수 PUZZLE_SUBWAY_API_KEY 또는 PUZZLE-SUBWAY_API_KEY 필요 (.env 확인)")
        sys.exit(1)

    output_dir = output_dir or BRONZE_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    date_label = date.replace("-", "") if date != "latest" else datetime.now().strftime("%Y%m%d")
    output_file = output_dir / f"{date_label}_성수권역_역별_시간대별_승하차인구.csv"

    fieldnames = [
        "status_code", "status_message", "status_totalCount",
        "subwayLine", "stationName", "stationCode", "gender", "ageGrp",
        "exit", "userCount", "datetime", "date", "hour",
    ]

    all_rows = []
    for i, st in enumerate(STATIONS):
        if i > 0:
            time.sleep(5)  # 429 방지: 역 간 5초 대기
        print(f"수집 중: {st['name']} ({st['code']})...")
        data = fetch_station_hourly(st["code"], date, api_key)
        rows = parse_response(data, st)
        all_rows.extend(rows)
        print(f"  → {len(rows)}건")

    if not all_rows:
        print("수집된 데이터 없음")
        sys.exit(1)

    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n저장: {output_file} ({len(all_rows)}행)")


def main():
    parser = argparse.ArgumentParser(description="성수권역 역별 시간대별 승하차인원 수집 (SK Open API)")
    parser.add_argument(
        "-d", "--date",
        default="latest",
        help="날짜: latest 또는 YYYYMMDD (예: 20260225)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="CSV 출력 디렉터리 (기본: pipeline/bronze)",
    )
    args = parser.parse_args()
    run(date=args.date, output_dir=args.output)


if __name__ == "__main__":
    main()
