import os
import httpx
import hashlib
from urllib.parse import urlparse

STATIC_FLAGS_DIR = "backend/static/flags"
STATIC_URL_PREFIX = "/static/flags"

async def ensure_local_flag(remote_url: str, country_name: str = None) -> str:
    """
    Checks if a flag image is already local. If not, downloads it.
    Returns the local URL path (e.g. /static/flags/xyz.svg) or original URL if failure.
    """
    if not remote_url or remote_url.startswith(STATIC_URL_PREFIX):
        return remote_url
        
    # Create filename hash to avoid weird characters
    ext = os.path.splitext(urlparse(remote_url).path)[1]
    if not ext or len(ext) > 5:
        ext = ".svg" # Default to svg if unsure, commonly referenced
        
    # Use country name for readable filename if possible, else hash URL
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
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(remote_url)
            if resp.status_code == 200:
                with open(local_path, "wb") as f:
                    f.write(resp.content)
                return public_url
            else:
                print(f"WARN: Failed to download flag {remote_url}, status {resp.status_code}")
                return remote_url # Fallback
    except Exception as e:
        print(f"ERROR: Could not localize flag {remote_url}: {e}")
        return remote_url

    return remote_url
