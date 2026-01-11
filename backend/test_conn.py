import httpx
import asyncio
import sys
import os

# Add path to find scraper_engine
sys.path.append(os.getcwd())
import scraper_engine
from scraper_engine import ScraperRule

async def test():
    url = "https://www.blackseanews.net/read/239436"
    print(f"Testing full pipeline for {url}...")
    
    html = ""
    try:
        async with httpx.AsyncClient(follow_redirects=True, verify=False, timeout=10.0) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            print(f"Fetch Status: {resp.status_code}")
            html = resp.text
    except Exception as e:
        print(f"Fetch Error: {e}")
        return

    print("Parsing...")
    # Simulate the rule
    rule = ScraperRule(
        domain="blackseanews.net",
        date_selectors=[".news-info__date .date"],  # User provided
        date_regex=[r"(\d{2}\.\d{2}\.\d{4})"],      # I added this to registry
        use_json_ld=True
    )
    
    try:
        date = scraper_engine.extract_date_from_html(html, url, custom_rule_override=rule)
        print(f"Extracted Date: {date}")
    except Exception as e:
        print(f"Parse Error: {e}")

asyncio.run(test())
