#!/usr/bin/env python3
"""Load salary_seongsu.json into database."""

import json
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.database import engine, async_session
from app.db.models import Base

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "pipeline" / "silver" / "salary_seongsu.json"

BATCH_SIZE = 500


async def load_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    workplaces = data["workplaces"]

    async with async_session() as session:
        await session.execute(text("DELETE FROM salary_workplaces"))
        await session.commit()

        for i in range(0, len(workplaces), BATCH_SIZE):
            batch = workplaces[i:i + BATCH_SIZE]
            for wp in batch:
                await session.execute(text("""
                    INSERT INTO salary_workplaces (name, industry, employees, monthly_salary, lng, lat)
                    VALUES (:name, :industry, :employees, :monthly_salary, :lng, :lat)
                """), {
                    "name": wp.get("name"),
                    "industry": wp.get("industry"),
                    "employees": wp.get("employees", 0),
                    "monthly_salary": wp.get("monthly_salary", 0),
                    "lng": wp.get("lng"),
                    "lat": wp.get("lat"),
                })
            await session.commit()
            print(f"  Inserted batch {i // BATCH_SIZE + 1} ({min(i + BATCH_SIZE, len(workplaces))}/{len(workplaces)})")

    print(f"Loaded {len(workplaces)} salary workplaces")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(load_data())
