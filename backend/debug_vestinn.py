
import asyncio
import httpx
from bs4 import BeautifulSoup

async def test_vestinn():
    url = "https://vestinn.ru/news/society/255439/"
    print(f"Fetching {url}...")
    
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    async with httpx.AsyncClient(headers=headers, verify=False, follow_redirects=True) as client:
        resp = await client.get(url)
        print(f"Status: {resp.status_code}")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Test 1: H1
        h1 = soup.find("h1")
        if h1:
            print(f"H1 Found: '{h1.get_text(strip=True)}'")
        else:
            print("H1 NOT Found.")
            
        # Test 2: Title Tag
        if soup.title:
            print(f"Title Tag: '{soup.title.get_text(strip=True)}'")
        else:
            print("Title Tag NOT Found.")
            
        # Test 3: Og:Title
        og_title = soup.find("meta", property="og:title")
        if og_title:
             print(f"OG:Title: '{og_title.get('content')}'")
        else:
             print("OG:Title NOT Found.")

if __name__ == "__main__":
    asyncio.run(test_vestinn())
