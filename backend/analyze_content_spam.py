
import asyncio
import httpx
from bs4 import BeautifulSoup
import sys
import os

# Ambiguous URLs from the user's report that we want to double-check
URLS_TO_ANALYZE = [
    "https://www.mprnews.org/ice-in-minnesota", # Short Path
    "https://www.mprnews.org/fraud-in-minnesota", # Short Path
    "https://www.mprnews.org/shows/minnesotanow", # Shows
    "https://www.twincities.com/2026/01/12/inver-grove-heights-teacher-at-special-education-school-held-by-ice-for-nearly-12-hours/", # Previous false positive
    "https://mspmag.com/arts-and-culture", # Short Path Category
    "https://racketmn.com/wall-of-fame" # Short Path
]

async def analyze_url(client, url):
    try:
        resp = await client.get(url, timeout=10, follow_redirects=True)
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Check Metadata (og:type)
        og_type = "unknown"
        meta_type = soup.find("meta", property="og:type")
        if meta_type:
            og_type = meta_type.get("content", "unknown")
            
        # 2. Check Link Density (Text vs Links)
        # High density = Category/Index page
        text = soup.get_text(" ", strip=True)
        text_len = len(text)
        links = soup.find_all("a")
        link_text_len = sum(len(a.get_text(strip=True)) for a in links)
        
        density = 0
        if text_len > 0:
            density = link_text_len / text_len
            
        # 3. Check Paragraphs (count > 3 reliable paras)
        paras = soup.find_all("p")
        good_paras = [p for p in paras if len(p.get_text(strip=True)) > 80]
        
        print(f"URL: {url}")
        print(f"  Result: {'[ARTICLE]' if og_type == 'article' else '[NOT ARTICLE]'}")
        print(f"  og:type: {og_type}")
        print(f"  Link Density: {density:.2f} (Index > 0.45)")
        print(f"  Significant Paragraphs: {len(good_paras)}")
        print("-" * 40)
            
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")

async def main():
    headers = {"User-Agent": "Urbanous/1.0"}
    async with httpx.AsyncClient(headers=headers, verify=False) as client:
        # Serial for simplicity/debug clarity
        for u in URLS_TO_ANALYZE:
            await analyze_url(client, u)

if __name__ == "__main__":
    asyncio.run(main())
