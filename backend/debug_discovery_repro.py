import asyncio
import os
import sys

# Ensure backend path is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routers.outlets import gemini_discover_city_outlets
from dotenv import load_dotenv

load_dotenv()

async def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in env.")
        # Try to find it manually or prompt user?
        # Assuming it's in .env file loaded above.
        return

    city = "Canberra"
    country = "Australia"
    lat = -35.2809
    lng = 149.1300

    print(f"--- Testing Discovery for {city}, {country} ---")
    try:
        outlets = await gemini_discover_city_outlets(city, country, lat, lng, api_key)
        print(f"Result count: {len(outlets)}")
        for o in outlets:
            print(f"- {o.name} ({o.country_code}) -> {o.url} [Pop: {o.popularity}]")
    except Exception as e:
        print(f"CRITICAL FAILURE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
