#!/usr/bin/env python3
"""Load bus_stops_hourly.json into database."""

import json
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.database import engine, async_session
from app.db.models import Base

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "pipeline" / "silver" / "bus_stops_hourly.json"


async def load_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    use_ym = data["meta"]["use_ym"]

    async with async_session() as session:
        await session.execute(text(
            "DELETE FROM bus_stop_hourly WHERE stop_id IN "
            "(SELECT id FROM bus_stops WHERE use_ym = :ym)"
        ), {"ym": use_ym})
        await session.execute(text("DELETE FROM bus_stops WHERE use_ym = :ym"), {"ym": use_ym})
        await session.commit()

        for stop in data["stops"]:
            result = await session.execute(text("""
                INSERT INTO bus_stops (ars_id, node_id, name, lng, lat, routes, use_ym, total_ride, total_alight, total)
                VALUES (:ars_id, :node_id, :name, :lng, :lat, :routes, :use_ym, :total_ride, :total_alight, :total)
                RETURNING id
            """), {
                "ars_id": stop["ars_id"],
                "node_id": stop["node_id"],
                "name": stop["name"],
                "lng": stop["lng"],
                "lat": stop["lat"],
                "routes": stop.get("routes", []),
                "use_ym": use_ym,
                "total_ride": stop.get("total_ride", 0),
                "total_alight": stop.get("total_alight", 0),
                "total": stop.get("total", 0),
            })
            stop_id = result.scalar_one()

            for hour in range(24):
                ride = stop["hourly"]["ride"][hour] if hour < len(stop["hourly"]["ride"]) else 0
                alight = stop["hourly"]["alight"][hour] if hour < len(stop["hourly"]["alight"]) else 0
                await session.execute(text("""
                    INSERT INTO bus_stop_hourly (stop_id, hour, ride, alight)
                    VALUES (:stop_id, :hour, :ride, :alight)
                """), {
                    "stop_id": stop_id,
                    "hour": hour,
                    "ride": ride,
                    "alight": alight,
                })

        await session.commit()

    print(f"Loaded {len(data['stops'])} stops with hourly data (use_ym={use_ym})")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(load_data())
