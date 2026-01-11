import asyncio
from database import AsyncSessionLocal
from models import ScraperRule
from sqlalchemy import select

async def dump_rules():
    async with AsyncSessionLocal() as db:
        stmt = select(ScraperRule)
        res = await db.execute(stmt)
        rules = res.scalars().all()
        print(f"Total Rules: {len(rules)}")
        for r in rules:
            print(f"Domain: '{r.domain}'")

if __name__ == "__main__":
    asyncio.run(dump_rules())
