"""Seed the database with synthetic resources for benchmarking and demos."""

from __future__ import annotations

import asyncio
import random
import sys

from nxflow.db import dispose_engine, get_engine
from nxflow.models import Resource
from sqlalchemy import insert

TYPES = ["server", "rack", "switch", "pdu", "patch-panel"]
STATUSES = ["declared", "discovered", "active", "retired"]
TAGS = ["prod", "staging", "lab", "web", "db", "storage", "network"]


def build_rows(count: int) -> list[dict]:
    rng = random.Random(42)
    rows = []
    for index in range(count):
        resource_type = rng.choice(TYPES)
        rows.append(
            {
                "type": resource_type,
                "name": f"{resource_type}-{index:05d}",
                "status": rng.choice(STATUSES),
                "location": (
                    f"dc{rng.randint(1, 3)}/row{rng.randint(1, 12)}"
                    f"/rack{rng.randint(1, 40)}"
                ),
                "tags": rng.sample(TAGS, k=rng.randint(1, 3)),
                "attributes": {"cpu": rng.choice([8, 16, 32, 64]), "power": rng.randint(100, 1200)},
                "metadata_json": {"asset_id": f"A-{index:05d}", "warranty": "2027-01-01"},
                "origin": {"source": "seed", "ref": f"seed/{index}"},
            }
        )
    return rows


async def main(count: int) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(insert(Resource), build_rows(count))
    await dispose_engine()
    print(f"seeded {count} resources")


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000))
