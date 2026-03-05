from fastapi import APIRouter, Query
from app.db.database import is_db_available, get_db
from app.services import bus_json

router = APIRouter(tags=["bus"])


@router.get("/bus-stops")
async def get_bus_stops():
    if not is_db_available():
        return bus_json.get_bus_stops()

    from sqlalchemy import select
    from app.db.models import BusStop

    async for db in get_db():
        result = await db.execute(
            select(
                BusStop.id, BusStop.ars_id, BusStop.node_id, BusStop.name,
                BusStop.lat, BusStop.lng,
                BusStop.routes, BusStop.use_ym,
                BusStop.total_ride, BusStop.total_alight, BusStop.total,
            )
        )
        return {"stops": [
            {
                "id": r.id, "ars_id": r.ars_id, "node_id": r.node_id,
                "name": r.name, "lat": float(r.lat), "lng": float(r.lng),
                "routes": r.routes or [], "use_ym": r.use_ym,
                "total_ride": r.total_ride, "total_alight": r.total_alight, "total": r.total,
            }
            for r in result.all()
        ]}


@router.get("/bus-stops/hourly")
async def get_bus_stops_hourly(hour: int = Query(default=8, ge=0, le=23)):
    if not is_db_available():
        return bus_json.get_bus_stops_hourly(hour)

    from sqlalchemy import select
    from app.db.models import BusStop, BusStopHourly

    async for db in get_db():
        result = await db.execute(
            select(
                BusStop.id, BusStop.ars_id, BusStop.node_id, BusStop.name,
                BusStop.lat, BusStop.lng,
                BusStop.routes, BusStop.total_ride, BusStop.total_alight, BusStop.total,
                BusStopHourly.ride, BusStopHourly.alight,
            )
            .join(BusStopHourly, BusStop.id == BusStopHourly.stop_id)
            .where(BusStopHourly.hour == hour)
        )
        return {"hour": hour, "stops": [
            {
                "id": r.id, "ars_id": r.ars_id, "node_id": r.node_id,
                "name": r.name, "lat": float(r.lat), "lng": float(r.lng),
                "routes": r.routes or [],
                "total_ride": r.total_ride, "total_alight": r.total_alight, "total": r.total,
                "ride": r.ride, "alight": r.alight,
            }
            for r in result.all()
        ]}


@router.get("/bus-stops/hourly-full")
async def get_all_stops_hourly_full():
    """All stops with full 24-hour ride/alight arrays for charts."""
    if not is_db_available():
        return bus_json.get_all_stops_hourly_full()

    from sqlalchemy import select
    from app.db.models import BusStop, BusStopHourly

    async for db in get_db():
        stop_result = await db.execute(
            select(
                BusStop.id, BusStop.name,
                BusStop.lat, BusStop.lng,
                BusStop.total_ride, BusStop.total_alight, BusStop.total,
            )
        )
        stops = stop_result.all()

        hourly_result = await db.execute(
            select(BusStopHourly.stop_id, BusStopHourly.hour,
                   BusStopHourly.ride, BusStopHourly.alight)
            .order_by(BusStopHourly.stop_id, BusStopHourly.hour)
        )
        hourly_map: dict[int, dict] = {}
        for r in hourly_result.all():
            if r.stop_id not in hourly_map:
                hourly_map[r.stop_id] = {"ride": [0]*24, "alight": [0]*24}
            hourly_map[r.stop_id]["ride"][r.hour] = r.ride
            hourly_map[r.stop_id]["alight"][r.hour] = r.alight

        return {"stops": [
            {
                "id": s.id, "name": s.name,
                "lat": float(s.lat), "lng": float(s.lng),
                "total_ride": s.total_ride, "total_alight": s.total_alight,
                "total": s.total,
                "hourly": hourly_map.get(s.id, {"ride": [0]*24, "alight": [0]*24}),
            }
            for s in stops
        ]}


@router.get("/bus-stops/{stop_id}/hourly-all")
async def get_stop_hourly_all(stop_id: int):
    if not is_db_available():
        return bus_json.get_stop_hourly_all(stop_id)

    from sqlalchemy import select
    from app.db.models import BusStop, BusStopHourly

    async for db in get_db():
        stop_result = await db.execute(
            select(
                BusStop.id, BusStop.ars_id, BusStop.node_id, BusStop.name,
                BusStop.lat, BusStop.lng,
                BusStop.routes,
            ).where(BusStop.id == stop_id)
        )
        stop = stop_result.first()
        if not stop:
            return {"error": "not found"}

        hourly_result = await db.execute(
            select(BusStopHourly.hour, BusStopHourly.ride, BusStopHourly.alight)
            .where(BusStopHourly.stop_id == stop_id)
            .order_by(BusStopHourly.hour)
        )
        return {
            "id": stop.id, "ars_id": stop.ars_id, "node_id": stop.node_id,
            "name": stop.name, "lat": float(stop.lat), "lng": float(stop.lng),
            "routes": stop.routes or [],
            "hourly": [{"hour": r.hour, "ride": r.ride, "alight": r.alight} for r in hourly_result.all()],
        }
