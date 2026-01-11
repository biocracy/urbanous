
import asyncio
import httpx
from bs4 import BeautifulSoup
import re

# Copy of the current logic from scraper_engine.py
def detect_content_type(html: str) -> str:
    if not html: return "unknown"
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Check Metadata
    og_type = soup.find("meta", property="og:type")
    print(f"DEBUG: og:type = {og_type}")
    if og_type and og_type.get("content"):
        c = og_type["content"].lower()
        if "article" in c: return "article"
        if "website" in c: pass
    
    # 2. Text vs Link Density
    paragraphs = soup.find_all("p")
    significant_paras = 0
    total_p_text_length = 0
    
    for p in paragraphs:
        text = p.get_text(strip=True)
        if len(text) > 60:
            significant_paras += 1
            total_p_text_length += len(text)
            
    print(f"DEBUG: Sig Paras: {significant_paras}, Total Len: {total_p_text_length}")

    if significant_paras < 2:
        return "category"
    if significant_paras >= 3 and total_p_text_length > 500:
        return "article"
    return "unknown"

async def test_url(url: str):
    print(f"\n--- Testing {url} ---")
    try:
        async with httpx.AsyncClient(verify=False, timeout=10, follow_redirects=True) as client:
            resp = await client.get(url)
            print(f"Status: {resp.status_code}, Len: {len(resp.text)}")
            decision = detect_content_type(resp.text[:20000])
            print(f"DECISION: {decision}")
    except Exception as e:
        print(f"Error: {e}")

async def main():
    urls = [
        "https://www.hbl.fi/politik",
        "https://www.kauppalehti.fi/tilaus",
        "https://www.lansivayla.fi/aihe/kruunujuttu",
        "https://arenan.yle.fi/tv/guide",
        "https://yle.fi/t/18-220306/fi"
    ]
    for u in urls:
        await test_url(u)

if __name__ == "__main__":
    asyncio.run(main())
