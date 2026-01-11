import asyncio
from database import AsyncSessionLocal
from routers.outlets import get_all_outlets, list_cities_with_outlets
from sqlalchemy import select, distinct
from models import NewsOutlet

async def verify():
    async with AsyncSessionLocal() as db:
        # 1. Check Raw Count
        stmt = select(NewsOutlet)
        res = await db.execute(stmt)
        all_outlets = res.scalars().all()
        print(f"Total Outlets in DB: {len(all_outlets)}")
        
        # 2. Check Cities
        stmt_cities = select(distinct(NewsOutlet.city))
        res_cities = await db.execute(stmt_cities)
        cities = res_cities.scalars().all()
        print(f"Distinct Cities in DB: {len(cities)}")
        print(f"Cities List: {cities}")
        
        # 3. Simulate get_all_outlets serialization
        serialized = [{"id": o.id, "name": o.name, "city": o.city, "country": o.country_code, "url": o.url} for o in all_outlets]
        print(f"Serialized Outlets: {len(serialized)}")
        if len(serialized) > 0:
            print(f"Sample: {serialized[0]}")

if __name__ == "__main__":
    asyncio.run(verify())
