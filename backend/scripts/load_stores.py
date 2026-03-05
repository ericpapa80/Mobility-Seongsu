#!/usr/bin/env python3
"""Load stores_seongsu.json into PostGIS database."""

import json
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.database import engine, async_session
from app.db.models import Base

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "pipeline" / "silver" / "stores_seongsu.json"

BATCH_SIZE = 500


async def load_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    stores = data["stores"]

    async with async_session() as session:
        await session.execute(text("DELETE FROM stores"))
        await session.commit()

        for i in range(0, len(stores), BATCH_SIZE):
            batch = stores[i:i + BATCH_SIZE]
            for s in batch:
                lng = s.get("lng")
                lat = s.get("lat")
                await session.execute(text("""
                    INSERT INTO stores
                        (store_id, name, road_address, category_bg, category_mi, category_sl,
                         geom, peco_total, peco_individual, peco_corporate, peco_foreign,
                         times, weekday, gender_f, gender_m)
                    VALUES
                        (:store_id, :name, :road_address, :category_bg, :category_mi, :category_sl,
                         CASE WHEN :lng IS NOT NULL THEN ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) ELSE NULL END,
                         :peco_total, :peco_individual, :peco_corporate, :peco_foreign,
                         :times::jsonb, :weekday::jsonb, :gender_f::jsonb, :gender_m::jsonb)
                    ON CONFLICT (store_id) DO NOTHING
                """), {
                    "store_id": s["store_id"],
                    "name": s["name"],
                    "road_address": s.get("road_address"),
                    "category_bg": s.get("category_bg"),
                    "category_mi": s.get("category_mi"),
                    "category_sl": s.get("category_sl"),
                    "lng": lng,
                    "lat": lat,
                    "peco_total": s.get("peco_total", 0),
                    "peco_individual": s.get("peco_individual", 0),
                    "peco_corporate": s.get("peco_corporate", 0),
                    "peco_foreign": s.get("peco_foreign", 0),
                    "times": json.dumps(s.get("times") or {}, ensure_ascii=False),
                    "weekday": json.dumps(s.get("weekday") or {}, ensure_ascii=False),
                    "gender_f": json.dumps(s.get("gender_f") or {}, ensure_ascii=False),
                    "gender_m": json.dumps(s.get("gender_m") or {}, ensure_ascii=False),
                })
            await session.commit()
            print(f"  Inserted batch {i // BATCH_SIZE + 1} ({min(i + BATCH_SIZE, len(stores))}/{len(stores)})")

    print(f"Loaded {len(stores)} stores")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(load_data())
