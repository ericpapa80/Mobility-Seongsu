#!/usr/bin/env python3
"""
서울열린데이터광장 CardSubwayTime API - 분당선 서울숲역 시간대별 승하차 수집

- 월별 데이터 (USE_MM: YYYYMM)
- HR_4~HR_23 승차/하차 → (hour, rideNope, gffNope) 행으로 변환
- 기존 public_...상세_카드권종별.csv 형식과 호환 (trnscd=전체)

참고: Docs/서울열린데이터광장/분당선_서울열린데이터_추가_가능여부_검토.md
"""

import os
import sys
import csv
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("필요 패키지 설치: pip install -r Collect/requirements.txt")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

API_BASE = "http://openapi.seoul.go.kr:8088"

# 분당선 서울숲역 (호선명=분당선, 역명=서울숲)
LINE_NM = "분당선"
STN_NM = "서울숲"


def fetch_card_subway_time(key: str, use_mm: str) -> dict | None:
    """CardSubwayTime API 호출 (분당선/서울숲)"""
    url = f"{API_BASE}/{key}/xml/CardSubwayTime/1/5/{use_mm}/{LINE_NM}/{STN_NM}/"
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        r.encoding = "utf-8"
        return ET.fromstring(r.text)
    except ET.ParseError as e:
        print(f"  XML 파싱 오류: {e}")
        return None
    except Exception as e:
        print(f"  오류: {e}")
        return None


def parse_hourly_data(root: ET.Element) -> list[dict]:
    """
    HR_4_GET_ON_NOPE ~ HR_23_GET_OFF_NOPE 파싱
    → (hour, rideNope, gffNope) 리스트 (00~23시)
    """
    row = root.find(".//row")
    if row is None:
        return []

    by_hour = {h: {"ride": 0, "gff": 0} for h in range(24)}

    for hour in range(4, 24):
        ride_tag = f"HR_{hour}_GET_ON_NOPE"
        gff_tag = f"HR_{hour}_GET_OFF_NOPE"
        ride_el = row.find(ride_tag)
        gff_el = row.find(gff_tag)
        ride_val = int(ride_el.text or 0) if ride_el is not None else 0
        gff_val = int(gff_el.text or 0) if gff_el is not None else 0
        by_hour[hour]["ride"] = ride_val
        by_hour[hour]["gff"] = gff_val

    return [
        {
            "hour": f"{h:02d}",
            "rideNope": by_hour[h]["ride"],
            "gffNope": by_hour[h]["gff"],
        }
        for h in range(24)
    ]


def to_detail_rows(hourly: list[dict], use_mm: str, ref_date: str) -> list[dict]:
    """기존 상세 CSV 포맷으로 변환 (trnscd=전체)"""
    # use_mm=202602 → ref_date=2026-02-25 형태로 기준일 사용
    rows = []
    for row in hourly:
        rows.append({
            "date": ref_date,
            "hour": row["hour"],
            "stationName": STN_NM + "역",
            "lineNm": LINE_NM,
            "stnCd": "",
            "stnNo": "",
            "trnscdSeCd": "",
            "trnscdSeCdNm": "전체",
            "trnscdUserSeCd": "",
            "trnscdUserSeCdNm": "전체",
            "rideNope": row["rideNope"],
            "gffNope": row["gffNope"],
            "totalNope": row["rideNope"] + row["gffNope"],
        })
    return rows


def run(use_mm: str, ref_date: str, output_dir: Path, append_to: Path | None):
    """수집 실행"""
    key = os.environ.get("SEOUL_OPEN_DATA_KEY") or os.environ.get("SEOUL_OPEN_API_KEY")
    if not key:
        print("환경변수 SEOUL_OPEN_DATA_KEY 필요 (.env)")
        print("서울열린데이터광장(data.seoul.go.kr)에서 인증키 발급 후 .env에 추가하세요.")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"수집 중: {LINE_NM} {STN_NM}역 (USE_MM={use_mm})...")

    root = fetch_card_subway_time(key, use_mm)
    if root is None:
        print("  → API 호출 실패")
        sys.exit(1)

    # 에러 체크 (Open API 에러 응답)
    result_msg = root.find(".//RESULT/CODE")
    if result_msg is not None and result_msg.text and result_msg.text != "INFO-000":
        code = result_msg.text
        msg = root.find(".//RESULT/MESSAGE")
        err = msg.text if msg is not None else ""
        print(f"  → API 오류: {code} {err}")
        sys.exit(1)

    hourly = parse_hourly_data(root)
    if not hourly:
        print("  → 파싱된 데이터 없음")
        sys.exit(1)

    rows = to_detail_rows(hourly, use_mm, ref_date)
    print(f"  → {len(rows)}시간대")

    fieldnames = [
        "date", "hour", "stationName", "lineNm", "stnCd", "stnNo",
        "trnscdSeCd", "trnscdSeCdNm", "trnscdUserSeCd", "trnscdUserSeCdNm",
        "rideNope", "gffNope", "totalNope",
    ]

    if append_to and append_to.exists():
        with open(append_to, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerows(rows)
        print(f"\n추가 저장: {append_to} (+{len(rows)}행)")
    else:
        output_file = output_dir / f"seoul_subway_{use_mm}_분당선_{STN_NM}_시간대별_승하차.csv"
        with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\n저장: {output_file} ({len(rows)}행)")


def main():
    parser = argparse.ArgumentParser(
        description="서울열린데이터 CardSubwayTime - 분당선 서울숲역 시간대별 승하차"
    )
    parser.add_argument(
        "-m", "--month",
        default="202601",
        help="USE_MM YYYYMM (기본: 202601, 202602는 아직 미갱신될 수 있음)",
    )
    parser.add_argument(
        "-r", "--ref-date",
        default="2026-02-25",
        help="CSV date 컬럼 기준일 (기본: 2026-02-25)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=ROOT / "Collect" / "raw",
    )
    parser.add_argument(
        "--append",
        type=Path,
        default=None,
        metavar="FILE",
        help="기존 CSV에 append (예: Collect/raw/public_20260225_...상세_카드권종별.csv)",
    )
    args = parser.parse_args()
    run(args.month, args.ref_date, args.output, args.append)


if __name__ == "__main__":
    main()
