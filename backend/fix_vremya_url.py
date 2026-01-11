
import asyncio
from sqlalchemy import select
from database import AsyncSessionLocal
from models import NewsOutlet

async def fix_url():
    async with AsyncSessionLocal() as db:
        # Find Vremya N
        stmt = select(NewsOutlet).where(NewsOutlet.url.like("%vremyan.ru%"))
        result = await db.execute(stmt)
        outlet = result.scalars().first()
        
        if outlet:
            print(f"Found Outlet: {outlet.name} | Current URL: {outlet.url}")
            # Update to /news
            # Note: We append /news if not present, but better to set exact known good URL
            new_url = "https://www.vremyan.ru/news"
            
            if outlet.url != new_url:
                outlet.url = new_url
                await db.commit()
                print(f"SUCCESS: Updated URL to: {outlet.url}")
            else:
                print("URL is already correct.")
        else:
            print("FAILURE: Outlet not found.")

if __name__ == "__main__":
    asyncio.run(fix_url())
