
import os
import httpx
import asyncio
import json

# Output directory
FLAGS_DIR = "backend/static/flags"
MAPPING_FILE = "backend/static/flags/country_map.json"

async def download_flags():
    if not os.path.exists(FLAGS_DIR):
        os.makedirs(FLAGS_DIR)

    async with httpx.AsyncClient() as client:
        # 1. Get Codes and Names
        print("Fetching country codes...")
        try:
            resp = await client.get("https://flagcdn.com/en/codes.json")
            resp.raise_for_status()
            codes = resp.json() # {"ad": "Andorra", ...}
        except Exception as e:
            print(f"Error fetching codes: {e}")
            return

        # 2. Invert and Save Map (Name -> Code)
        # Handle simple cases. Complex names might need fuzzy matching later, 
        # but this covers standard ones.
        name_to_code = {name: code for code, name in codes.items()}
        
        # Add some manual overrides for common mismatches if known, e.g.:
        name_to_code["United States"] = "us"
        name_to_code["United Kingdom"] = "gb"
        name_to_code["Russia"] = "ru" 
        
        with open(MAPPING_FILE, "w") as f:
            json.dump(name_to_code, f, indent=2)
        print(f"Saved mapping for {len(name_to_code)} countries to {MAPPING_FILE}")

        # 3. Download Flags
        tasks = []
        sem = asyncio.Semaphore(10) # Limit concurrency

        async def download_one(code, name):
            async with sem:
                filename = f"{code}.png"
                filepath = os.path.join(FLAGS_DIR, filename)
                
                if os.path.exists(filepath):
                    # print(f"Skipping {code} ({name}) - exists")
                    return

                url = f"https://flagcdn.com/w320/{code}.png"
                try:
                    r = await client.get(url)
                    if r.status_code == 200:
                        with open(filepath, "wb") as f:
                            f.write(r.content)
                        print(f"Downloaded {code}.png ({name})")
                    else:
                        print(f"Failed to download {code}: {r.status_code}")
                except Exception as e:
                    print(f"Error downloading {code}: {e}")

        for code, name in codes.items():
            tasks.append(download_one(code, name))
        
        await asyncio.gather(*tasks)
        print("Done.")

if __name__ == "__main__":
    asyncio.run(download_flags())
