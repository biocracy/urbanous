import json
import os
import math
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import NewsOutlet
import time

# --- Configuration ---
DATABASE_URL = "sqlite:///backend/urbanous.db"
OUTPUT_DIR = "backend/static/clusters"
RADII = [0.1, 0.3, 0.5, 0.7, 1.0]
CITIES_URL = 'https://raw.githubusercontent.com/lmfmaier/cities-json/master/cities500.json'

# --- Database Setup ---
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_pop_scale(pop_str):
    try:
        pop = int(pop_str) if pop_str else 0
        if pop > 10_000_000: return 4.5
        if pop > 5_000_000: return 3.5
        if pop > 1_000_000: return 2.5
        if pop > 500_000: return 2.0
        if pop > 100_000: return 1.5
        return 1.0
    except:
        return 1.0

def compute_clusters(items, radius_deg, news_city_names=set()):
    """
    Greedy clustering algorithm for CITIES only.
    """
    clusters = []
    
    # Sort by population (desc)
    sorted_items = sorted(items, key=lambda x: int(x.get('pop', 0)), reverse=True)

    for item in sorted_items:
        try:
            lat = float(item.get('lat', 0))
            lng = float(item.get('lon', 0))
            name = item.get('name')
            country = item.get('country')
            pop_val = int(item.get('pop', 0))
            
            if not lat or not lng: continue
        except:
            continue

        # Check if this city has news
        has_news = name in news_city_names
        
        # Color Logic (to match Frontend)
        # We store 'hasNews' boolean, frontend handles color.
        
        # Find existing cluster
        found_cluster = None
        for cluster in clusters:
            # STRICT CHECK: Only cluster cities from the SAME country.
            if cluster['country'] != country:
                continue

            dist = math.sqrt((cluster['lat'] - lat)**2 + (cluster['lng'] - lng)**2)
            if dist < radius_deg:
                found_cluster = cluster
                break
        
        # Point Object
        point = {
            "name": name,
            "lat": lat,
            "lng": lng, 
            "pop": pop_val,
            "radius": get_pop_scale(pop_val),
            "country": country,
            "hasNews": has_news
        }

        if found_cluster:
            found_cluster['subPoints'].append(point)
            found_cluster['count'] += 1
            # If subpoint has news, the cluster effectively has news
            if has_news:
                found_cluster['hasNews'] = True
        else:
            # New Cluster Head
            clusters.append({
                "id": f"c-{lat}-{lng}",
                "lat": lat,
                "lng": lng,
                "name": name,
                "count": 1,
                "isCluster": True,
                "subPoints": [],
                "pop": pop_val,
                "radius": get_pop_scale(pop_val),
                "country": country,
                "hasNews": has_news
            })
            
    return clusters

def main():
    print("--- Starting Corrected Cluster Pre-computation ---")
    session = SessionLocal()
    
    try:
        # 1. Load News Cities from DB
        outlets = session.query(NewsOutlet).all()
        news_city_names = set()
        for o in outlets:
            if o.city:
                news_city_names.add(o.city)
        print(f"Index: Found {len(news_city_names)} cities with active news coverage.")
        
        # 2. Setup Dirs
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 3. Download Cities
        print(f"Downloading Cities from {CITIES_URL}...")
        resp = requests.get(CITIES_URL)
        cities_data = resp.json()
        cities_data = [c for c in cities_data if int(c.get('pop', 0) or 0) > 100000] # Major only
        print(f"Loaded {len(cities_data)} major cities.")

        # 4. Compute
        for r in RADII:
            print(f"Clustering Cities for Radius {r}°...")
            c_clusters = compute_clusters(cities_data, r, news_city_names)
            path = os.path.join(OUTPUT_DIR, f"cities_{r}.json")
            with open(path, "w") as f:
                json.dump(c_clusters, f)
            print(f"Saved {len(c_clusters)} city clusters (Active tagged).")

    except Exception as e:
        print(f"Processing Failed: {e}")
    finally:
         session.close()

if __name__ == "__main__":
    main()
