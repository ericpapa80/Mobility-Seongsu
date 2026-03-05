#!/usr/bin/env python3
"""Run all Silver→PostGIS loading scripts in sequence."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import load_bus_stops
import load_subway
import load_traffic
import load_stores
import load_salary
import load_foottraffic


async def main():
    loaders = [
        ("bus_stops",     load_bus_stops.load_data),
        ("subway",        load_subway.load_data),
        ("traffic",       load_traffic.load_data),
        ("stores",        load_stores.load_data),
        ("salary",        load_salary.load_data),
        ("foottraffic",   load_foottraffic.load_data),
    ]

    for name, fn in loaders:
        print(f"\n{'='*50}")
        print(f"Loading: {name}")
        print(f"{'='*50}")
        try:
            await fn()
        except Exception as exc:
            print(f"ERROR loading {name}: {exc}", file=sys.stderr)
            raise

    print("\n✅ All datasets loaded successfully.")


if __name__ == "__main__":
    asyncio.run(main())
