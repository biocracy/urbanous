import os
import httpx
import hashlib
import json
from urllib.parse import urlparse

STATIC_URL_PREFIX = "/static/flags"

# Determine path dynamically to match main.py serving logic
DATA_DIR = os.getenv("DATA_DIR")
if not DATA_DIR:
    if os.path.exists("/app/data"):
        DATA_DIR = "/app/data"
    else:
        DATA_DIR = "." # Fallback to current directory (likely backend/..)
        
STATIC_FLAGS_DIR = os.path.join(DATA_DIR, "static", "flags")
MAPPING_FILE = os.path.join(STATIC_FLAGS_DIR, "country_map.json")

# Cache the mapping
_COUNTRY_MAP = None

def get_country_code(name: str):
    global _COUNTRY_MAP
    if _COUNTRY_MAP is None:
        try:
            if os.path.exists(MAPPING_FILE):
                with open(MAPPING_FILE, "r") as f:
                    _COUNTRY_MAP = json.load(f)
                    # Normalize keys to lowercase for robust matching
                    _COUNTRY_MAP = {k.lower(): v for k, v in _COUNTRY_MAP.items()}
            else:
                _COUNTRY_MAP = {}
        except Exception as e:
            print(f"Error loading country map: {e}")
            _COUNTRY_MAP = {}
    
    if not name:
        return None
    return _COUNTRY_MAP.get(name.lower().strip())

async def ensure_local_flag(remote_url: str, country_name: str = None) -> str:
    """
    Returns the local URL path for a flag.
    Prioritizes looking up by Country Name -> ISO Code -> Local File.
    Falls back to downloading the remote URL if no local match found.
    """
    
    # 1. Try ISO Lookup (Best Quality)
    if country_name:
        iso_code = get_country_code(country_name)
        if iso_code:
            local_filename = f"{iso_code}.png"
            local_path = os.path.join(STATIC_FLAGS_DIR, local_filename)
            if os.path.exists(local_path):
                return f"{STATIC_URL_PREFIX}/{local_filename}"

    # 2. Existing Fallback Logic (Download Remote)
    if not remote_url or remote_url.startswith(STATIC_URL_PREFIX):
        return remote_url or ""
        
    # Create filename hash to avoid weird characters
    ext = os.path.splitext(urlparse(remote_url).path)[1]
    if not ext or len(ext) > 5:
        ext = ".svg" # Default to svg if unsure
        
    if country_name:
        safe_name = "".join([c for c in country_name.lower() if c.isalnum() or c=='-']).strip()
        filename = f"{safe_name}{ext}"
    else:
        hash_name = hashlib.md5(remote_url.encode()).hexdigest()
        filename = f"{hash_name}{ext}"

    # Ensure Dir Exists
    if not os.path.exists(STATIC_FLAGS_DIR):
        os.makedirs(STATIC_FLAGS_DIR)

    local_path = os.path.join(STATIC_FLAGS_DIR, filename)
    public_url = f"{STATIC_URL_PREFIX}/{filename}"

    # Check existence
    if os.path.exists(local_path):
        return public_url

    # Download
    print(f"DEBUG: Localizing flag for {country_name} from {remote_url}")
    try:
        headers = {"User-Agent": "Urbanous/1.0"}
        async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers=headers) as client:
            resp = await client.get(remote_url)
            if resp.status_code == 200:
                with open(local_path, "wb") as f:
                    f.write(resp.content)
                return public_url
            else:
                print(f"WARN: Failed to download flag {remote_url}, status {resp.status_code}")
                # Don't return remote_url if it failed? actually keep remote as last resort
                return remote_url
    except Exception as e:
        print(f"ERROR: Could not localize flag {remote_url}: {e}")
        return remote_url

    return remote_url
