
import asyncio
import httpx
from bs4 import BeautifulSoup
import scraper_engine

async def debug_crash():
    url = "https://www.paris.fr/recherche/infos"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient(follow_redirects=True, verify=False) as client:
        print(f"Fetching {url}...")
        resp = await client.get(url, headers=headers)
        print(f"Status: {resp.status_code}")
        
        try:
            print("Attempting extract_date_from_html...")
            # Simulate what scraper.py does
            date = scraper_engine.extract_date_from_html(resp.text, url)
            print(f"Extracted Date: {date}")
            
            print("Attempting extract_title_from_html...")
            title = scraper_engine.extract_title_from_html(resp.text, url)
            print(f"Extracted Title: {title}")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"CRASHED: {e}")

if __name__ == "__main__":
    asyncio.run(debug_crash())
