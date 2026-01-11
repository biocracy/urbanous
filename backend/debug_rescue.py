import asyncio
from database import AsyncSessionLocal
from models import ScraperRule
from sqlalchemy import select
import json
import httpx
from urllib.parse import urlparse
from datetime import datetime
import scraper_engine

# Mock target article
ARTICLE_URL = "https://www.vremyan.ru/news/592894"

async def debug_rescue():
    print(f"DEBUG: Starting Rescue Simulation for {ARTICLE_URL}")
    
    # 1. Fetch Rules like generating_digest does
    async with AsyncSessionLocal() as db:
        stmt = select(ScraperRule)
        res = await db.execute(stmt)
        all_rules = res.scalars().all()
        
        rules_map = {}
        for r in all_rules:
            # Replicating outlets.py logic exactly
            # rules_map[r.domain] = json.loads(r.config_json)
            # outlets.py line 1422: rules_map[r.domain] = json.loads(r.config_json)
            try:
                rules_map[r.domain] = json.loads(r.config_json)
            except: pass
            
        print(f"DEBUG: Loaded {len(rules_map)} rules.")
        
        # 2. Derive Domain for Lookup
        domain = urlparse(ARTICLE_URL).netloc.replace("www.", "").lower()
        print(f"DEBUG: Derived Domain: '{domain}'")
        
        rule_config = rules_map.get(domain)
        print(f"DEBUG: Rule Config Found: {rule_config}")
        
        if not rule_config:
            print("ERROR: Rule not found in map!")
            return

        # 3. Instantiate Rule Object
        rule_obj = scraper_engine.ScraperRule(
            domain="custom",
            date_selectors=rule_config.get('date_selectors'),
            date_regex=rule_config.get('date_regex'),
            use_json_ld=rule_config.get('use_json_ld', True)
        )
        print(f"DEBUG: Rule Object Created: {rule_obj.date_selectors}")

        # 4. Fetch and Extract
        async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0"}, verify=False, timeout=10) as client:
            resp = await client.get(ARTICLE_URL)
            print(f"DEBUG: Fetch Status: {resp.status_code}")
            
            if resp.status_code == 200:
                # 5. Extract
                rescued_date = scraper_engine.extract_date_from_html(resp.text, ARTICLE_URL, custom_rule_override=rule_obj)
                print(f"DEBUG: Extracted Result: {rescued_date} (Type: {type(rescued_date)})")
                
                # 6. Validate Processing Logic
                d_obj = None
                if isinstance(rescued_date, datetime):
                    d_obj = rescued_date
                    rescued_date_str = d_obj.strftime("%Y-%m-%d")
                    print(f"DEBUG: Handled as Datetime -> {rescued_date_str}")
                elif rescued_date:
                    c_date = str(rescued_date).split("T")[0]
                    try:
                        d_obj = datetime.strptime(c_date, "%Y-%m-%d")
                        print(f"DEBUG: Handled as String -> {c_date}")
                    except ValueError as e:
                        print(f"DEBUG: String Parsing Failed: {e}")
                
if __name__ == "__main__":
    asyncio.run(debug_rescue())
