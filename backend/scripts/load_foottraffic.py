#!/usr/bin/env python3
"""Load foottraffic_seongsu.json into PostGIS database."""

import json
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.database import engine, async_session
from app.db.models import Base

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "pipeline" / "silver" / "foottraffic_seongsu.json"

BATCH_SIZE = 200


def _linestring_wkt(coordinates: list) -> str | None:
    if not coordinates or len(coordinates) < 2:
        return None
    pts = ", ".join(f"{c[0]} {c[1]}" for c in coordinates)
    return f"LINESTRING({pts})"


def _point_wkt(centroid: list) -> str | None:
    if not centroid or len(centroid) < 2:
        return None
    return f"POINT({centroid[0]} {centroid[1]})"


async def load_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    links = data["links"]

    async with async_session() as session:
        await session.execute(text("DELETE FROM foottraffic_links"))
        await session.commit()

        for i in range(0, len(links), BATCH_SIZE):
            batch = links[i:i + BATCH_SIZE]
            for lk in batch:
                coords = lk.get("coordinates", [])
                centroid = lk.get("centroid")
                geom_wkt = _linestring_wkt(coords)
                centroid_wkt = _point_wkt(centroid)

                await session.execute(text("""
                    INSERT INTO foottraffic_links (road_link_id, geom, centroid, data)
                    VALUES (
                        :road_link_id,
                        CASE WHEN :geom IS NOT NULL THEN ST_GeomFromText(:geom, 4326) ELSE NULL END,
                        CASE WHEN :centroid IS NOT NULL THEN ST_GeomFromText(:centroid, 4326) ELSE NULL END,
                        :data::jsonb
                    )
                    ON CONFLICT (road_link_id) DO NOTHING
                """), {
                    "road_link_id": lk["road_link_id"],
                    "geom": geom_wkt,
                    "centroid": centroid_wkt,
                    "data": json.dumps(lk.get("data") or {}, ensure_ascii=False),
                })
            await session.commit()
            print(f"  Inserted batch {i // BATCH_SIZE + 1} ({min(i + BATCH_SIZE, len(links))}/{len(links)})")

    print(f"Loaded {len(links)} foottraffic links")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(load_data())
