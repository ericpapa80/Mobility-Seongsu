#!/usr/bin/env python3
"""Load traffic_seongsu.json into PostGIS database."""

import json
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.database import engine, async_session
from app.db.models import Base

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "pipeline" / "silver" / "traffic_seongsu.json"


def _linestring_wkt(coordinates: list) -> str:
    """Convert [[lng, lat], ...] to WKT LINESTRING."""
    pts = ", ".join(f"{c[0]} {c[1]}" for c in coordinates)
    return f"LINESTRING({pts})"


async def load_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    use_date = data["meta"].get("date", "")

    async with async_session() as session:
        await session.execute(text("DELETE FROM traffic_segments WHERE use_date = :d"), {"d": use_date})
        await session.commit()

        inserted = 0
        for seg in data["segments"]:
            coords = seg.get("coordinates", [])
            geom_wkt = _linestring_wkt(coords) if len(coords) >= 2 else None

            await session.execute(text("""
                INSERT INTO traffic_segments
                    (link_id, road_name, direction, distance, lanes, road_type, area_type, geom, speeds, use_date)
                VALUES
                    (:link_id, :road_name, :direction, :distance, :lanes, :road_type, :area_type,
                     CASE WHEN :geom IS NOT NULL THEN ST_GeomFromText(:geom, 4326) ELSE NULL END,
                     :speeds, :use_date)
                ON CONFLICT (link_id) DO UPDATE SET
                    road_name = EXCLUDED.road_name,
                    direction = EXCLUDED.direction,
                    distance = EXCLUDED.distance,
                    lanes = EXCLUDED.lanes,
                    road_type = EXCLUDED.road_type,
                    area_type = EXCLUDED.area_type,
                    geom = EXCLUDED.geom,
                    speeds = EXCLUDED.speeds,
                    use_date = EXCLUDED.use_date
            """), {
                "link_id": seg["link_id"],
                "road_name": seg.get("road_name"),
                "direction": seg.get("direction"),
                "distance": seg.get("distance"),
                "lanes": seg.get("lanes"),
                "road_type": seg.get("road_type"),
                "area_type": seg.get("area_type"),
                "geom": geom_wkt,
                "speeds": seg.get("speeds", []),
                "use_date": use_date,
            })
            inserted += 1

        await session.commit()

    print(f"Loaded {inserted} traffic segments (use_date={use_date})")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(load_data())
