
import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Partial Logic from scraper_engine.extract_article_links (simulated)
async def test_extract_links(url):
    print(f"Fetching Homepage: {url}")
    try:
        async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0"}, verify=False, timeout=10, follow_redirects=True) as client:
            resp = await client.get(url)
            print(f"Status: {resp.status_code}")
            if resp.status_code != 200:
                print("Failed to fetch homepage.")
                return

            soup = BeautifulSoup(resp.text, "html.parser")
            links = soup.find_all("a", href=True)
            print(f"Total <a> tags found: {len(links)}")
            
            print(f"Total <a> tags found: {len(links)}")
            
            news_links = []
            for a in links:
                href = a.get('href', '')
                full_url = urljoin(url, href)
                # Broader check
                if 'news/' in full_url:
                    news_links.append(full_url)

            print(f"Total 'news/' links: {len(news_links)}")
            for l in news_links[:20]:
                print(f" -> {l}")

    except Exception as e:
        print(f"Exception: {e}")

async def main():
    await test_extract_links("https://www.vremyan.ru/news")

if __name__ == "__main__":
    asyncio.run(main())
