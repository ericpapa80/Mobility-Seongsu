import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter(tags=["map-data"])

logger = logging.getLogger(__name__)

PIPELINE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "pipeline"
REF_DIR = PIPELINE_DIR / "ref"
SILVER_DIR = PIPELINE_DIR / "silver"

RISK_POINTS = [
    {"name": "공사구간", "lat": 37.5435, "lng": 127.0610, "risk": "high"},
    {"name": "행사구간", "lat": 37.5490, "lng": 127.0550, "risk": "mid"},
]


_cache: dict[str, object] = {}


def _load_silver(filename: str) -> dict:
    if filename not in _cache:
        with open(SILVER_DIR / filename, encoding="utf-8") as f:
            _cache[filename] = json.load(f)
    return _cache[filename]


def _load_geojson(filename: str) -> dict:
    with open(REF_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


# ── DB-first helpers (각 함수는 DB 조회 성공 시 결과 반환, 실패 시 None) ──

async def _db_get_traffic(hour: Optional[int] = None) -> Optional[dict]:
    """traffic_segments 테이블에서 교통속도 조회. DB 없으면 None."""
    from app.db.database import is_db_available, async_session
    if not is_db_available() or async_session is None:
        return None
    try:
        from sqlalchemy import text as sa_text
        async with async_session() as session:
            rows = (await session.execute(sa_text(
                "SELECT link_id, road_name, direction, distance, lanes, road_type, area_type, speeds, "
                "ST_AsGeoJSON(geom)::json AS geom_json FROM traffic_segments"
            ))).all()
        if not rows:
            return None
        segments = []
        for r in rows:
            coords = []
            if r.geom_json:
                coords = r.geom_json.get("coordinates", [])
            sp = r.speeds or []
            seg = {
                "link_id": r.link_id,
                "road_name": r.road_name or "",
                "direction": r.direction or "",
                "distance": r.distance or 0,
                "lanes": r.lanes or 1,
                "road_type": r.road_type or "",
                "area_type": r.area_type or "",
                "speeds": sp,
                "coordinates": coords,
            }
            if hour is not None and sp:
                seg["speed"] = sp[hour] if hour < len(sp) else 0
            segments.append(seg)
        return {"meta": {"segment_count": len(segments)}, "segments": segments}
    except Exception as exc:
        logger.warning("DB traffic query failed, fallback to JSON: %s", exc)
        return None


async def _db_get_subway_hourly() -> Optional[dict]:
    """subway_stations + subway_station_hourly 테이블 조회. DB 없으면 None."""
    from app.db.database import is_db_available, async_session
    if not is_db_available() or async_session is None:
        return None
    try:
        from sqlalchemy import text as sa_text
        async with async_session() as session:
            sta_rows = (await session.execute(sa_text(
                "SELECT id, name, sub_sta_sn, use_date, "
                "ST_X(geom) AS lng, ST_Y(geom) AS lat FROM subway_stations"
            ))).all()
            if not sta_rows:
                return None
            hourly_rows = (await session.execute(sa_text(
                "SELECT station_id, hour, ride, alight FROM subway_station_hourly ORDER BY station_id, hour"
            ))).all()

        hourly_map: dict[int, dict] = {}
        for h in hourly_rows:
            if h.station_id not in hourly_map:
                hourly_map[h.station_id] = {"ride": [0] * 24, "alight": [0] * 24}
            if h.hour < 24:
                hourly_map[h.station_id]["ride"][h.hour] = h.ride
                hourly_map[h.station_id]["alight"][h.hour] = h.alight

        stations = []
        use_date = sta_rows[0].use_date if sta_rows else ""
        for s in sta_rows:
            hr = hourly_map.get(s.id, {"ride": [0] * 24, "alight": [0] * 24})
            stations.append({
                "name": s.name,
                "lat": s.lat,
                "lng": s.lng,
                "sub_sta_sn": s.sub_sta_sn,
                "ridership": hr,
            })
        return {"meta": {"date": use_date, "station_count": len(stations)}, "stations": stations}
    except Exception as exc:
        logger.warning("DB subway query failed, fallback to JSON: %s", exc)
        return None


async def _db_get_stores(category: Optional[str] = None) -> Optional[dict]:
    """stores 테이블 조회. DB 없으면 None."""
    from app.db.database import is_db_available, async_session
    if not is_db_available() or async_session is None:
        return None
    try:
        from sqlalchemy import text as sa_text
        where = "WHERE category_bg = :cat" if category else ""
        async with async_session() as session:
            rows = (await session.execute(sa_text(
                f"SELECT store_id, name, road_address, category_bg, category_mi, category_sl, "
                f"ST_X(geom) AS lng, ST_Y(geom) AS lat, peco_total, peco_individual, "
                f"peco_corporate, peco_foreign, times, weekday, gender_f, gender_m "
                f"FROM stores {where}"
            ), {"cat": category} if category else {})).all()
        if not rows:
            return None
        stores = [
            {
                "store_id": r.store_id, "name": r.name, "road_address": r.road_address,
                "category_bg": r.category_bg, "category_mi": r.category_mi, "category_sl": r.category_sl,
                "lng": r.lng, "lat": r.lat,
                "peco_total": r.peco_total, "peco_individual": r.peco_individual,
                "peco_corporate": r.peco_corporate, "peco_foreign": r.peco_foreign,
                "times": r.times or {}, "weekday": r.weekday or {},
                "gender_f": r.gender_f or {}, "gender_m": r.gender_m or {},
            }
            for r in rows
        ]
        return {"meta": {"store_count": len(stores)}, "stores": stores}
    except Exception as exc:
        logger.warning("DB stores query failed, fallback to JSON: %s", exc)
        return None


async def _db_get_salary(industry: Optional[str] = None) -> Optional[dict]:
    """salary_workplaces 테이블 조회. DB 없으면 None."""
    from app.db.database import is_db_available, async_session
    if not is_db_available() or async_session is None:
        return None
    try:
        from sqlalchemy import text as sa_text
        where = "WHERE industry = :ind" if industry else ""
        async with async_session() as session:
            rows = (await session.execute(sa_text(
                f"SELECT name, industry, employees, monthly_salary, "
                f"ST_X(geom) AS lng, ST_Y(geom) AS lat FROM salary_workplaces {where}"
            ), {"ind": industry} if industry else {})).all()
        if not rows:
            return None
        workplaces = [
            {
                "name": r.name, "industry": r.industry,
                "employees": r.employees, "monthly_salary": r.monthly_salary,
                "lng": r.lng, "lat": r.lat,
            }
            for r in rows
        ]
        return {"meta": {"workplace_count": len(workplaces)}, "workplaces": workplaces}
    except Exception as exc:
        logger.warning("DB salary query failed, fallback to JSON: %s", exc)
        return None


async def _db_get_foottraffic() -> Optional[dict]:
    """foottraffic_links 테이블 조회. DB 없으면 None."""
    from app.db.database import is_db_available, async_session
    if not is_db_available() or async_session is None:
        return None
    try:
        from sqlalchemy import text as sa_text
        async with async_session() as session:
            rows = (await session.execute(sa_text(
                "SELECT road_link_id, "
                "ST_AsGeoJSON(geom)::json AS geom_json, "
                "ARRAY[ST_X(centroid), ST_Y(centroid)] AS centroid_arr, "
                "data FROM foottraffic_links"
            ))).all()
        if not rows:
            return None
        links = []
        for r in rows:
            coords = []
            if r.geom_json:
                coords = r.geom_json.get("coordinates", [])
            links.append({
                "road_link_id": r.road_link_id,
                "coordinates": coords,
                "centroid": list(r.centroid_arr) if r.centroid_arr else [],
                "data": r.data or {},
            })
        return {"meta": {"link_count": len(links)}, "links": links}
    except Exception as exc:
        logger.warning("DB foottraffic query failed, fallback to JSON: %s", exc)
        return None


def _build_subway_stations() -> list[dict]:
    """ss_pt_subway_statn.geojson → API 응답 형식으로 변환"""
    geo = _load_geojson("ss_pt_subway_statn.geojson")
    return [
        {
            "name": feat["properties"]["KOR_SUB_NM"],
            "lat": feat["geometry"]["coordinates"][1],
            "lng": feat["geometry"]["coordinates"][0],
            "sub_sta_sn": feat["properties"]["SUB_STA_SN"],
        }
        for feat in geo["features"]
    ]


def _build_subway_entrances() -> list[dict]:
    """ss_pt_subway_entrc.geojson → API 응답 형식으로 변환"""
    geo = _load_geojson("ss_pt_subway_entrc.geojson")
    return [
        {
            "station_name": feat["properties"]["KOR_SUB_NM"],
            "entrance_no": feat["properties"]["ENTRC_NO"],
            "lat": feat["geometry"]["coordinates"][1],
            "lng": feat["geometry"]["coordinates"][0],
            "sub_sta_sn": feat["properties"]["SUB_STA_SN"],
        }
        for feat in geo["features"]
    ]


def _build_subway_polygons() -> dict:
    """ss_pg_subway_statn.geojson → GeoJSON FeatureCollection 그대로 전달"""
    return _load_geojson("ss_pg_subway_statn.geojson")


def _load_subway_hourly() -> dict:
    with open(SILVER_DIR / "subway_stations_hourly.json", encoding="utf-8") as f:
        return json.load(f)


SUBWAY_STATIONS = _build_subway_stations()
SUBWAY_ENTRANCES = _build_subway_entrances()
SUBWAY_POLYGONS = _build_subway_polygons()
SUBWAY_HOURLY = _load_subway_hourly()


@router.get("/subway-stations")
async def get_subway_stations():
    return {"stations": SUBWAY_STATIONS}


@router.get("/subway-entrances")
async def get_subway_entrances():
    return {"entrances": SUBWAY_ENTRANCES}


@router.get("/subway-polygons")
async def get_subway_polygons():
    return SUBWAY_POLYGONS


@router.get("/subway-hourly")
async def get_subway_hourly():
    db_result = await _db_get_subway_hourly()
    if db_result:
        return db_result
    return SUBWAY_HOURLY


@router.get("/risk-points")
async def get_risk_points():
    return {"points": RISK_POINTS}


# ── New GeoJSON-backed endpoints ──────────────────────────────────

@router.get("/traffic")
async def get_traffic(hour: Optional[int] = Query(None, ge=0, le=23)):
    db_result = await _db_get_traffic(hour)
    if db_result:
        if hour is not None:
            db_result["hour"] = hour
        return db_result
    # JSON fallback
    data = _load_silver("traffic_seongsu.json")
    if hour is not None:
        segments = [{**seg, "speed": seg["speeds"][hour]} for seg in data["segments"]]
        return {"meta": data["meta"], "hour": hour, "segments": segments}
    return data


@router.get("/traffic/pattern")
async def get_traffic_pattern():
    """TOPIS 과거 데이터 기반 평일/주말 시간대별 패턴"""
    key = "topis_traffic_pattern.json"
    if key not in _cache:
        path = REF_DIR / key
        if not path.exists():
            return {"error": "pattern data not found", "overall": None, "roads": {}}
        with open(path, encoding="utf-8") as f:
            _cache[key] = json.load(f)
    data = _cache[key]
    return data


@router.get("/traffic/realtime")
async def get_traffic_realtime():
    """TOPIS 실시간 도로 소통 정보 (5분 캐시)"""
    from app.config import get_settings
    from app.services.topis_client import get_topis_client

    settings = get_settings()
    if not settings.SEOUL_OPEN_DATA_KEY:
        return {"error": "SEOUL_OPEN_DATA_KEY not configured", "segments": []}

    client = get_topis_client(settings.SEOUL_OPEN_DATA_KEY)
    return await client.get_realtime()


@router.get("/traffic/realtime/history")
async def get_traffic_realtime_history(
    compare: str = Query("yesterday", regex="^(yesterday|last_week|hours_24)$"),
):
    """DB에 축적된 실시간 이력에서 비교 데이터 조회

    compare:
      - yesterday: 어제 같은 시간대 (±30분)
      - last_week: 지난주 같은 요일 같은 시간대 (±30분)
      - hours_24: 최근 24시간 시간대별 평균
    """
    from datetime import datetime, timedelta, timezone

    from app.db.database import is_db_available, async_session
    if not is_db_available() or async_session is None:
        return {"error": "DB not available", "data": None}

    from sqlalchemy import select, func as sa_func, extract
    from app.db.models import TrafficRealtimeLog

    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST)

    async with async_session() as session:
        if compare == "hours_24":
            cutoff = now - timedelta(hours=24)
            stmt = (
                select(
                    extract("hour", TrafficRealtimeLog.fetched_at).label("hour"),
                    sa_func.avg(TrafficRealtimeLog.speed).label("avg_speed"),
                    sa_func.count().label("samples"),
                )
                .where(TrafficRealtimeLog.fetched_at >= cutoff)
                .group_by("hour")
                .order_by("hour")
            )
            rows = (await session.execute(stmt)).all()
            data = [
                {"hour": int(r.hour), "avg_speed": round(float(r.avg_speed), 2), "samples": r.samples}
                for r in rows
            ]
            return {"compare": compare, "reference_time": now.isoformat(), "data": data}

        if compare == "yesterday":
            ref_time = now - timedelta(days=1)
        else:  # last_week
            ref_time = now - timedelta(weeks=1)

        window_start = ref_time - timedelta(minutes=30)
        window_end = ref_time + timedelta(minutes=30)

        stmt = (
            select(
                sa_func.avg(TrafficRealtimeLog.speed).label("avg_speed"),
                sa_func.avg(TrafficRealtimeLog.travel_time).label("avg_travel_time"),
                sa_func.count().label("samples"),
            )
            .where(TrafficRealtimeLog.fetched_at >= window_start)
            .where(TrafficRealtimeLog.fetched_at <= window_end)
        )
        row = (await session.execute(stmt)).one_or_none()

        if row and row.samples > 0:
            data = {
                "avg_speed": round(float(row.avg_speed), 2),
                "avg_travel_time": round(float(row.avg_travel_time), 2),
                "samples": row.samples,
                "window": {
                    "start": window_start.isoformat(),
                    "end": window_end.isoformat(),
                },
            }
        else:
            data = None

        return {"compare": compare, "reference_time": ref_time.isoformat(), "data": data}


@router.get("/foottraffic")
async def get_foottraffic():
    db_result = await _db_get_foottraffic()
    if db_result:
        return db_result
    return _load_silver("foottraffic_seongsu.json")


@router.get("/stores")
async def get_stores(
    category: Optional[str] = Query(None),
    time_slot: Optional[str] = Query(None),
):
    db_result = await _db_get_stores(category)
    if db_result:
        return db_result
    # JSON fallback
    data = _load_silver("stores_seongsu.json")
    stores = data["stores"]
    if category:
        stores = [s for s in stores if s["category_bg"] == category]
    return {"meta": data["meta"], "stores": stores}


@router.get("/stores/summary")
async def get_stores_summary():
    data = _load_silver("stores_seongsu.json")
    return {"summary": data["summary"], "meta": data["meta"]}


@router.get("/buildings")
async def get_buildings():
    return _load_geojson("ss_pg_building.geojson")


@router.get("/salary")
async def get_salary(industry: Optional[str] = Query(None)):
    db_result = await _db_get_salary(industry)
    if db_result:
        return db_result
    # JSON fallback
    data = _load_silver("salary_seongsu.json")
    workplaces = data["workplaces"]
    if industry:
        workplaces = [w for w in workplaces if w["industry"] == industry]
    return {
        "meta": data["meta"],
        "summary": data["summary"],
        "workplaces": workplaces,
    }


@router.get("/krafton-cluster")
async def get_krafton_cluster():
    return _load_geojson("ss_pg_krafton_cluster.geojson")


@router.get("/commercial-area")
async def get_commercial_area():
    return _load_geojson("ss_pg_commercial_area.geojson")


@router.get("/cross-analysis")
async def get_cross_analysis():
    """보행-상권 상관, 직주 근접성, 클러스터 활력도 종합 분석"""
    import math

    foot_data = _load_silver("foottraffic_seongsu.json")
    store_data = _load_silver("stores_seongsu.json")
    salary_data = _load_silver("salary_seongsu.json")
    krafton_geo = _load_geojson("ss_pg_krafton_cluster.geojson")

    TMZON_LIST = ["00~05", "06~10", "11~13", "14~16", "17~20", "21~23"]

    # 5-1: foottraffic vs stores – 보행 밀도 상위 50 링크 주변 상가 수
    foot_links = foot_data["links"]
    stores = store_data["stores"]

    def haversine_m(lat1, lng1, lat2, lng2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lng2 - lng1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _get_acost_allday(link: dict) -> int:
        """data 구조에서 평일 전체 종일 acost 추출 (하위호환)"""
        data = link.get("data", link.get("by_tmzon_legacy", {}))
        if "1" in data:
            return data.get("1", {}).get("00", {}).get("종일", {}).get("acost", 0)
        return data.get("종일", {}).get("acost", 0)

    top_links = sorted(
        foot_links,
        key=lambda l: _get_acost_allday(l),
        reverse=True,
    )[:50]

    foot_store_corr = []
    for link in top_links:
        cx, cy = link["centroid"]
        nearby = [s for s in stores if haversine_m(cy, cx, s["lat"], s["lng"]) <= 50]
        foot_store_corr.append({
            "link_id": link["road_link_id"],
            "acost": _get_acost_allday(link),
            "store_count": len(nearby),
            "centroid": link["centroid"],
        })

    # 5-2: work-residence proximity – 사업장 밀집 vs 지하철/버스 접근성
    workplaces = salary_data["workplaces"]
    wp_density = []
    grid_size = 0.002
    grid: dict[str, dict] = {}
    for wp in workplaces:
        gx = round(wp["lng"] / grid_size) * grid_size
        gy = round(wp["lat"] / grid_size) * grid_size
        key = f"{gx:.4f}_{gy:.4f}"
        if key not in grid:
            grid[key] = {"lng": gx, "lat": gy, "employees": 0, "count": 0, "salary_sum": 0.0}
        grid[key]["employees"] += wp["employees"]
        grid[key]["count"] += 1
        grid[key]["salary_sum"] += wp["monthly_salary"] * wp["employees"]

    for cell in grid.values():
        avg_sal = cell["salary_sum"] / cell["employees"] if cell["employees"] > 0 else 0
        wp_density.append({
            "lng": round(cell["lng"], 5),
            "lat": round(cell["lat"], 5),
            "employees": cell["employees"],
            "workplace_count": cell["count"],
            "avg_salary": round(avg_sal),
        })
    wp_density.sort(key=lambda x: -x["employees"])

    # 5-3: krafton cluster vitality – 클러스터 내 vs 외 상가 시간대 패턴
    cluster_bounds = []
    for feat in krafton_geo["features"]:
        coords = feat["geometry"]["coordinates"]
        flat_coords = []
        for ring in coords:
            if isinstance(ring[0][0], list):
                for sub in ring:
                    flat_coords.extend(sub)
            else:
                flat_coords.extend(ring)
        lngs = [c[0] for c in flat_coords]
        lats = [c[1] for c in flat_coords]
        cluster_bounds.append({
            "min_lng": min(lngs), "max_lng": max(lngs),
            "min_lat": min(lats), "max_lat": max(lats),
        })

    def in_cluster(lng, lat):
        for b in cluster_bounds:
            if b["min_lng"] <= lng <= b["max_lng"] and b["min_lat"] <= lat <= b["max_lat"]:
                return True
        return False

    time_keys = ["아침", "점심", "오후", "저녁", "밤", "심야", "새벽"]
    inside = {k: 0 for k in time_keys}
    outside = {k: 0 for k in time_keys}
    inside_count = 0
    outside_count = 0
    for s in stores:
        target = inside if in_cluster(s["lng"], s["lat"]) else outside
        counter = "inside_count" if in_cluster(s["lng"], s["lat"]) else "outside_count"
        if counter == "inside_count":
            inside_count += 1
        else:
            outside_count += 1
        for k in time_keys:
            target[k] += s.get("times", {}).get(k, 0)

    cluster_vitality = {
        "inside": {
            "count": inside_count,
            "time_profile": inside,
        },
        "outside": {
            "count": outside_count,
            "time_profile": outside,
        },
    }

    return {
        "foot_store_correlation": foot_store_corr[:30],
        "workplace_density": wp_density[:20],
        "cluster_vitality": cluster_vitality,
    }
