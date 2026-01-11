import asyncio
import httpx
from bs4 import BeautifulSoup

# Copy of the function from scraper_engine.py
def detect_content_type(html: str) -> str:
    """
    Analyzes HTML to determine if it's an Article or a Category/Landing page.
    Returns: 'article', 'category', or 'unknown'
    """
    if not html: return "unknown"
    soup = BeautifulSoup(html, 'html.parser')
    
    # 2. Link Density Heuristic
    all_text = soup.get_text(strip=True)
    if len(all_text) < 100: return "unknown"
    
    links = soup.find_all("a")
    link_text_len = sum(len(a.get_text(strip=True)) for a in links)
    
    link_density = link_text_len / len(all_text)
    print(f"  [Stats] Link Density: {link_density:.2f} ({link_text_len}/{len(all_text)})")

    # 3. Decision Logic
    # Strict Keywords in Title
    title = soup.title.string.lower() if soup.title else ""
    noise_keywords = ["donate", "support", "pidtrymka", "contact", "region", "rubric", "category"]
    if any(k in title for k in noise_keywords):
        print("  [Reject] Title keyword match")
        return "category"
    
    if link_density > 0.45: # Aggressive threshold
        return "category"

    paragraphs = soup.find_all("p")
    significant_paras = 0
    total_p_text_length = 0
    
    for p in paragraphs:
        text = p.get_text(strip=True)
        if len(text) > 60: 
            significant_paras += 1
            total_p_text_length += len(text)
            
    print(f"  [Stats] Sig Paras: {significant_paras}, Total Text: {total_p_text_length}")
    
    if significant_paras < 2:
        return "category"
        
    if significant_paras >= 3 and total_p_text_length > 500:
        return "article"
        
    return "unknown" 

async def test_urls():
    urls = [
        "https://lug-info.com/eksklyuziv/",
        "https://www.unian.ua/theme/110-otstuplenie-iz-debalcevo",
        "https://www.rbc.ua/ukr/moda",
        "https://www.rbc.ua/ukr/allnews",
        "https://linklist.bio/zvlni8nzww",
        "https://tsn.ua/ukrayina",
        "https://tsn.ua/rules"
    ]
    
    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as client:
        for url in urls:
            print(f"\nTesting: {url}")
            try:
                resp = await client.get(url)
                print(f"  Status: {resp.status_code}")
                if resp.status_code != 200:
                    print("  -> Fetch Failed!")
                    continue
                    
                ct = detect_content_type(resp.text)
                print(f"  Result: {ct}")
            except Exception as e:
                print(f"  Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_urls())
