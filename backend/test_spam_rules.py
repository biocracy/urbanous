
import json
import re
from urllib.parse import urlparse

# Proposed Global Rules
BLOCKED_DOMAINS = {
    "accuweather.com", "weather.com", "airtable.com", "intuit.com", 
    "oraclecloud.com", "pagesuite-professional.co.uk", "eepurl.com",
    "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
    "youtube.com", "google.com", "bing.com", "foxlocal.onelink.me",
    "help.startribune.com", "corp.sina.com.cn", "games.sina.com.cn",
    "hugedomains.com", "issuu.com", "ec.europa.eu"
}

BLOCKED_SUBDOMAINS = {
    "help", "support", "status", "corp", "career", "jobs", "job", "shop", "store", 
    "subscribe", "subscription", "billing", "account", "mail", "my", "login", 
    "admin", "edition", "connect", "beta", "pay", "checkout"
}


# 1. Substrings: These are safe to block if they appear ANYWHERE in the path (e.g. file.php?login=true)
BLOCKED_SUBSTRINGS = {
    "login", "signin", "signup", "register", "password", 
    "subscribe", "subscription", "unsubscribe",
    "terms-of-service", "privacy-policy", "cookie-policy",
    "newsletter", "rss-feed", "sitemap", 
    "advertorial", "mediakit",
    "/tag/", "/category/", "/topic/", "/author/", "/section/", 
    "/c/", "/stiri/", "/szerzo/", # Hungarian author
    "odr/main", # EU Dispute
    "epaper", "paperindex", "html5/reader", "onelink.me"
}

# 2. Segments: These only block if they are a FULL path segment (between slashes).
# e.g. /admin/ matches, but /administration/ does NOT.
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

def is_spam(url):
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        path = parsed.path.lower()
        subdomain = domain.split(".")[0] if domain.count(".") > 1 else ""
        
        # 1. Domain Block
        if any(d.lower() in domain.lower() for d in BLOCKED_DOMAINS):
            return "Domain Block"
            
        # 1.5 Subdomain Block
        if subdomain in BLOCKED_SUBDOMAINS:
             return f"Subdomain Block: {subdomain}"

        # 2. Substring Block (Aggressive)
        for kw in BLOCKED_SUBSTRINGS:
            if kw in path:
                return f"Keyword Block: {kw}"

        # 3. Segment Block (Exact)
        segments = [s for s in path.strip("/").split("/") if s]
        for seg in segments:
            if seg in BLOCKED_SEGMENTS:
                return f"Segment Block: {seg}"
        
        # 4. Structural Heuristics
        # Heuristic: Root Path or Index File
        if path == "/" or path == "": return "Root Path"
        if re.search(r"(index|default)\.(html|htm|php|asp|aspx)$", path):
             return "Index File"
             
        last_seg = segments[-1]
        
        # Short First-Level path (often Category)
        # e.g. /world, /sport. But excludes /2024 (Year)
        if len(segments) == 1:
            # Avoid blocking years like /2024
            if not re.match(r'^\d+$', last_seg):
                if len(last_seg) < 20 and not last_seg.endswith(".html"):
                     return f"Short Path Index (len={len(last_seg)})"
    except:
        return False

def test():
    with open('backend/spam_urls.json', 'r') as f:
        data = json.load(f)
    
    caught = 0
    total = len(data)
    
    print(f"Testing {total} URLs...")
    
    for item in data:
        res = is_spam(item['url'])
        if res:
            caught += 1
        else:
            print(f"[MISSED]  {item['url']}")
            pass
            
    print(f"\nFinal Result: Caught {caught}/{total} ({caught/total*100:.1f}%)")

if __name__ == "__main__":
    test()
