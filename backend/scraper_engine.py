
import re
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from pydantic import BaseModel
import google.generativeai as genai

# --- Configuration Models ---

class ScraperRule(BaseModel):
    domain: str
    date_selectors: Optional[List[str]] = None      # CSS Selectors e.g. ["span.post-date", "time.pub"]
    date_regex: Optional[List[str]] = None          # Specific Regexes to run on full text or specific elements
    title_selectors: Optional[List[str]] = None     # CSS Selectors for Title (e.g. h1.entry-title)
    use_json_ld: bool = True                        # Check Schema.org JSON-LD
    use_data_layer: bool = False                    # Check for window.dataLayer variables (common in news)
    data_layer_var: Optional[str] = None            # Specific JS variable name (default "dataLayer")
    date_format_hint: Optional[str] = None          # Hint for strptime if format is known

# --- The Registry ---
# Map domain (no www) to rules
SCRAPER_REGISTRY: Dict[str, ScraperRule] = {
    "stirileprotv.ro": ScraperRule(
        domain="stirileprotv.ro",
        use_data_layer=True,
        # fallback if JS fails
        date_selectors=["p.article-publication-date", ".article-info .date"] 
    ),
    "observatornews.ro": ScraperRule(
        domain="observatornews.ro",
        date_selectors=["span.post-date", ".post-date"],
        date_regex=[r"la\s+(\d{1,2}\.\d{2}\.\d{4})"]
    ),
    "digi24.ro": ScraperRule(
        domain="digi24.ro",
        date_selectors=["time", ".data-publicarii"],
        use_json_ld=True
    ),
    "g4media.ro": ScraperRule(
        domain="g4media.ro",
        date_selectors=["time", ".entry-date"],
        use_json_ld=True
    ),
    "tribuna.ro": ScraperRule(
        domain="tribuna.ro",
        date_selectors=["time.entry-date", ".posted-on time", ".post-date"],
        use_json_ld=True # WP site, likely has it
    ),
    "blackseanews.net": ScraperRule(
        domain="blackseanews.net",
        date_selectors=[".news-info__date .date", ".news-info .date", "span.date"],
        date_regex=[r"(\d{2}\.\d{2}\.\d{4})"]
    ),
    "qianlong.com": ScraperRule(
        domain="qianlong.com",
        date_selectors=[".s_laiz_box1 .row span", ".s_laiz span", ".content .date"],
        date_regex=[r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})"]
    ),
}

# --- Helper Functions ---

def parse_romanian_date(date_str: str) -> Optional[datetime]:
    """
    Parses dates like '29 decembrie 2025', 'ian. 04, 2026', 'la 06.01.2026'.
    """
    if not date_str: return None
    
    # Map RO months
    ro_months = {
        "ianuarie": 1, "ian": 1,
        "februarie": 2, "feb": 2,
        "martie": 3, "mar": 3,
        "aprilie": 4, "apr": 4,
        "mai": 5,
        "iunie": 6, "iun": 6,
        "iulie": 7, "iul": 7,
        "august": 8, "aug": 8,
        "septembrie": 9, "sept": 9,
        "octombrie": 10, "oct": 10,
        "noiembrie": 11, "nov": 11,
        "decembrie": 12, "dec": 12,
        # Russian
        "января": 1, "январь": 1, "февраля": 2, "февраль": 2, "марта": 3, "март": 3,
        "апреля": 4, "апрель": 4, "мая": 5, "май": 5, "июня": 6, "июнь": 6,
        "июля": 7, "июль": 7, "августа": 8, "август": 8, "сентября": 9, "сентябрь": 9,
        "октября": 10, "октябрь": 10, "ноября": 11, "ноябрь": 11, "декабря": 12, "декабрь": 12,
        # English fallbacks just in case
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }
    
    clean_text = date_str.lower().replace("la ", "").replace("din ", "").strip()
    
    # 1. Try ISO-like YYYY-MM-DD
    match_iso = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', clean_text)
    if match_iso:
         try: return datetime(int(match_iso.group(1)), int(match_iso.group(2)), int(match_iso.group(3)))
         except: pass

    # 2. Try DD.MM.YYYY or DD/MM/YYYY or DD-MM-YYYY
    match_dots = re.search(r'(\d{1,2})[./-](\d{1,2})[./-](\d{4})', clean_text)
    if match_dots:
         try: return datetime(int(match_dots.group(3)), int(match_dots.group(2)), int(match_dots.group(1)))
         except: pass
         
    # 3. Try "DD Month YYYY" (e.g. 29 Ianuarie 2025, 30 декабря 2025)
    # Supports Latin and Cyrillic
    match = re.search(r'(\d{1,2})\s+([a-zа-яăâîșț]+)\s+(\d{4})', clean_text)
    if match:
        day, month_name, year = match.groups()
        month = ro_months.get(month_name[:3]) 
        # For Russian, 3 chars might not be unique/enough? 
        # "дек" (dec), "янв" (jan) - seemingly ok.
        # But ro_months has full names mapped.
        # Let's try full name first.
        month = ro_months.get(month_name) or ro_months.get(month_name[:3])
        if month:
            try: return datetime(int(year), month, int(day))
            except: pass

    # 4. Try "Month. DD, YYYY" (e.g. Ian. 04, 2026)
    match_en_style = re.search(r'([a-zа-яăâîșț]{3,})\.?\s+(\d{1,2})[,\.]?\s+(\d{4})', clean_text)
    if match_en_style:
        month_name, day, year = match_en_style.groups()
        month = ro_months.get(month_name.lower()) or ro_months.get(month_name.lower()[:3])
        if month:
            try: return datetime(int(year), month, int(day))
            except: pass
            
    return None

def extract_date_from_url(url: str) -> Optional[datetime]:
    """
    Extracts date from URL slugs like /2025/12/29/ or /2025-12-29/.
    """
    if not url: return None
    
    # Pattern 1: /YYYY/MM/DD/
    match_slug = re.search(r'/(\d{4})/(\d{1,2})/(\d{1,2})/', url)
    if match_slug:
        y, m, d = match_slug.groups()
        try: return datetime(int(y), int(m), int(d))
        except: pass

    # Pattern 2: YYYY-MM-DD
    match_iso = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', url)
    if match_iso:
         y, m, d = match_iso.groups()
         if 2000 < int(y) < 2030:
             try: return datetime(int(y), int(m), int(d))
             except: pass
             
    return None

# --- Main Extraction Logic ---

def extract_from_js_datalayer(html: str, var_name: str = "dataLayer") -> Optional[datetime]:
    print(f"DEBUG: Checking dataLayer var '{var_name}'...")
    """
    Attempts to parse JSON objects assigned to window.dataLayer or similar arrays in script tags.
    Looks for 'articleDatePublished', 'datePublished', 'pubDate'.
    """
    # Regex to find: dataLayer = [{ ... }]; or dataLayer.push({...})
    # This is a heuristic.
    
    # 1. Look for explicit patterns like 'articleDatePublished': "..."
    # common in ProTV dataLayer
    # "articleDatePublished":"2026-01-05T14:04:00+02:00"
    match = re.search(r'[\'"]articleDatePublished[\'"]\s*:\s*[\'"]([^\'"]+)[\'"]', html)
    if match:
        dt_str = match.group(1)
        # Parse ISO
        # Handle +02:00
        try:
             # Truncate to YYYY-MM-DD
             return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except: 
             # Manual split
             if 'T' in dt_str:
                 return parse_romanian_date(dt_str.split('T')[0])

    return None

def extract_date_from_html(html: str, url: str, custom_rule_override: Optional[ScraperRule] = None) -> Optional[str]:
    """
    Orchestrator for extracting date from HTML content using Registry Rules followed by Global Fallback.
    Returns YYYY-MM-DD string or None.
    """
    soup = BeautifulSoup(html, 'html.parser')
    print(f"DEBUG: Extracting date for URL: {url}")
    
    # 1. Identify Domain
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.replace("www.", "").lower()
    
    rule = custom_rule_override or SCRAPER_REGISTRY.get(domain)
    found_date: Optional[datetime] = None
    
    if rule:
        print(f"DEBUG: Using Scraper Rule for {domain}")
        
        # A. JS/DataLayer
        if rule.use_data_layer:
            found_date = extract_from_js_datalayer(html, rule.data_layer_var or "dataLayer")
            if found_date: 
                print(f"  -> Found via DataLayer: {found_date}")
                return found_date.strftime("%Y-%m-%d")
        
        # B. Selectors
        if rule.date_selectors:
            for selector in rule.date_selectors:
                elements = soup.select(selector)
                for el in elements:
                    # Check text
                    text_val = el.get_text(strip=True)
                    
                    # 1. Try Text
                    d = parse_romanian_date(text_val)
                    if d: 
                        print(f"  -> Found via Selector '{selector}' (text): {d}")
                        return d.strftime("%Y-%m-%d")

                    # 2. Try 'content' attribute (Meta tags)
                    if el.has_attr('content'):
                        d = parse_romanian_date(el['content'].split('T')[0]) # Split ISO T just in case
                        if d:
                            print(f"  -> Found via Selector '{selector}' (content): {d}")
                            return d.strftime("%Y-%m-%d")

                    # 3. Try 'datetime' attribute (Time tags)
                    if el.has_attr('datetime'):
                        d = parse_romanian_date(el['datetime'].split('T')[0])
                        if d: 
                            print(f"  -> Found via Selector '{selector}' (datetime): {d}")
                            return d.strftime("%Y-%m-%d")

        # C. Regex via Rule
        if rule.date_regex:
            full_text = soup.get_text(" ", strip=True) 
            for pattern in rule.date_regex:
                try:
                    match = re.search(pattern, full_text)
                    if match:
                        # Expecting one group that contains the date string
                        val = match.group(1) if match.groups() else match.group(0)
                        d = parse_romanian_date(val)
                        if d:
                            print(f"  -> Found via Regex '{pattern}': {d}")
                            return d.strftime("%Y-%m-%d")
                except Exception as e:
                    print(f"WARN: Regex error {pattern}: {e}")

        # D. JSON-LD via Rule
        if rule.use_json_ld:
             scripts = soup.find_all('script', type='application/ld+json')
             for script in scripts:
                 try:
                     if not script.string: continue
                     data = json.loads(script.string)
                     
                     # Flatten @graph if present
                     items = []
                     if isinstance(data, dict):
                         if "@graph" in data:
                             items = data["@graph"]
                         else:
                             items = [data]
                     elif isinstance(data, list):
                         items = data
                         
                     for item in items:
                         # Look for datePublished, dateCreated
                         raw = item.get('datePublished') or item.get('dateCreated') or item.get('uploadDate')
                         
                         # Check nested mainEntity if applicable (sometimes schema is complex)
                         if not raw and 'mainEntity' in item:
                             raw = item['mainEntity'].get('datePublished')
                             
                         if raw:
                             d = parse_romanian_date(raw.split('T')[0])
                             if d:
                                 print(f"  -> Found via JSON-LD: {d}")
                                 return d.strftime("%Y-%m-%d")
                 except: 
                     continue

    # 2. Global Fallback (The "Smart" Engine)
    
    # A. <time> tags (Standard HTML5)
    time_tags = soup.find_all('time')
    for tag in time_tags:
        if tag.has_attr('datetime'):
             d = parse_romanian_date(tag['datetime'].split('T')[0])
             if d: return d.strftime("%Y-%m-%d")
             
    # B. Meta Tags (Schema.org / OG)
    meta_candidates = [
        {'property': 'article:published_time'},
        {'property': 'og:published_time'},
        {'name': 'date'},
        {'name': 'pubdate'},
        {'name': 'publishdate'}, # User Request: China Daily style
        {'name': 'publishtime'}, # Common variant
        {'name': 'original-publish-date'},
        {'itemprop': 'datePublished'}
    ]
    for attr in meta_candidates:
        tag = soup.find('meta', attr)
        if tag and tag.get('content'):
            d = parse_romanian_date(tag['content'].split('T')[0])
            if d: return d.strftime("%Y-%m-%d")
            
    # C. URL Extraction
    found_date = extract_date_from_url(url)
    if found_date: return found_date.strftime("%Y-%m-%d")

    # D. Heuristic Regex on Body (Risky but sometimes needed)
    # (Leaving this to the caller or AI fallback usually, as pure random regex on body is high noise)
    
    return None

async def extract_date_with_ai(html_content: str, url: str, api_key: str) -> Optional[str]:
    """
    Legacy/Fallback: Uses Gemini to extract date.
    Assumes genai is configured.
    """
    try:
        if not api_key: return None
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp') # Fast model
        
        truncated_html = html_content[:4000]
        prompt = f"""
        Extract the publication date of this news article.
        URL: {url}
        HTML Metadata/Header:
        {truncated_html}
        
        Rules:
        1. Look for 'published_time', 'date', 'time', or text like "15 Ianuarie 2026", "02.01.2026".
        2. Return ONLY the date in YYYY-MM-DD format.
        3. If no date is found, return NULL.
        """
        
        response = await model.generate_content_async(prompt)
        ans = response.text.strip()
        if "NULL" in ans: return None
        # Validate format
        if re.match(r'\d{4}-\d{2}-\d{2}', ans):
            return ans
        return None
        return None
    except Exception as e:
        print(f"AI Date Extraction Failed: {e}")
        return None

async def gemini_find_category_url(html_content: str, base_url: str, category: str, api_key: str) -> Optional[str]:
    """
    Uses Gemini to analyze the homepage navigation and find the best link for a given category.
    This works across all languages by understanding the semantic meaning of menu items.
    """
    if not api_key: return None
    
    try:
        genai.configure(api_key=api_key)
        # Use a model capable of understanding HTML structure and multiple languages
        # Using flash for speed/cost balance
        model = genai.GenerativeModel('gemini-2.0-flash-exp') 
        
        # We need the nav/header part. Cap to avoid context overflow.
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Heuristic: Extract only likely navigation areas to reduce noise
        nav_elements = soup.find_all(['nav', 'header', 'ul', 'menu', 'div.menu', 'div.nav'])
        nav_html = ""
        for n in nav_elements:
             nav_html += str(n)[:5000] # Cap each element
        
        if not nav_html:
            nav_html = html_content[:20000] # Fallback to raw top 20KB
            
        prompt = f"""
        You are a navigation assistant. Your task is to find the URL for the '{category}' section in the following HTML navigation menu.
        
        Base URL: {base_url}
        HTML Menu Snippet:
        {nav_html[:20000]}
        
        Instructions:
        1. Analyze the links (<a> tags). Translate non-English text if needed (e.g. 'Politik' = Politics).
        2. Find the link that best matches the concept of '{category}'.
        3. If the link is relative (e.g. "/politics"), resolve it against the Base URL to be absolute.
        4. Return ONLY the JSON object with the key "url". If not found, return {{"url": null}}.
        
        Example Output:
        {{"url": "https://example.com/politika"}}
        """
        
        response = await model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
        data = json.loads(response.text)
        return data.get("url")

    except Exception as e:
        print(f"AI Navigation Failed: {e}")
        return None

# --- Link Extraction ---
def extract_article_links(html: str, base_url: str) -> List[Dict[str, str]]:
    """
    Extracts high-quality article links from a category/homepage.
    Returns list of dicts: {'url': ..., 'title': ...}
    """
    from urllib.parse import urljoin
    soup = BeautifulSoup(html, 'html.parser')
    candidates = []
    seen_urls = set()
    
    raw_links = soup.find_all('a', href=True)
    with open("stream_debug.log", "a") as f: f.write(f"EXTRACT_ENGINE: Found {len(raw_links)} raw links in {base_url}\n")
    
    import traceback
    
    for a in raw_links:
        try:
            href = a.get('href', None)
            if not href: continue
            
            full_url = urljoin(base_url, href)
            
            # Helper to log immediate crash
            with open("stream_debug.log", "a") as f: 
                 # f.write(f"CHECKING: {full_url}\n") 
                 pass
            
            # Basic Validation
            if full_url in seen_urls: continue
            
            # IS VALID CHECK (Wrapped)
            try:
                if not is_valid_article_url(full_url): 
                    # Log handled inside is_valid_article_url
                    continue
            except Exception as e:
                with open("stream_debug.log", "a") as f: f.write(f"CRASH_IN_VALIDATION: {full_url} -> {e}\n")
                continue
                
            if full_url == base_url or full_url + "/" == base_url: 
                 with open("stream_debug.log", "a") as f: f.write(f"REJECT_SELF: {full_url}\n")
                 continue # Skip self
            
            title = a.get_text(strip=True)

            if len(title) < 2: 
                 with open("stream_debug.log", "a") as f: f.write(f"REJECT_EMPTY_TITLE: {full_url}\n")
                 continue 
            
            candidates.append({'url': full_url, 'title': title})
            seen_urls.add(full_url)
        except Exception as e:
            with open("stream_debug.log", "a") as f: 
                 f.write(f"CRASH_IN_LOOP: {e}\n")
                 traceback.print_exc(file=f)
        
    return candidates

def detect_content_type(html: str) -> str:
    """
    Analyzes HTML to determine if it's an Article or a Category/Landing page.
    Returns: 'article', 'category', or 'unknown'
    """
    if not html: return "unknown"
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Content-Based Heuristics (More reliable than Metadata)
    
    # A. Link Density Check
    # Categories/Landing pages have high ratio of link text to total text.
    all_text = soup.get_text(strip=True)
    if len(all_text) < 100: return "unknown" # innovative
    
    links = soup.find_all("a")
    link_text_len = sum(len(a.get_text(strip=True)) for a in links)
    
    link_density = link_text_len / len(all_text)
    
    # B. Title/Keyword Check (Noise Filter)
    title = soup.title.string.lower() if soup.title else ""
    noise_keywords = [
        "donate", "support", "pidtrymka", "contact", "rubric", "donat",
        "termeni", "conditii", "gdpr", "confidentialitate",
        "index", "homepage", "arhiva", "login", "register"
    ]
    if any(k in title for k in noise_keywords):
        return "category" # Treat as category/page to reject
        
    # Decision: High Link Density -> Category
    if link_density > 0.45:
        return "category"

    # 2. Paragraph Heuristic (Legacy but valid)
    paragraphs = soup.find_all("p")
    significant_paras = 0
    total_p_text_length = 0
    
    for p in paragraphs:
        text = p.get_text(strip=True)
        if len(text) > 60: 
            significant_paras += 1
            total_p_text_length += len(text)
            
    # 3. Decision Logic
    if significant_paras < 2:
        return "category"
        
    # 4. Metadata Check (Secondary - only if heuristics are ambiguous? No, trust heuristics first)
    # If og:type says article but density is high, we trusted density (above).
    # If density is low (looks like article) AND significant paras exist:
    if significant_paras >= 3 and total_p_text_length > 500:
        return "article"
        
    return "unknown" 

def is_valid_article_url(url: str) -> bool:
    """
    Strict filter to reject non-article pages (categories, feeds, ads, etc.).
    """
    import re
    if not url: return False
    
    url_lower = url.lower()
    
    # DEBUG LOGGING
    with open("stream_debug.log", "a") as f:
         # f.write(f"VALIDATING: {url}\n") 
         pass
         
    # 0. Protocol Check
    if not (url_lower.startswith('http://') or url_lower.startswith('https://')):
        with open("stream_debug.log", "a") as f: f.write(f"REJECT_PROTOCOL: {url}\n")
        return False
        
    # 1. Extensions to ignore
    if any(url_lower.endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.gif', '.xml', '.rss', '.atom', '.mp3', '.mp4']):
        with open("stream_debug.log", "a") as f: f.write(f"REJECT_EXT: {url}\n")
        return False
        
    # 2. Blacklisted keywords (Legacy + Universal Spam Filter)
    
    # Universal Spam Filter Rules (V4 - Content Verified)
    # 1. Substrings: Safe to block if anywhere in path
    BLOCKED_SUBSTRINGS = {
        "login", "signin", "signup", "register", "password", 
        "subscribe", "subscription", "unsubscribe",
        "terms-of-service", "privacy-policy", "cookie-policy",
        "newsletter", "rss-feed", "sitemap", 
        "advertorial", "mediakit",
        "/tag/", "/category/", "/topic/", "/author/", "/section/", 
        "/c/", "/szero/", # Specific taxonomies
        "odr/main", # EU Dispute
        "epaper", "paperindex", "html5/reader", "onelink.me",
        "/feed/", "/rss", "/search", "/cart/", "/basket/"
    }

    # 2. Segments: Only block if FULL path segment
    BLOCKED_SEGMENTS = {
        "admin", "dashboard", "profile", "user", "account", "billing", "my",
        "donate", "donation", "giving", "pay", "payment", "checkout", "cart", "shop",
        "careers", "jobs", "employment", "vacancy", "work-with-us",
        "terms", "privacy", "legal", "gdpr", "tos", "policy", "rules", "disclaimer", "copyright",
        "contact", "contact-us", "about", "about-us", "info", "help", "faq", "support", "feedback",
        "search", "find", "archive", "weather", "horoscope", "traffic",
        "gallery", "photos", "video", "videos", "live", "watch", "listen", "podcast", "shows",
        "stiri", "servicii", "codul", "redactia", "echipa", "publicitate", "abonamente",
        "mobile", "scroll", "newmedia", "special", "specials"
    }

    # High-Risk Domains (Hard Block)
    BLOCKED_DOMAINS = {
        "accuweather.com", "weather.com", "airtable.com", "intuit.com", 
        "oraclecloud.com", "pagesuite-professional.co.uk", "eepurl.com",
        "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
        "youtube.com", "google.com", "bing.com", "foxlocal.onelink.me",
        "help.startribune.com", "corp.sina.com.cn", "games.sina.com.cn",
        "hugedomains.com", "issuu.com", "ec.europa.eu", "paydemic.com", "wordpress.org"
    }

    # A. Domain Check
    parsed = urlparse(url)
    domain_part = parsed.netloc.replace("www.", "").lower()
    if any(d in domain_part for d in BLOCKED_DOMAINS):
        with open("stream_debug.log", "a") as f: f.write(f"REJECT_DOMAIN: {url}\n")
        return False
        
    path = parsed.path.lower()
    
    # B. Substring Check
    for kw in BLOCKED_SUBSTRINGS:
        if kw in path:
            with open("stream_debug.log", "a") as f: f.write(f"REJECT_KEYWORD [{kw}]: {url}\n")
            return False

    # C. Segment Check
    segments = [s for s in path.strip("/").split("/") if s]
    for seg in segments:
         if seg in BLOCKED_SEGMENTS:
             with open("stream_debug.log", "a") as f: f.write(f"REJECT_SEGMENT [{seg}]: {url}\n")
             return False

    # 3. Explicit Pagination Check
    # Matches: /page/2, /2.html (if segment is just digit), /p/2
    if re.search(r'/(page|p)/\d+', url_lower) or re.search(r'/\d+\.html$', url_lower):
        # Exception: Some articles are just ID.html (e.g. /12345.html)
        # But /1.html or /2.html are usually pages.
        # Let's be careful. If the number is small (< 100), likely pagination.
        match = re.search(r'/(\d+)\.html$', url_lower)
        if match:
             num = int(match.group(1))
             if num < 50: 
                 with open("stream_debug.log", "a") as f: f.write(f"REJECT_PAGINATION_ID: {url}\n")
                 return False # Page 1-49 usually pagination
        else:
             if '/page/' in url_lower: 
                 with open("stream_debug.log", "a") as f: f.write(f"REJECT_PAGINATION: {url}\n")
                 return False
            
    # 4. Path Analysis (Structural)
    path_strip = path.strip("/")
    if not path_strip: 
        with open("stream_debug.log", "a") as f: f.write(f"REJECT_HOMEPAGE: {url}\n")
        return False # Homepage
    
    last_seg = segments[-1] if segments else ""
    
    # 5. Pagination Blocking (e.g. /news/2/, /page/5)
    if re.match(r'^\d+$', last_seg):
        if len(last_seg) < 4: 
             with open("stream_debug.log", "a") as f: f.write(f"REJECT_SHORT_DIGIT: {url}\n")
             return False 
 
    # 6. Trailing Slash Heuristic
    # Note: We relaxed this for the content-based filter. 
    # Only blocking if it looks VERY much like a category (1 segment, no digits)
    # e.g. /politics/ -> Block. /my-article-title/ -> Keep.
 
    # Reject high-level single-segment paths that look like categories
    # e.g. /politics (reject), /2025/article (accept), /long-slug-with-id (accept)
    if len(segments) == 1:
        slug = segments[0]
        # Heuristic: Articles usually have IDs (digits) or long slugs with hyphens
        has_digits = any(c.isdigit() for c in slug)
        hyphen_count = slug.count("-")
        
        # KEY CHANGE: Relaxed length from 20 to 15, and requiring NO hyphens to block.
        # If it has 2+ hyphens, it's likely an article title "man-bites-dog"
        # If it has NO hyphens and is short, it's "sports", "world".
        
        if len(slug) < 20 and not has_digits and hyphen_count < 2:
             with open("stream_debug.log", "a") as f: f.write(f"REJECT_SINGLE_SEG_CAT: {url}\n")
             return False
        
        # Block specific short paths that might be missed by keywords
        if slug in ["opinion", "editorials"]: # Explicit short-path block, but allow /opinion/foo
             with open("stream_debug.log", "a") as f: f.write(f"REJECT_SINGLE_SEG_OPINION: {url}\n")
             return False
             
    # 7. Query Param Check
    if parsed.query:
        q = parsed.query.lower()
        # Aggressive blocking of sort/filter params usually found on lists
        bad_params = ['cat_id', 'tag', 'sort', 'filter', 'page', 'p=', 'limit', 'utm_source'] 
        if any(p in q for p in ['cat_id=', 'tag=', 'sort=', 'filter=', 'page=']):
            return False
            
    return True

async def fetch_sitemap_urls(base_url: str, max_urls: int = 50, days_limit: int = 3) -> List[str]:
    """
    Attempts to fetch and parse sitemap.xml for a given base URL.
    Returns list of FRESH article URLs (last N days) found in sitemap(s), capped at max_urls.
    """
    # Try standard paths (prioritize news sitemaps)
    paths = ["/sitemap-news.xml", "/sitemap_news.xml", "/sitemap.xml", "/sitemap_index.xml", "/wp-sitemap.xml"]
    
    found_items = [] # List of (date, url) tuples for sorting
    sub_sitemaps_fetched = 0
    
    try:
        import httpx
        import xml.etree.ElementTree as ET
        from datetime import datetime, timedelta
        
        # Threshold: N days ago
        cutoff_date = datetime.now() - timedelta(days=days_limit)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/xml,text/xml,application/xhtml+xml,text/html;q=0.9,*/*;q=0.8"
        }

        async with httpx.AsyncClient(verify=False, timeout=20, follow_redirects=True, headers=headers) as client:
            for path in paths:
                target = base_url.rstrip("/") + path
                try:
                    resp = await client.get(target)
                    if resp.status_code == 200 and "xml" in resp.headers.get("Content-Type", "").lower():
                        # Limit XML size to 10MB to prevent OOM/DoS
                        if len(resp.content) > 10 * 1024 * 1024:
                            print(f"Skipping sitemap {target}: Too large ({len(resp.content)} bytes)")
                            continue
                            
                        try:
                            root = ET.fromstring(resp.text)
                        except ET.ParseError:
                            print(f"Skipping sitemap {target}: Invalid XML")
                            continue

                        # Better loop: Iterate top-level children (url or sitemap)
                        # We need to handle namespaces blindly
                        for item in root:
                            url = None
                            lastmod_date = None
                            
                            for child in item:
                                tag = child.tag.split('}')[-1]
                                if tag == "loc": url = child.text.strip() if child.text else None
                                if tag == "lastmod": 
                                    try: 
                                        # Parsing ISO date (many formats possible, take first 10 chars YYYY-MM-DD)
                                        d_str = child.text.strip()[:10]
                                        lastmod_date = datetime.strptime(d_str, "%Y-%m-%d")
                                    except: pass
                                    
                            if url:
                                # Recursive check if it points to another xml (Index)
                                if url.endswith(".xml"):
                                    # Limit recursion to avoid infinite archives
                                    if sub_sitemaps_fetched >= 3: continue # Reduced to 3
                                    
                                    if lastmod_date and lastmod_date < cutoff_date:
                                        continue 
                                        
                                    try:
                                        sub_sitemaps_fetched += 1
                                        sub_resp = await client.get(url)
                                        if sub_resp.status_code == 200:
                                            if len(sub_resp.content) > 5 * 1024 * 1024: continue
                                            sub_root = ET.fromstring(sub_resp.text)
                                            # Extract from sub
                                            for sub_item in sub_root:
                                                s_url = None
                                                s_date = None
                                                for sub_child in sub_item:
                                                    tag = sub_child.tag.split('}')[-1]
                                                    if tag == "loc": s_url = sub_child.text.strip() if sub_child.text else None
                                                    if tag == "lastmod" and sub_child.text:
                                                        try:
                                                            s_date = datetime.strptime(sub_child.text.strip()[:10], "%Y-%m-%d")
                                                        except: pass
                                                
                                                # APPLY FILTER
                                                if s_url and is_valid_article_url(s_url):
                                                    # Filter by date if available
                                                    if s_date:
                                                        if s_date >= cutoff_date:
                                                            found_items.append((s_date, s_url))
                                                    else:
                                                        found_items.append((None, s_url))
                                    except: pass
                                else:
                                    # APPPLY FILTER (Root Level)
                                    if is_valid_article_url(url):
                                        if lastmod_date:
                                            if lastmod_date >= cutoff_date:
                                                found_items.append((lastmod_date, url))
                                        else:
                                            found_items.append((datetime.min, url))
                                            
                        # If we found something, break (one valid sitemap path is enough)
                        if found_items: break
                except Exception as e:
                    # print(f"Sitemap parse error: {e}")
                    continue
                    
    except Exception as e:
        print(f"Sitemap fetch failed: {e}")
       
    # Sort by date desc (newest first)
    found_items.sort(key=lambda x: x[0], reverse=True)
    
    # Return top N URLs
    return [x[1] for x in found_items[:max_urls]]

def generate_master_timeline(all_events_map: Dict[str, List[Dict[str, Any]]]):
    """
    Generates a master HTML timeline for ALL sources + Histogram of operations.
    all_events_map: { "OutletName": [events...] }
    """
    if not all_events_map: return

    # Flatten for global bounds
    all_events_flat = []
    for src, evs in all_events_map.items():
        for e in evs:
            e['source'] = src
            all_events_flat.append(e)

    if not all_events_flat: return

    start_time = min(e['start'] for e in all_events_flat)
    end_time = max(e.get('end', e['start']) for e in all_events_flat)
    total_duration = end_time - start_time
    if total_duration == 0: total_duration = 1

    # Colors
    colors = {
        "fetch": "#3b82f6",     # Blue
        "parse": "#a855f7",     # Purple
        "extract": "#eab308",   # Yellow
        "deep_scan": "#ef4444", # Red
        "rescue": "#22c55e",    # Green
        "init": "#64748b",      # Gray
        "other": "#94a3b8"
    }

    # Histogram Data Aggregation
    # Sum duration per type
    stats = {}
    for e in all_events_flat:
        etype = e.get('type', 'other')
        dur = e.get('end', e['start']) - e['start']
        if etype not in stats: stats[etype] = 0.0
        stats[etype] += dur

    # Generate HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Master Scraper Timeline ({len(all_events_map)} Sources)</title>
        <style>
            body {{ font-family: system-ui, sans-serif; padding: 20px; background: #0f172a; color: white; }}
            h1, h2 {{ color: #e2e8f0; }}
            .container {{ display: flex; flex-direction: column; gap: 40px; }}
            
            /* Gantt Styles */
            .timeline-container {{ width: 100%; border: 1px solid #334155; padding: 10px; border-radius: 8px; background: #1e293b; overflow-x: auto; }}
            .timeline-row {{ position: relative; height: 40px; border-bottom: 1px solid #334155; margin-bottom: 5px; }}
            .timeline-label {{ position: absolute; left: 0; width: 150px; font-size: 12px; line-height: 40px; padding-left: 10px; color: #94a3b8; font-weight: bold; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }}
            .timeline-track {{ position: absolute; left: 160px; right: 0; height: 100%; }}
            .bar {{ position: absolute; height: 24px; top: 8px; border-radius: 4px; font-size: 10px; padding-left: 5px; line-height: 24px; white-space: nowrap; overflow: hidden; color: rgba(255,255,255,0.9); box-shadow: 0 1px 2px rgba(0,0,0,0.3); }}
            
            /* Histogram Styles */
            .chart-container {{ width: 100%; max-width: 800px; padding: 20px; background: #1e293b; border-radius: 8px; }}
            .bar-row {{ display: flex; align-items: center; margin-bottom: 15px; }}
            .bar-label {{ width: 100px; font-size: 14px; text-transform: capitalize; }}
            .bar-track {{ flex-grow: 1; background: #334155; height: 20px; border-radius: 10px; overflow: hidden; position: relative; }}
            .bar-fill {{ height: 100%; border-radius: 10px; transition: width 0.5s; }}
            .bar-val {{ width: 80px; text-align: right; padding-left: 10px; font-mono; font-size: 13px; color: #cbd5e1; }}
        </style>
    </head>
    <body>
        <h1>Master Scraper Timeline</h1>
        <div class="info">Total Duration: {total_duration:.2f}s | Sources: {len(all_events_map)} | Events: {len(all_events_flat)}</div>
        
        <div class="container">
            <!-- Section 1: Gantt Chart -->
            <div>
                <h2>Operation Timeline</h2>
                <div class="timeline-container">
    """
    
    # Sort outlets by name
    sorted_outlets = sorted(all_events_map.keys())
    
    for outlet in sorted_outlets:
        evs = all_events_map[outlet]
        html += f"""
        <div class="timeline-row">
            <div class="timeline-label">{outlet}</div>
            <div class="timeline-track">
        """
        for e in evs:
            start_pct = ((e['start'] - start_time) / total_duration) * 100
            duration = e.get('end', e['start']) - e['start']
            width_pct = (duration / total_duration) * 100
            if width_pct < 0.1: width_pct = 0.1 # Min visibility
            
            color = colors.get(e.get('type', 'other'), colors['other'])
            label = f"{e.get('label', e.get('type'))}"
            
            html += f"""
                <div class="bar" style="left: {start_pct}%; width: {width_pct}%; background: {color};" title="{label} ({duration:.2f}s)"></div>
            """
        html += """
            </div>
        </div>
        """
        
    html += """
                </div>
            </div>
            
            <!-- Section 2: Histogram -->
            <div>
                <h2>Time Distribution (Total Seconds)</h2>
                <div class="chart-container">
    """
    
    max_val = max(stats.values()) if stats else 1
    
    for etype, val in stats.items():
        pct = (val / max_val) * 100
        color = colors.get(etype, colors['other'])
        html += f"""
            <div class="bar-row">
                <div class="bar-label">{etype}</div>
                <div class="bar-track">
                    <div class="bar-fill" style="width: {pct}%; background: {color};"></div>
                </div>
                <div class="bar-val">{val:.2f}s</div>
            </div>
        """
        
    html += """
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open("master_timeline.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Master Timeline saved to master_timeline.html")

# --- Title Extraction ---
def extract_title_from_html(html: str, url: str, custom_rule_override: Optional[ScraperRule] = None) -> Optional[str]:
    """
    Extracts the article title using Rules, Metadata, or Heuristics.
    """
    if not html: return None
    soup = BeautifulSoup(html, 'html.parser')
    
    # 0. Check Rules Registry or Override
    rule = custom_rule_override
    if not rule:
        domain = url.split("//")[-1].split("/")[0].replace("www.", "")
        rule = SCRAPER_REGISTRY.get(domain)
    
    if rule and rule.title_selectors:
        for selector in rule.title_selectors:
            try:
                el = soup.select_one(selector)
                if el:
                    text = el.get_text(strip=True)
                    if len(text) > 5: return text
            except Exception as e:
                print(f"Rule Title Selector '{selector}' failed: {e}")

    # 1. Open Graph Meta
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title["content"].strip()

    # 2. H1 (Standard for most CMS)
    h1 = soup.find("h1")
    if h1:
        text = h1.get_text(strip=True)
        if len(text) > 5: return text

    # 3. Twitter Card
    tw_title = soup.find("meta", name="twitter:title")
    if tw_title and tw_title.get("content"):
        return tw_title["content"].strip()
        
    # 4. Fallback to <title>
    if soup.title:
        return soup.title.get_text(strip=True)

    return None
