
import asyncio
import httpx
from bs4 import BeautifulSoup
import urllib.parse
import scraper_engine

async def test_homepage():
    target_url = "https://vestinn.ru"
    print(f"Fetching Homepage: {target_url}...")
    
    headers = {"User-Agent": "Mozilla/5.0"}
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=10.0, verify=False) as client:
        resp = await client.get(target_url, headers=headers)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code != 200:
            print("Failed to fetch.")
            return

        soup = BeautifulSoup(resp.text, 'html.parser')
        links = soup.find_all('a', href=True)
        print(f"Total raw links: {len(links)}")
        
        valid_count = 0
        for a in links:
            href = a['href']
            # Normalize
            if not href.startswith('http'):
                full_url = urllib.parse.urljoin(target_url, href)
            else:
                full_url = href
            
            # Simple Filter Check
            if scraper_engine.is_valid_article_url(full_url):
                valid_count += 1
                if valid_count <= 5:
                    print(f"  Valid Link: {full_url}")
        
        print(f"Total Valid Article Links: {valid_count}")

if __name__ == "__main__":
    asyncio.run(test_homepage())
