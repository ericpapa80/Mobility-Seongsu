#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1단계: 성수동 버스정류장 + 경유노선 목록 확보

- 서울시 버스 API (ws.bus.go.kr): getStationByPos, getRouteByStation
- 성수동 중심(성수역) 반경 내 정류장 조회 → 각 정류장별 경유노선 수집
- 결과: pipeline/ref/bus_stops_routes.json, bus_routes.txt

필요: 공공데이터포털 서울특별시_정류소정보조회(15000303) 활용신청 후 serviceKey
      .env에 SEOUL_BUS_API_KEY 또는 PUBLIC_DATA_KEY 사용

사용 예:
  python pipeline/extractors/bus_stops.py
  python pipeline/extractors/bus_stops.py -o pipeline/ref
"""

import os
import sys
import io
import json

# Windows 터미널 한글 깨짐 방지
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
import time
import argparse
from pathlib import Path

try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("필요 패키지: pip install -r pipeline/requirements.txt")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent.parent
PIPELINE = ROOT / "pipeline"
REF_DIR = PIPELINE / "ref"
load_dotenv(ROOT / ".env")

BUS_API = "http://ws.bus.go.kr/api/rest/stationinfo"

# 성수동 중심 (성수역 좌표, WGS84)
SEONGSU_CENTER = {"tmX": 127.055972, "tmY": 37.544583}
DEFAULT_RADIUS = 1200  # m, 성수동 영역 커버


def get_stations_by_pos(service_key: str, tm_x: float, tm_y: float, radius: int = 1200, verbose: bool = False) -> list[dict]:
    """좌표 기반 근접 정류소 목록 조회 (서울시 버스 API)"""
    url = f"{BUS_API}/getStationByPos"
    params = {
        "serviceKey": service_key,
        "tmX": tm_x,
        "tmY": tm_y,
        "radius": radius,
        "numOfRows": 500,
        "resultType": "json",
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        r.encoding = "utf-8"
        text = r.text
        if verbose:
            print(f"  [응답 일부] {text[:500]}...")
        data = r.json()
    except ValueError:
        # JSON 파싱 실패: 공공데이터 포털 API는 데이터셋별 별도 활용신청 필요
        print(f"  getStationByPos 오류: '서울특별시_정류소정보조회(15000303)' 별도 활용신청 후 동일 인증키로 사용 가능.")
        return []
    except Exception as e:
        print(f"  getStationByPos 오류: {e}")
        return []

    try:
        # 인증키 미등록 등 오류 체크
        msg_hdr = data.get("msgHeader", {}) or data.get("MsgHeader", {})
        if msg_hdr.get("headerCd") in ("7", "4", "12") or "NOT REGISTERED" in str(data):
            print(f"  getStationByPos: {msg_hdr.get('headerMsg', '인증키 미등록')}")
            print(f"  → 공공데이터포털(data.go.kr) '서울특별시_정류소정보조회(15000303)' 활용신청 필요")
            return []
        # 공공데이터 포털 응답: comMsgHeader, msgBody 등
        if "response" in data:
            body = data["response"].get("body", {})
            items = body.get("items")
            if items:
                item = items.get("item")
                if item is None:
                    return []
                return item if isinstance(item, list) else [item]
        body = data.get("msgBody", {}) or data.get("MsgBody", {})
        item = body.get("itemList") or body.get("ItemList") or body.get("item")
        if item is None:
            return []
        return item if isinstance(item, list) else [item]
    except Exception:
        return []


def get_route_by_station(service_key: str, ars_id: str) -> list[dict]:
    """정류소별 경유노선 목록 조회"""
    url = f"{BUS_API}/getRouteByStation"
    params = {"serviceKey": service_key, "arsId": ars_id, "resultType": "json"}
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        r.encoding = "utf-8"
        data = r.json()
    except Exception as e:
        return []

    try:
        body = data.get("msgBody", {}) or data.get("MsgBody", {})
        item = body.get("itemList") or body.get("ItemList")
        if item is None:
            return []
        return item if isinstance(item, list) else [item]
    except Exception:
        return []


def run(tm_x: float, tm_y: float, radius: int, output_dir: Path) -> None:
    key = os.environ.get("SEOUL_BUS_API_KEY") or os.environ.get("PUBLIC_DATA_KEY")
    if not key:
        print("환경변수 SEOUL_BUS_API_KEY 또는 PUBLIC_DATA_KEY 필요 (.env)")
        print("공공데이터포털(data.go.kr) → 서울특별시_정류소정보조회(15000303) 활용신청")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"1단계: 성수동 버스정류장 조회 (반경 {radius}m)...")

    stations = get_stations_by_pos(key, tm_x, tm_y, radius)
    if not stations:
        print("  → 근접 정류소 없음 (API 키·좌표 확인)")
        sys.exit(1)
    print(f"  → {len(stations)}개 정류장")

    result = []
    route_set = set()
    for i, st in enumerate(stations):
        ars_id = st.get("arsId") or st.get("arsid") or ""
        st_id = st.get("stId") or st.get("stid") or ""
        st_nm = st.get("stNm") or st.get("stnm") or ""
        if not ars_id:
            continue
        time.sleep(0.15)
        routes = get_route_by_station(key, ars_id)
        route_nos = [r.get("busRouteId") or r.get("busRouteNm") or r.get("routeNo", "") for r in routes]
        route_nos = [str(x).strip() for x in route_nos if x]
        for rn in route_nos:
            route_set.add(rn)
        result.append({
            "stops_id": st_id,
            "stops_ars_no": ars_id,
            "stops_nm": st_nm,
            "tmX": st.get("tmX"), "tmY": st.get("tmY"),
            "route_ids": route_nos,
            "route_count": len(route_nos),
        })
        if (i + 1) % 5 == 0:
            print(f"  진행: {i+1}/{len(stations)}")

    out_json = output_dir / "bus_stops_routes.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"stops": result, "route_ids": list(route_set)}, f, ensure_ascii=False, indent=2)

    # CardBusTimeNew용 노선번호 매핑: busRouteId → RTE_NO (노선번호)
    # CardBusTimeNew는 노선번호(예: 2412, 7730)를 사용. busRouteId가 숫자면 동일할 수 있음
    route_ids_sorted = sorted(route_set, key=lambda x: (len(x), x))
    out_routes = output_dir / "bus_routes.txt"
    with open(out_routes, "w", encoding="utf-8") as f:
        f.write("\n".join(route_ids_sorted))

    print(f"\n저장: {out_json}")
    print(f"저장: {out_routes} ({len(route_set)}개 노선)")
    print(f"→ 2단계: collect_seoul_bus_seongsu.py -m YYYYMM 실행")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="성수동 버스정류장 + 경유노선 목록 수집")
    parser.add_argument("--tmX", type=float, default=SEONGSU_CENTER["tmX"], help="중심 X(경도)")
    parser.add_argument("--tmY", type=float, default=SEONGSU_CENTER["tmY"], help="중심 Y(위도)")
    parser.add_argument("--radius", type=int, default=DEFAULT_RADIUS, help="반경(m)")
    parser.add_argument("-o", "--output", type=Path, default=REF_DIR)
    args = parser.parse_args()
    run(args.tmX, args.tmY, args.radius, args.output)
