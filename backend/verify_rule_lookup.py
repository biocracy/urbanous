
import asyncio
import json
from sqlalchemy import select
from database import AsyncSessionLocal
from models import NewsOutlet, ScraperRule
from urllib.parse import urlparse

async def verify():
    async with AsyncSessionLocal() as db:
        # 1. Fetch Outlets
        print("Fetching Outlets...")
        stmt = select(NewsOutlet).where(NewsOutlet.url.like("%vremyan%"))
        res = await db.execute(stmt)
        outlets = res.scalars().all()
        print(f"Found {len(outlets)} outlets matching 'vremyan'.")
        
        # 2. Fetch Rules (Mimic outlets.py)
        print("Fetching Rules...")
        stmt_rules = select(ScraperRule)
        res_rules = await db.execute(stmt_rules)
        all_rules = res_rules.scalars().all()
        
        rules_map = {}
        for r in all_rules:
            try:
                # Normalize?
                rules_map[r.domain] = json.loads(r.config_json)
                # print(f"Loaded: {r.domain}")
            except Exception as e:
                print(f"Failed to load {r.domain}: {e}")

        print(f"Total Rules in Map: {len(rules_map)}")
        if 'vremyan.ru' in rules_map:
            print("vremyan.ru IS in rules_map.")
            print(f"Config: {rules_map['vremyan.ru']}")
        else:
            print("vremyan.ru IS NOT in rules_map.")

        # 3. Test Lookup
        for o in outlets:
            parsed = urlparse(o.url)
            domain = parsed.netloc.replace("www.", "").lower()
            if not domain: # Fallback if URL is bad
                 domain = o.url.replace("www.", "").split("/")[0].lower() # Primitive
                 
            print(f"Outlet: {o.name} | URL: {o.url} | Domain: {domain}")
            
            rule = rules_map.get(domain)
            if rule:
                print(f"  -> MATCH! Rule Found.")
            else:
                print(f"  -> NO MATCH.")
                # Try fallback logic
                parts = domain.split('.')
                if len(parts) > 2:
                    root = ".".join(parts[-2:])
                    if root in rules_map:
                        print(f"  -> Root Domain Match: {root}")

if __name__ == "__main__":
    asyncio.run(verify())
