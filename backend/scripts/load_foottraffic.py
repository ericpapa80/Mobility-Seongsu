#!/usr/bin/env python3
"""Load foottraffic_seongsu.json into database."""

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
                centroid_lng = centroid[0] if centroid and len(centroid) >= 2 else None
                centroid_lat = centroid[1] if centroid and len(centroid) >= 2 else None

                await session.execute(text("""
                    INSERT INTO foottraffic_links (road_link_id, coordinates, centroid_lng, centroid_lat, data)
                    VALUES (:road_link_id, :coordinates::jsonb, :centroid_lng, :centroid_lat, :data::jsonb)
                    ON CONFLICT (road_link_id) DO NOTHING
                """), {
                    "road_link_id": lk["road_link_id"],
                    "coordinates": json.dumps(coords),
                    "centroid_lng": centroid_lng,
                    "centroid_lat": centroid_lat,
                    "data": json.dumps(lk.get("data") or {}, ensure_ascii=False),
                })
            await session.commit()
            print(f"  Inserted batch {i // BATCH_SIZE + 1} ({min(i + BATCH_SIZE, len(links))}/{len(links)})")

    print(f"Loaded {len(links)} foottraffic links")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(load_data())
