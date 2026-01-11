
import asyncio
import httpx
from bs4 import BeautifulSoup

async def test_progorod():
    # URL that fails for the user (numeric title, missing date)
    url = "https://progorodnn.ru/news/144063"
    print(f"Fetching {url}...")
    
    # Exact setup from outlets.py
    headers = {"User-Agent": "Mozilla/5.0"}
    
    async with httpx.AsyncClient(headers=headers, verify=False, timeout=15, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            print(f"Status: {resp.status_code}")
            print(f"URL after redirect: {str(resp.url)}")
            
            if resp.status_code == 200:
                 # Check Date Extraction
                 # ProGorod date selector?
                 # Need to peek at HTML
                 soup = BeautifulSoup(resp.text, 'html.parser')
                 title = soup.title.get_text(strip=True) if soup.title else "No Title"
                 h1 = soup.find("h1")
                 h1_text = h1.get_text(strip=True) if h1 else "No H1"
                 
                 print(f"Title Tag: {title}")
                 print(f"H1: {h1_text}")
                 
                 # Check if date is easily found
                 time = soup.find("time")
                 if time:
                      print(f"Time Tag: {time}")
                 else:
                      print("No <time> tag found.")
                 
                 # Check og:title
                 og = soup.find("meta", property="og:title")
                 if og:
                     print(f"OG:Title: {og.get('content')}")

                 # Test Scraper Engine Extraction (Simulate smart_scrape_outlet logic)
                 import scraper_engine
                 # Create a dummy rule like in outlets.py
                 rule = scraper_engine.ScraperRule(domain="progorodnn.ru", use_json_ld=True)
                 date_str = scraper_engine.extract_date_from_html(resp.text, url, custom_rule_override=rule)
                 print(f"Scraper Engine Date: {date_str}")
            else:
                 print(f"Failed with status {resp.status_code}")
                 
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_progorod())
