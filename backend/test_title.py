import httpx
import asyncio
from bs4 import BeautifulSoup

async def get_title():
    url = "https://www.vremyan.ru/news/592974"
    print(f"Fetching {url}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(follow_redirects=True, verify=False) as client:
        resp = await client.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Try h1
        h1 = soup.find('h1')
        title_tag = soup.find('title')
        
        print(f"H1: {h1.get_text(strip=True) if h1 else 'None'}")
        print(f"Title Tag: {title_tag.get_text(strip=True) if title_tag else 'None'}")

if __name__ == "__main__":
    asyncio.run(get_title())
