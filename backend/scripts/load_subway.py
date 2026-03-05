#!/usr/bin/env python3
"""Load subway_stations_hourly.json into PostGIS database."""

import json
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.database import engine, async_session
from app.db.models import Base

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "pipeline" / "silver" / "subway_stations_hourly.json"


async def load_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    use_date = data["meta"].get("date", "")

    async with async_session() as session:
        await session.execute(text(
            "DELETE FROM subway_station_hourly WHERE station_id IN "
            "(SELECT id FROM subway_stations WHERE use_date = :d)"
        ), {"d": use_date})
        await session.execute(text("DELETE FROM subway_stations WHERE use_date = :d"), {"d": use_date})
        await session.commit()

        for sta in data["stations"]:
            result = await session.execute(text("""
                INSERT INTO subway_stations (name, geom, sub_sta_sn, use_date)
                VALUES (:name, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), :sub_sta_sn, :use_date)
                RETURNING id
            """), {
                "name": sta["name"],
                "lng": sta["lng"],
                "lat": sta["lat"],
                "sub_sta_sn": sta.get("sub_sta_sn"),
                "use_date": use_date,
            })
            station_id = result.scalar_one()

            ridership = sta.get("ridership", {})
            rides = ridership.get("ride", [0] * 24)
            alights = ridership.get("alight", [0] * 24)

            for hour in range(24):
                ride = rides[hour] if hour < len(rides) else 0
                alight = alights[hour] if hour < len(alights) else 0
                await session.execute(text("""
                    INSERT INTO subway_station_hourly (station_id, hour, ride, alight)
                    VALUES (:station_id, :hour, :ride, :alight)
                """), {"station_id": station_id, "hour": hour, "ride": ride, "alight": alight})

        await session.commit()

    print(f"Loaded {len(data['stations'])} subway stations with hourly data (use_date={use_date})")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(load_data())
