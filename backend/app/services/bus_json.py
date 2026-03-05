"""Fallback service: serve bus data directly from JSON file when PostGIS is unavailable."""

import json
from pathlib import Path
from functools import lru_cache

DATA_FILE = Path(__file__).resolve().parent.parent.parent.parent / "pipeline" / "silver" / "bus_stops_hourly.json"


@lru_cache(maxsize=1)
def _load():
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    stops = []
    for idx, s in enumerate(data["stops"], start=1):
        stops.append({
            "id": idx,
            "ars_id": s["ars_id"],
            "node_id": s["node_id"],
            "name": s["name"],
            "lat": s["lat"],
            "lng": s["lng"],
            "routes": s.get("routes", []),
            "use_ym": data["meta"]["use_ym"],
            "total_ride": s.get("total_ride", 0),
            "total_alight": s.get("total_alight", 0),
            "total": s.get("total", 0),
            "hourly": s["hourly"],
        })
    return stops


def get_bus_stops():
    stops = _load()
    return {"stops": [{k: v for k, v in s.items() if k != "hourly"} for s in stops]}


def get_bus_stops_hourly(hour: int):
    stops = _load()
    result = []
    for s in stops:
        ride = s["hourly"]["ride"][hour] if hour < len(s["hourly"]["ride"]) else 0
        alight = s["hourly"]["alight"][hour] if hour < len(s["hourly"]["alight"]) else 0
        result.append({
            "id": s["id"],
            "ars_id": s["ars_id"],
            "node_id": s["node_id"],
            "name": s["name"],
            "lat": s["lat"],
            "lng": s["lng"],
            "routes": s["routes"],
            "total_ride": s["total_ride"],
            "total_alight": s["total_alight"],
            "total": s["total"],
            "ride": ride,
            "alight": alight,
        })
    return {"hour": hour, "stops": result}


def get_all_stops_hourly_full():
    """Return all stops with full 24-hour ride/alight arrays."""
    stops = _load()
    result = []
    for s in stops:
        result.append({
            "id": s["id"],
            "name": s["name"],
            "lat": s["lat"],
            "lng": s["lng"],
            "total_ride": s["total_ride"],
            "total_alight": s["total_alight"],
            "total": s["total"],
            "hourly": s["hourly"],
        })
    return {"stops": result}


def get_stop_hourly_all(stop_id: int):
    stops = _load()
    for s in stops:
        if s["id"] == stop_id:
            hourly = [
                {"hour": h, "ride": s["hourly"]["ride"][h], "alight": s["hourly"]["alight"][h]}
                for h in range(24)
            ]
            return {
                "id": s["id"],
                "ars_id": s["ars_id"],
                "node_id": s["node_id"],
                "name": s["name"],
                "lat": s["lat"],
                "lng": s["lng"],
                "routes": s["routes"],
                "hourly": hourly,
            }
    return {"error": "not found"}
