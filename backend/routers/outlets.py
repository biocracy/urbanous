import os
import json
import httpx
import google.generativeai as genai
from bs4 import BeautifulSoup
import asyncio # Added for digest parallel requests
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import select, distinct
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from database import AsyncSessionLocal
from database import AsyncSessionLocal
from models import NewsOutlet, User, Country, CityMetadata
from dependencies import get_current_user

from datetime import datetime, timedelta
import re

router = APIRouter()

# --- Pydantic Schemas ---
class OutletCreate(BaseModel):
    name: str
    country_code: str
    city: str
    lat: Optional[float] = 0.0
    lng: Optional[float] = 0.0
    url: Optional[str] = None
    type: Optional[str] = "Unknown" # Print, Online, TV, Radio
    popularity: Optional[int] = 5
    focus: Optional[str] = "Local"

class OutletRead(BaseModel):
    id: int
    name: str
    country_code: str
    city: str
    lat: float
    lng: float
    url: Optional[str] = None
    type: Optional[str] = "Unknown"
    url: Optional[str] = None
    type: Optional[str] = "Unknown"
    origin: Optional[str] = "auto"
    popularity: Optional[int] = 5
    focus: Optional[str] = "Local"
    
    class Config:
        from_attributes = True

class GeocodeRequest(BaseModel):
    city: str
    country: str

class GeocodeResponse(BaseModel):
    lat: float
    lng: float

from google.api_core.exceptions import ResourceExhausted

class CityDiscoveryRequest(BaseModel):
    city: str
    country: str
    lat: Optional[float] = 0.0
    lng: Optional[float] = 0.0
    force_refresh: bool = False

class ImportUrlRequest(BaseModel):
    url: str
    city: str
    country: str
    lat: Optional[float] = 0.0

class CityInfoResponse(BaseModel):
    population: str
    description: str
    ruling_party: str
    flag_url: Optional[str] = None
    lng: Optional[float] = 0.0
    instructions: Optional[str] = None

# --- Helpers ---

def parse_romanian_date(date_str: str) -> Optional[datetime]:
    """
    Parses dates like '29 decembrie 2025', 'Accepts relative time if simple'.
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
        "decembrie": 12, "dec": 12
    }
    
    text = date_str.lower()
    
    # Try Regex for "DD Month YYYY"
    # match 1-2 digits, space, word, space, 4 digits
    match = re.search(r'(\d{1,2})\s+([a-z]+)\s+(\d{4})', text)
    if match:
        day, month_name, year = match.groups()
        month = ro_months.get(month_name)
        if month:
            try:
                return datetime(int(year), month, int(day))
            except: pass
            
    # ISO Format fallback
    try:
        return datetime.fromisoformat(date_str)
    except: pass
    
    return None

def extract_date_from_url(url: str) -> Optional[datetime]:
    """
    Extracts date from URL slugs like /2025/12/29/ or /2025-12-29/.
    High confidence if found.
    """
    if not url: return None
    
    # Pattern 1: /YYYY/MM/DD/
    match_slug = re.search(r'/(\d{4})/(\d{1,2})/(\d{1,2})/', url)
    if match_slug:
        y, m, d = match_slug.groups()
        try:
             return datetime(int(y), int(m), int(d))
        except: pass

    # Pattern 2: YYYY-MM-DD
    match_iso = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', url)
    if match_iso:
         y, m, d = match_iso.groups()
         # Sanity check year
         if 2000 < int(y) < 2030:
             try:
                 return datetime(int(y), int(m), int(d))
             except: pass
             
    return None

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def gemini_discover_city_outlets(city: str, country: str, lat: float, lng: float, api_key: str) -> List[OutletCreate]:
    if not api_key: return []
    genai.configure(api_key=api_key)

    prompt = f"""
    You are a news outlet discovery expert. Try finding the townhall page of the {city}, {country} and see if there is information regarding the local media in {city}. For example, in "Sibiu", there is this page "https://www.sibiu.ro/sibiu/media"  which lists all media produced in the city.
    If you cannot find such a page, then find the top 15-20 most relevant local news outlets (Newspapers, TV Stations, Radio, Online Portals) based in or covering: {city}, {country}.
    Do not ignore national outlets if they are based in the same location: {city}, {country}
    Focus on finding and validating live Website URLs. Do not return outdated, non-loading or broken links. 
    After finding the outlets, assign a popularity score from 1 to 10 based on the outlet's reputation and reach.
    
    Return a strictly valid JSON list. Example:
    [
        {{ "name": "Monitorul de Cluj", "url": "https://www.monitorulcj.ro", "type": "Online", "popularity": 10, "focus": "Local" }},
        {{ "name": "Radio Cluj", "url": "http://radiocluj.ro", "type": "Radio", "popularity": 7, "focus": "Local and National" }}
    ]
    """
    
    print(f"DEBUG: Starting Gemini Discovery for {city}, {country}")
    model = genai.GenerativeModel('gemini-flash-latest')
    try:
        response = await model.generate_content_async(prompt, generation_config={"max_output_tokens": 4000})
        text = response.text.strip()
        print(f"DEBUG: Gemini response received. Length: {len(text)}")
        
        # Robust JSON finding using Regex
        import re
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            text = match.group(0)
            print("DEBUG: JSON block found.")
        else:
            print(f"DEBUG: No JSON block found in response: {text[:100]}...")
            return []
        
        try:
            data = json.loads(text)
            print(f"DEBUG: JSON parsed successfully. {len(data)} items.")
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON Parsed Error: {e}")
            # Try to fix common trailing comma issues or markdown
            return []
        
        def safe_int(val):
            try: return int(val)
            except: return 5

        outlets = [OutletCreate(
            name=d['name'], 
            city=city, 
            country_code="RO" if "Romania" in country else "XX",
            url=d.get('url'),
            type=d.get('type', 'Online'),
            popularity=safe_int(d.get('popularity', 5)),
            focus=d.get('focus', 'Local'),
            lat=lat,
            lng=lng
        ) for d in data]
        print(f"DEBUG: Processed {len(outlets)} outlets.")
        return outlets
    except Exception as e:
        print(f"DEBUG: Gemini Discovery Critical Error for {city}: {e}")
        import traceback
        traceback.print_exc()
        return []
        # Log raw text for debugging if available
        try: print(f"Raw Response: {response.text}") 
        except: pass
        return []

async def gemini_scrape_outlets(html_content: str, city: str, country: str, lat: float, lng: float, api_key: str, instructions: str = None) -> List[OutletCreate]:
    if not api_key: return []
    genai.configure(api_key=api_key)

    # Truncate HTML to avoid token limits (approx 30k chars is usually enough for structure)
    html_sample = html_content[:50000]

    prompt = f"""
    Analyze this HTML content from a website ({instructions or "General Analysis"}).
    
    Goal: Identify the News Outlet(s) associated with this page.
    
    Scenario A (Single Outlet): The website ITSELF is a news outlet (newspaper, blog, TV station).
    -> Return it as a single entry.
    
    Scenario B (Directory): The website contains a LIST of OTHER news outlets.
    -> Return the list of extracted outlets.
    
    Context: We are looking for media related to {city}, {country}.
    
    Return a JSON list:
    [
        {{ "name": "Outlet Name", "url": "https://full.url.com", "type": "Online" }}
    ]
    """
    
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        response = await model.generate_content_async([prompt, html_sample])
        text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return [OutletCreate(
            name=d['name'], 
            city=city, 
            country_code="RO" if "Romania" in country else "XX",
            url=d.get('url'),
            type=d.get('type', 'Online'),
            lat=lat,
            lng=lng
        ) for d in data]
    except ResourceExhausted:
         raise # Re-raise 429
    except Exception as e:
        print(f"Gemini Scrape Error: {e}")
        return []

@router.post("/outlets/discover_city", response_model=List[OutletRead])
async def discover_city_outlets(req: CityDiscoveryRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Finds outlets for a specific city.
    Checks DB first. If not found OR force_refresh is True, uses AI to discover.
    """
    existing = []
    print(f"DEBUG: Request for {req.city}, force={req.force_refresh}")
    if not req.force_refresh:
        result = await db.execute(select(NewsOutlet).where(NewsOutlet.city.ilike(req.city)))
        existing = result.scalars().all()
        print(f"DEBUG: Found {len(existing)} existing outlets in DB.")
        if existing:
            return existing
    
    # Auto-Discover
    print(f"Discovering outlets for city: {req.city}, {req.country} (Force: {req.force_refresh})")
    
    try:
        discovered = await gemini_discover_city_outlets(req.city, req.country, req.lat, req.lng, api_key=current_user.gemini_api_key)
    except ResourceExhausted:
         raise HTTPException(status_code=429, detail="AI Quota Exceeded. Please try again later.")
    except Exception as e:
        print(f"Discovery Error: {e}")
        # If we have existing data and discovery failed, return existing
        if existing: return existing
        return []

    saved_outlets = []
    
    # If refreshing, we might get duplicates. Only add new ones.
    # We re-fetch existing to be sure
    result = await db.execute(select(NewsOutlet).where(NewsOutlet.city.ilike(req.city)))
    current_db_outlets = result.scalars().all()
    current_urls = {o.url for o in current_db_outlets if o.url}
    current_names = {o.name.lower() for o in current_db_outlets}

    for disc in discovered:
        # Check duplicate by URL or Name
        if disc.url and disc.url in current_urls: continue
        if disc.name.lower() in current_names: continue
        
        db_outlet = NewsOutlet(
            name=disc.name,
            country_code="RO" if "Romania" in req.country or "RO" in req.country else "XX", 
            city=disc.city,
            lat=disc.lat,
            lng=disc.lng,
            url=disc.url,
            type=disc.type,
            popularity=disc.popularity,
            focus=disc.focus 
        )
        db.add(db_outlet)
        saved_outlets.append(db_outlet)
    
    if saved_outlets:
        await db.commit()
    
    # Return updated list
    result = await db.execute(select(NewsOutlet).where(NewsOutlet.city.ilike(req.city)))
    final_outlets = result.scalars().all()
    print(f"DEBUG: Returning {len(final_outlets)} outlets to frontend for {req.city}.")
    return final_outlets

class OutletUpdate(BaseModel):
    url: Optional[str] = None
    name: Optional[str] = None

@router.delete("/outlets/{outlet_id}")
async def delete_outlet(outlet_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await db.execute(select(NewsOutlet).where(NewsOutlet.id == outlet_id))
    outlet = result.scalars().first()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")
    
    await db.delete(outlet)
    await db.commit()
    return {"status": "deleted", "id": outlet_id}

@router.put("/outlets/{outlet_id}", response_model=OutletRead)
async def update_outlet(outlet_id: int, update_data: OutletUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await db.execute(select(NewsOutlet).where(NewsOutlet.id == outlet_id))
    outlet = result.scalars().first()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")
    
    if update_data.url is not None:
        outlet.url = update_data.url
    if update_data.name is not None:
        outlet.name = update_data.name
        
    await db.commit()
    await db.refresh(outlet)
    return outlet

@router.post("/outlets/import_from_url", response_model=List[OutletRead])
async def import_outlets_from_url(req: ImportUrlRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Scrapes a provided URL and uses AI to extract outlet information, saving it to the DB.
    """
    print(f"Importing for {req.city} from {req.url}")
    
    # 1. Fetch URL
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        async with httpx.AsyncClient(follow_redirects=True, timeout=15, headers=headers) as client:
            response = await client.get(req.url)
            response.raise_for_status()
            html_content = response.text
    except Exception as e:
        print(f"Fetch failed: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")

    # 2. Extract
    extracted = await gemini_scrape_outlets(html_content, req.city, req.country, req.lat, req.lng, api_key=current_user.gemini_api_key, instructions=req.instructions)
    
    # 3. Save
    saved_outlets = []
    for out in extracted:
        # Check if exists to avoid dupes? (Simple check: name + city)
        result = await db.execute(select(NewsOutlet).where(NewsOutlet.name == out.name, NewsOutlet.city == req.city))
        if result.scalars().first():
            continue # Skip duplicate
            
        db_outlet = NewsOutlet(
            name=out.name,
            country_code="RO" if "Romania" in req.country or "RO" in req.country else "XX",
            city=out.city,
            lat=out.lat,
            lng=out.lng,
            url=out.url,
            type=out.type or "Unknown", # Ensure type
            origin="manual",
            popularity=out.popularity,
            focus=out.focus
        )
        db.add(db_outlet)
        saved_outlets.append(db_outlet)
        
    if saved_outlets:
        await db.commit()
    
    # Return all outlets for city (including old ones)
    result = await db.execute(select(NewsOutlet).where(NewsOutlet.city.ilike(req.city)))
    return result.scalars().all()

@router.get("/outlets/cities/list", response_model=List[str])
async def list_cities_with_outlets(db: Session = Depends(get_db)):
    """Returns a list of distinct city names that have stored outlets."""
    result = await db.execute(select(distinct(NewsOutlet.city)))
    cities = result.scalars().all()
    return [c for c in cities if c]



# --- News Digest Agent ---
from bs4 import BeautifulSoup
from models import NewsDigest

class KeywordData(BaseModel):
    word: str
    importance: int # 1-100
    type: str 
    sentiment: str
    source_urls: Optional[List[str]] = [] # New: Links to specific source articles

class ArticleMetadata(BaseModel):
    title: str
    url: str
    source: str
    image_url: Optional[str] = None
    date_str: Optional[str] = None
    relevance_score: Optional[int] = 0
    scores: Optional[Dict[str, int]] = None # Detailed breakdown # New: Calculated score based on keyword overlap
    
class DigestResponse(BaseModel):
    digest: str
    articles: List[ArticleMetadata]
    analysis_source: Optional[List[KeywordData]] = []
    analysis_digest: Optional[List[KeywordData]] = []

class DigestSaveRequest(BaseModel):
    title: str
    category: str
    summary_markdown: str
    articles: List[ArticleMetadata]
    analysis_source: Optional[List[KeywordData]] = []
    analysis_digest: Optional[List[KeywordData]] = []

class DigestRead(BaseModel):
    id: int
    title: str
    category: str
    created_at: str

@router.get("/outlets/digests/saved", response_model=List[DigestRead])
async def get_saved_digests(db: Session = Depends(get_db)):
    """Returns list of saved digests."""
    result = await db.execute(select(NewsDigest).order_by(NewsDigest.created_at.desc()))
    digests = result.scalars().all()
    return [
        DigestRead(
            id=d.id,
            title=d.title,
            category=d.category,
            created_at=d.created_at.isoformat()
        ) for d in digests
    ]

class DigestDetail(BaseModel):
    id: int
    title: str
    category: str
    summary_markdown: str
    articles: List[ArticleMetadata]
    analysis_source: Optional[List[KeywordData]] = []
    analysis_digest: Optional[List[KeywordData]] = []
    created_at: str

@router.get("/outlets/digests/{id}", response_model=DigestDetail)
async def get_digest_detail(id: int, db: Session = Depends(get_db)):
    """Returns full details of a saved digest."""
    result = await db.execute(select(NewsDigest).where(NewsDigest.id == id))
    digest = result.scalars().first()
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    
    articles = []
    if digest.articles_json:
        try:
            raw_articles = json.loads(digest.articles_json)
            articles = [ArticleMetadata(**a) for a in raw_articles]
        except:
            pass
            
    analysis_source = []
    if digest.analysis_source:
        try:
            raw_src = json.loads(digest.analysis_source)
            analysis_source = [KeywordData(**k) for k in raw_src]
        except: pass

    analysis_digest = []
    if digest.analysis_digest:
        try:
            raw_dig = json.loads(digest.analysis_digest)
            analysis_digest = [KeywordData(**k) for k in raw_dig]
        except: pass

    return DigestDetail(
        id=digest.id,
        title=digest.title,
        category=digest.category,
        summary_markdown=digest.summary_markdown,
        articles=articles,
        analysis_source=analysis_source,
        analysis_digest=analysis_digest,
        created_at=digest.created_at.isoformat()
    )

@router.post("/outlets/digests/save")
async def save_digest(req: DigestSaveRequest, db: Session = Depends(get_db)):
    """Saves a generated digest."""
    db_digest = NewsDigest(
        title=req.title,
        category=req.category,
        summary_markdown=req.summary_markdown,
        articles_json=json.dumps([a.dict() for a in req.articles]),
        analysis_source=json.dumps([k.dict() for k in req.analysis_source]) if req.analysis_source else None,
        analysis_digest=json.dumps([k.dict() for k in req.analysis_digest]) if req.analysis_digest else None
    )
    db.add(db_digest)
    await db.commit()
    return {"status": "success", "id": db_digest.id}

class CityInfoResponse(BaseModel):
    population: str
    description: str
    ruling_party: str
    flag_url: Optional[str] = None
    city_native_name: Optional[str] = None
    city_phonetic_name: Optional[str] = None
    country_flag_url: Optional[str] = None
    country_english: Optional[str] = None
    country_native: Optional[str] = None
    country_phonetic: Optional[str] = None

@router.get("/outlets/city_info", response_model=CityInfoResponse)
async def get_city_info(city: str, country: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Fetches quick city stats using Gemini, with DB caching.
    """
    # 1. Check DB Cache
    stmt = select(CityMetadata).join(Country).where(
        CityMetadata.name == city, 
        (Country.name == country) | (Country.native_name == country)
    )
    stmt = select(CityMetadata).where(CityMetadata.name == city)
    result = await db.execute(stmt)
    cached_city = result.scalars().first()
    
    if cached_city:
        db_country_stmt = select(Country).where(Country.id == cached_city.country_id)
        res_c = await db.execute(db_country_stmt)
        db_country = res_c.scalars().first()
        
        if db_country:
            return CityInfoResponse(
                population=cached_city.population or "Unknown",
                description=cached_city.description or "",
                ruling_party=cached_city.ruling_party or "Unknown",
                flag_url=cached_city.flag_url,
                city_native_name=cached_city.native_name,
                city_phonetic_name=cached_city.phonetic_name,
                country_flag_url=db_country.flag_url,
                country_english=db_country.name,
                country_native=db_country.native_name,
                country_phonetic=db_country.phonetic_name
            )

    # 2. Not cached: Generate
    prompt = f"""
    Provide brief structured info about the city {city}, {country}.
    
    Instructions:
    1. **Country Metadata**: Identify the country's name in English, its Native Language Name (e.g. "România"), and its Phonetic Pronunciation (e.g. "ro-muh-nee-a").
    2. **City Metadata**: Identify the city's Native Name (e.g. "București") and Phonetic Pronunciation.
    3. **Flag**: Find a high-quality Wikimedia URL for the **COUNTRY's Flag** (SVG or PNG).
    4. **City Stats**: Population, 1-sentence description, and Mayor's Party.
    
    Return strictly JSON:
    {{
      "population": "approx X (Year)",
      "description": "1-sentence summary (max 15 words).",
      "ruling_party": "Mayor's Party",
      "flag_url": "URL to City Coat of Arms (optional, can be null)",
      "city_native_name": "București",
      "city_phonetic_name": "/bukuˈreʃtʲ/",
      "country_flag_url": "URL to COUNTRY Flag (Wikimedia SVG preferred)",
      "country_english": "Romania",
      "country_native": "România",
      "country_phonetic": "/ro.mɨˈni.a/" 
    }}
    """
    
    try:
        api_key = current_user.gemini_api_key
        if not api_key: 
            return CityInfoResponse(population="Unknown", description="API Key needed.", ruling_party="Unknown")
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-flash-latest')
        response = await model.generate_content_async(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        
        # 3. Save to DB
        c_eng = data.get('country_english', country)
        stmt_c = select(Country).where(Country.name == c_eng)
        res_c = await db.execute(stmt_c)
        db_country = res_c.scalars().first()
        
        if not db_country:
            db_country = Country(
                name=c_eng,
                native_name=data.get('country_native'),
                phonetic_name=data.get('country_phonetic'),
                flag_url=data.get('country_flag_url')
            )
            db.add(db_country)
            await db.commit()
            await db.refresh(db_country)
        else:
            if not db_country.flag_url and data.get('country_flag_url'):
                db_country.flag_url = data.get('country_flag_url')
                await db.commit()

        db_city = CityMetadata(
            name=city,
            native_name=data.get('city_native_name'),
            phonetic_name=data.get('city_phonetic_name'),
            country_id=db_country.id,
            population=data.get('population'),
            description=data.get('description'),
            ruling_party=data.get('ruling_party'),
            flag_url=data.get('flag_url')
        )
        db.add(db_city)
        await db.commit()

        return CityInfoResponse(**data)

    except Exception as e:
        print(f"City Info Error: {e}")
        return CityInfoResponse(population="Unknown", description=f"Automated data unavailable.", ruling_party="Unknown")

class DigestRequest(BaseModel):
    outlet_ids: List[int]
    category: str
    timeframe: Optional[str] = "24h" # 24h, 3days, 1week

async def robust_fetch(client, url):
    try:
        response = await client.get(url)
        if response.status_code in [301, 302, 307, 308]:
             response = await client.get(response.headers["Location"])
        return response
    except Exception as e:
        print(f"Fetch error {url}: {e}")
        return None

async def smart_scrape_outlet(outlet: NewsOutlet, category: str, timeframe: str = "24h") -> dict:
    """
    Fetches content from an outlet, intelligently navigating to the category page if possible.
    Returns structured article data and raw text for AI.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=20, headers=headers) as client:
        # 1. Fetch Homepage
        print(f"[{outlet.name}] Fetching homepage: {outlet.url}")
        resp = await robust_fetch(client, outlet.url)
        if not resp or resp.status_code != 200:
            return {"text": "", "articles": []}

        final_url = outlet.url
        # Limit HTML size to prevent CPU blocking on huge pages
        html = resp.text[:200000] 
        soup = BeautifulSoup(html, 'html.parser')

        # 2. Try to find Category Link (if category is specific)
        if category.lower() not in ["general", "all", "headline"]:
            # naive search for link text or href
            cat_link = None
            term = category.lower()
            # Multi-language mappings for Category navigation
            # EN, RO, ES, FR, DE, IT
            mappings = {
                "politics": [
                    "politics", "politic", "politica", "politique", "politik", 
                    "administratie", "administration", "gobierno", "regierung", "governo"
                ],
                "sports": [
                    "sport", "sports", "deporte", "deportes", "fotbal", "football", "soccer", "futbol"
                ],
                "economy": [
                    "economy", "business", "financial", "economie", "economia", "wirtschaft", "finanzen", 
                    "bani", "money", "dinero", "argent", "geld"
                ],
                "social": [
                    "social", "society", "societate", "sociedad", "société", "gesellschaft", "società", 
                    "community", "comunitate", "comunidad"
                ],
                "culture": [
                    "culture", "cultura", "kultur", "arts", "life", "lifestyle", "monden", "entertainment", 
                    "unterhaltung", "magazin", "magazine"
                ]
            }
            
            # Add the requested category itself as a primary term
            search_terms = mappings.get(term, [])
            if term not in search_terms:
                search_terms.insert(0, term)
            
            for t in search_terms:
                link_tag = soup.find('a', string=lambda text: text and t in text.lower()) or \
                           soup.find('a', href=lambda href: href and t in href.lower())
                if link_tag:
                    href = link_tag.get('href')
                    if href:
                        if href.startswith("/"):
                            # Handle relative URLs
                            import urllib.parse
                            final_url = urllib.parse.urljoin(outlet.url, href)
                        elif href.startswith("http"):
                            final_url = href
                        
                        print(f"[{outlet.name}] Found category link: {final_url}")
                        cat_resp = await robust_fetch(client, final_url)
                        if cat_resp and cat_resp.status_code == 200:
                            html = cat_resp.text[:200000] # Limit size
                            soup = BeautifulSoup(html, 'html.parser')
                        break

        # 2. Construct Potential Category URLs (Active Discovery)
    # Instead of hoping to find a link on the homepage, we try to guess the category URL.
    # Most RO sites use /politica, /administratie, /sport, etc.
    outlet_url = outlet.url # Use the base URL for construction
    urls_to_scrape = [outlet_url] # Always scrape homepage
    
    # Get relevant keywords for the category
    cat_keywords = mappings.get(category.lower(), [])
    
    # Try to construct specific paths (limit to 2 most likely to save time)
    # e.g. site.ro/politica or site.ro/category/politica
    for kw in cat_keywords[:2]:
        # Clean double slashes
        base = outlet_url.rstrip("/")
        urls_to_scrape.append(f"{base}/{kw}")
        urls_to_scrape.append(f"{base}/stiri/{kw}") # Common pattern
        urls_to_scrape.append(f"{base}/sectiune/{kw}") # Another pattern

    print(f"DEBUG: Active Scraping for {outlet.name}: {urls_to_scrape}")
    
    # NEW: Dictionary to aggregate metadata by URL
    candidates_map = {} 
    
    # 3. Scrape All Candidates
    import asyncio
    
    # Helper to fetch and parse single URL (placeholder)
    async def fetch_and_parse(target_url):
         try: pass
         except: pass

    # Refactored Loop to process multiple URLs
    combined_content = ""
    
    for i, target_url in enumerate(urls_to_scrape):
        # Limit active scraping to avoid timeouts
        if i > 3: break 
        
        try:
            print(f"  -> Fetching: {target_url}")
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client: # Reduced timeout for sub-pages
                resp = await client.get(target_url, headers=headers)
                if resp.status_code != 200: continue
                
                # Parse
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Extract Text (Append to combined)
                text = soup.get_text(separator=' ', strip=True)
                # Truncate to avoid exploding token context
                combined_content += f"\n--- SOURCE: {outlet.name} [{target_url}] ---\n{text[:10000]}\n"
                
                # Extract Links (Article Discovery)
                # Reuse the existing article extraction logic?
                # The original code had a big block for "Find Articles".
                # We need to run that block on 'soup'.
                
                # ... (Logic below is the original article extraction, customized for the loop)
                
                # Find all potential links
                links = soup.find_all('a', href=True)
                
                for a in links:
                    href = a['href']
                    raw_title = a.get_text(strip=True)
                    
                    # Normalize URL
                    if not href.startswith('http'):
                        full_url = outlet_url.rstrip('/') + '/' + href.lstrip('/')
                    else:
                        full_url = href
                    
                    # Deduplication logic (handled via candidates_map later)
                    # if full_url in seen_urls: continue
                    
                    # Basic Validation
                    if len(raw_title) < 5: continue
                    
                    # Content/Allowlist Filter
                    # (Reusing mappings/blacklist logic)
                    is_relevant = False
                    
                    # 1. URL Keywords
                    if any(k in full_url.lower() for k in cat_keywords): is_relevant = True
                    # 2. Title Keywords
                    if any(k in raw_title.lower() for k in cat_keywords): is_relevant = True
                    # 3. Date check (simple slug)
                    if "2026" in full_url or "2025" in full_url: is_relevant = True
                    
                    # Blacklist
                    BLACKLIST_TERMS = [
                        # Meta-pages (Contact, Terms, Privacy)
                        "contact", "terms", "privacy", "cookies", "gdpr", "politica-confidentialitate", "despre", "about", 
                        "redactia", "echipa", "team", "publicitate", "advertising", "cariere", "careers", 
                        "politica-editoriala", "caseta-redactionala", "termeni", "conditii",
                        # Food/Recipes
                        "recipe", "retet", "receta", "recette", "rezept", "ricett", "mancare", "food", "kitchen", "bucatarie", "essen", "cucina",
                        # Horoscope/Astrology
                        "horoscop", "horoscope", "horoskop", "zodiac", "zodiaque", "astrology", "astro",
                        # Gossip/Tabloid
                        "can-can", "cancan", "paparazzi", "gossip", "tabloid", "klatsch", "potins", "monden", "diva", "vedete", "vip",
                        # Games/Quizzes
                        "game", "jocuri", "juego", "jeu", "spiele", "gioc", "quiz", "crossword", "sudoku", "rebus",
                        # Lifestyle/Shopping
                        "lifestyle", "fashion", "moda", "mode", "shop", "magazin-online", "store", "oferte"
                    ]
                    if any(b in full_url.lower() for b in BLACKLIST_TERMS): is_relevant = False
                    
                    if is_relevant:
                        # Attempt Date Parsing from Title (Heuristic for Timestamp Links)
                        found_date_str = None
                        import re
                        # Match YYYY-MM-DD or DD.MM.YYYY or "04 Ian"
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2})|(\d{1,2}\.\d{2}\.\d{4})|(\d{1,2}\s+(?:Ian|Feb|Mar|Apr|Mai|Iun|Iul|Aug|Sep|Oct|Nov|Dec|Jan))', raw_title, re.IGNORECASE)
                        
                        if date_match:
                             match_str = date_match.group(0)
                             try:
                                 if '-' in match_str: found_date_str = match_str
                                 elif '.' in match_str:
                                      d, m, y = match_str.split('.')
                                      found_date_str = f"{y}-{m}-{d}"
                             except: pass

                        # Extract from URL capability
                        def extract_date_from_url(url):
                            # Supports YYYY/MM/DD, YYYY-MM-DD, YYYY.MM.DD
                            match = re.search(r'(\d{4})[./-](\d{2})[./-](\d{2})', url)
                            if match:
                                try:
                                    # Normalize to dashes for strptime if needed, or just use parts
                                    y, m, d = match.groups()
                                    return datetime(int(y), int(m), int(d))
                                except ValueError: pass
                            return None
                        
                        url_date_obj = extract_date_from_url(full_url)
                        url_date_str = url_date_obj.strftime("%Y-%m-%d") if url_date_obj else None
                        
                        # NEW: Context Lookbehind (Parent Text)
                        # Helps when date is "02.01.2026 - Title" plain text before anchor
                        context_date_str = None
                        try:
                             parent_text = a.parent.get_text(separator=' ', strip=True)
                             # Look for DD.MM.YYYY, DD-MM-YYYY, DD Month YYYY
                             # Using a slightly looser regex to catch "2 Ianuarie 2026" etc
                             ctx_match = re.search(r'(\d{1,2})[.\/-](\d{1,2})[.\/-](\d{4})|(\d{1,2})\s+(?:Ian|Feb|Mar|Apr|Mai|Iun|Iul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})', parent_text, re.IGNORECASE)
                             
                             if ctx_match:
                                  # Parse if match
                                  # This is a bit complex to normalize perfectly without a huge heavy libs, 
                                  # but let's try to grab the YYYY part at least to validate 'freshness'
                                  # Or just extract the string for now.
                                  # If it matches strict DD.MM.YYYY:
                                   m_str = ctx_match.group(0)
                                   # quick normalize dot
                                   if '.' in m_str:
                                        d, m, y = m_str.split('.')
                                        context_date_str = f"{y}-{m}-{d}"
                        except: pass

                        # Merge/Update Logic
                        existing = candidates_map.get(full_url)
                        
                        if existing:
                             # Heuristic: if found_date_str is present in raw_title, this 'title' is likely just a timestamp
                             is_timestamp_only = (found_date_str is not None and len(raw_title) < 20)
                             
                             if not is_timestamp_only and len(raw_title) > len(existing.title):
                                 existing.title = raw_title
                                 
                             # Update Date if missing
                             if not existing.date_str:
                                 if url_date_str: existing.date_str = url_date_str
                                 elif context_date_str: existing.date_str = context_date_str
                                 elif found_date_str: existing.date_str = found_date_str
                        else:
                             # Create New
                             # Priority: URL > Context (Parent) > Title Match
                             final_date_str = url_date_str or context_date_str or found_date_str
                             
                             art = ArticleMetadata(
                                 source=outlet.name,
                                 title=raw_title,
                                 url=full_url,
                                 date_str=final_date_str
                             )
                             candidates_map[full_url] = art
                        
        except Exception as e:
            print(f"Error scraping {target_url}: {e}")
            continue

    # Finalize: Convert values to list
    all_extracted_articles = list(candidates_map.values())

    # Return aggregated result (matching the expected dict structure)
    return {
        "text": combined_content,
        "articles": all_extracted_articles
    }

async def generate_keyword_analysis(text: str, category: str, current_user: User) -> List[KeywordData]:
    """Reusable function to analyze text and extract keywords/sentiment."""
    if not text:
        return []

    api_key = current_user.gemini_api_key
    if not api_key: return []
    genai.configure(api_key=api_key)

    # Truncate to avoid context limits if very large
    text_sample = text[:30000]

    prompt = f"""
    Analyze the following news text specifically for the category '{category}'. IGNORE topics unrelated to {category}.
    Extract the Top 100 most significant keywords/terms that are strictly grounded in the text.
    
    Instructions:
    1. **Strict Category Relevance**: Only include terms directly related to "{category}". For example, if category is "Politics", exclude "Football" or "Celebrity Gossip" unless directly political.
    2. **Entities**: Identify specific Persons, Locations, Organizations, and Events (e.g., "Mayor Boc", "Cluj-Napoca", "Untold Festival").
    3. **Concepts**: Identify key themes or objects (e.g., "Budget", "Traffic", "Pollution").
    4. **Filter**: EXCLUDE generic stopwords (and, the, if, but, etc.) and generic news terms (reporter, news, article).
    5. **Metadata**:
        - **Importance**: Score 1-100 based on relevance/frequency.
        - **Type**: Person, Location, Organization, Concept, Event, Object.
        - **Sentiment**: Detect the context/emotion associated with this specific term in the text. 
          Examples: Positive, Negative, Balanced, Accusatory, Praise, Fearful, Controversial.
    
    Return strictly a JSON list:
    [
        {{ "word": "Emil Boc", "importance": 95, "type": "Person", "sentiment": "Positive" }},
        {{ "word": "Traffic", "importance": 80, "type": "Concept", "sentiment": "Negative" }}
    ]

    Text to Analyze:
    {text_sample}
    """

    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        response = await model.generate_content_async(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        
        results = []
        for item in data:
            results.append(KeywordData(
                word=item.get('word', 'Unknown'),
                importance=int(item.get('importance', 50)),
                type=item.get('type', 'Concept'),
                sentiment=item.get('sentiment', 'Neutral')
            ))
        
        # Sort by importance descending
        results.sort(key=lambda x: x.importance, reverse=True)
        return results
    except ResourceExhausted:
         raise HTTPException(status_code=429, detail="AI Quota Exceeded. Please try again later.")
    except Exception as e:
        print(f"Analysis Failed: {e}")
        return []

# --- Digest Management Models ---
class DigestCreate(BaseModel):
    title: str
    category: str
    summary_markdown: str
    articles: List[Dict[str, Any]] # Will be serialized to JSON
    analysis_source: Optional[List[Dict[str, Any]]] = None # Will be serialized to JSON
    analysis_digest: Optional[List[Dict[str, Any]]] = None

class DigestRead(DigestCreate):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Digest Endpoints ---

@router.post("/digests", response_model=DigestRead)
async def save_digest(
    digest: DigestCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save a generated digest to the database."""
    import json
    
    db_digest = NewsDigest(
        user_id=current_user.id,
        title=digest.title,
        category=digest.category,
        summary_markdown=digest.summary_markdown,
        articles_json=json.dumps(digest.articles),
        analysis_source=json.dumps(digest.analysis_source) if digest.analysis_source else None,
        analysis_digest=json.dumps(digest.analysis_digest) if digest.analysis_digest else None
    )
    db.add(db_digest)
    await db.commit()
    await db.refresh(db_digest)
    
    # Clean return (deserialize for response)
    return DigestRead(
        id=db_digest.id,
        title=db_digest.title,
        category=db_digest.category,
        summary_markdown=db_digest.summary_markdown,
        articles=json.loads(db_digest.articles_json),
        analysis_source=json.loads(db_digest.analysis_source) if db_digest.analysis_source else [],
        created_at=db_digest.created_at
    )

@router.get("/digests", response_model=List[DigestRead])
async def list_digests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all saved digests for the current user."""
    import json
    stmt = select(NewsDigest).where(NewsDigest.user_id == current_user.id).order_by(NewsDigest.created_at.desc())
    result = await db.execute(stmt)
    digests = result.scalars().all()
    
    # Manual mapping to handle JSON deserialization
    return [
        DigestRead(
            id=d.id,
            title=d.title,
            category=d.category,
            summary_markdown=d.summary_markdown,
            articles=json.loads(d.articles_json) if d.articles_json else [],
            analysis_source=json.loads(d.analysis_source) if d.analysis_source else [],
            created_at=d.created_at
        ) for d in digests
    ]

@router.delete("/digests/{digest_id}")
async def delete_digest(
    digest_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a saved digest."""
    stmt = select(NewsDigest).where(NewsDigest.id == digest_id, NewsDigest.user_id == current_user.id)
    result = await db.execute(stmt)
    digest = result.scalar_one_or_none()
    
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
        
    await db.delete(digest)
    await db.commit()
    return {"status": "success", "message": "Digest deleted"}

# --- AI RELEVANCE CHECK ---
async def verify_relevance_with_ai(title: str, url: str, category: str, api_key: str) -> bool:
    """
    Uses Gemini to strictly verify if an article is relevant to the category.
    Returns True if relevant, False otherwise.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""
        Analyze if the following news article is relevant to the category '{category}'.
        Title: {title}
        URL: {url}
        
        Rules:
        1. Context matters. "Water cutoff" is NOT Politics. "Mayor announces water cutoff" IS Politics/Administration.
        2. "Traffic accident" is NOT Politics/Administration.
        3. If it is a generic utility announcement, specific crime report (robbery), or gossip, return FALSE.
        4. If it is about city council, mayor, public spending, laws, healthcare policy, education policy, infrastructure projects, return TRUE.
        
        Respond with exactly ONE word: TRUE or FALSE.
        """
        
        response = await model.generate_content_async(prompt)
        ans = response.text.strip().upper()
        return "TRUE" in ans
    except Exception as e:
        print(f"AI Verification Failed: {e}")
        return True # Fail open to avoid dropping potentially good articles if API fails

async def extract_date_with_ai(html_content: str, url: str, api_key: str) -> Optional[str]:
    """
    Uses Metadata tags first, then Gemini to extract the publication date from the article HTML.
    Returns YYYY-MM-DD string or None.
    """
    try:
        # 1. Metadata Probe (Deterministic & Fast)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Candidate tags
        meta_candidates = [
            {'property': 'article:published_time'},
            {'property': 'og:published_time'},
            {'name': 'date'},
            {'name': 'pubdate'},
            {'name': 'original-publish-date'},
            {'itemprop': 'datePublished'}
        ]
        
        for attr in meta_candidates:
            tag = soup.find('meta', attr)
            if tag and tag.get('content'):
                raw_date = tag['content']
                # Parse ISO format commonly found in meta (e.g. 2026-01-04T12:00:00+02:00)
                # Use simplified regex for YYYY-MM-DD
                match = re.search(r'(\d{4}-\d{2}-\d{2})', raw_date)
                if match:
                    print(f"  -> Metadata Hit ({attr}): {match.group(1)}")
                    return match.group(1)

        # 2. AI Fallback
        genai.configure(api_key=api_key)
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Truncate HTML to header/metadata/first few paragraphs to save tokens
        # Usually date is in the first 3000 chars
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
        return ans
    except Exception as e:
        print(f"AI Date Extraction Failed: {e}")
        return None

@router.post("/outlets/digest", response_model=DigestResponse)
async def generate_digest(req: DigestRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Aggregates news, generates summary, and performs DUAL analysis (Sources + Digest).
    """
    # 1. Fetch Outlets
    stmt = select(NewsOutlet).where(NewsOutlet.id.in_(req.outlet_ids))
    result = await db.execute(stmt)
    outlets = result.scalars().all()
    
    if not outlets:
         raise HTTPException(status_code=400, detail="No valid outlets selected")

    # 2. Parallel Smart Scrape
    print(f"Digest: Smart scraping {len(outlets)} outlets for '{req.category}' within {req.timeframe}...")
    scrape_tasks = [smart_scrape_outlet(o, req.category, req.timeframe) for o in outlets]
    scrape_results = await asyncio.gather(*scrape_tasks)
    
    combined_text = "\\n".join([r['text'] for r in scrape_results])
    all_articles = []
    for r in scrape_results:
        all_articles.extend(r['articles'])
    
    # 3. Parallel Processing: Source Analysis & Table Generation
    print("Digest: Starting Source Analysis & Table Generation...")
    
    # Task A: Analyze SOURCES (Raw Content) - Keep this for keyword extraction
    async def analyze_sources_task():
        # Inject Category for relevance
        results = await generate_keyword_analysis(combined_text, req.category, current_user)
        
        # Post-process: Map to specific source URLs purely by simplified text matching
        final_results = []
        for kw in results:
            kw.source_urls = []
            
            # 1. Strict Source Verification
            # Keyword must appear in the article title or match the URL content
            match_found = False
            for article in all_articles:
                # Use title and URL for matching since we don't store full text in metadata object
                if kw.word.lower() in article.title.lower() or kw.word.lower() in article.url.lower():
                     if article.url and article.url not in kw.source_urls:
                         kw.source_urls.append(article.url)
                         match_found = True
            
            # 2. Ghost Filter: If no sources contain this keyword, discard it.
            if match_found:
                 final_results.append(kw)
        
        return final_results

    # Execute Analysis Task
    t_source_analysis = asyncio.create_task(analyze_sources_task())
    analysis_source = await t_source_analysis
    
    # --- TABLE GENERATION (Replaces Digest) ---
    
    # 1. Relevance Scoring (Strict 3-Factor)
    SUSPICIOUS_TERMS = [
        "recipe", "retet", "receta", "recette", "rezept", "ricett", "mancare", "food", "kitchen", "bucatarie", "essen", "cucina",
        "horoscop", "horoscope", "horoskop", "zodiac", "zodiaque", "astrology",
        "can-can", "cancan", "paparazzi", "gossip", "tabloid", "klatsch", "potins", "cookie", "gdpr", "privacy", "termeni", "conditii"
    ]
    BLOCKED_DOMAINS = ["google.com", "apple.com", "youronlinechoices", "facebook.com", "twitter.com", "instagram.com", "tiktok.com", "youtube.com"]

    # Map articles to outlets for the table
    outlet_articles_map = {o.name: [] for o in outlets}

    # 1. Processing & Scoring
    filtered_articles = [] # Initialize list

    
    # 1. Processing & Scoring
    filtered_articles = [] # Final list
    candidates_for_ai = [] # Tuples of (article, task)
    
    # Pre-scoring loop
    for article in all_articles:
        # SPAM BLOCK
        # SPAM BLOCK
        if any(d in article.url for d in BLOCKED_DOMAINS): continue
        # CATEGORY BLOCK
        if "/category/" in article.url or "/page/" in article.url or "/tag/" in article.url or "/eticheta/" in article.url: continue

        # SCORING
        # FACTOR 1: TOPIC (MAX ~90 pts)
        topic_score = 0
        title_lower = article.title.lower()
        url_lower = article.url.lower()
        
        # Check against keywords extracted from Source/Digest Analysis
        if analysis_source:
             for kw in analysis_source:
                  if kw.word.lower() in title_lower or kw.word.lower() in url_lower:
                       topic_score += 40 # Boost for matching analyzed keywords
                       break # Cap at one match to avoid inflation
        
        # Simple heuristic for category matching if keywords fail
        if req.category.lower() in title_lower or req.category.lower() in url_lower:
            topic_score += 30
            
        # Contextual URL Boost (e.g. /politica/ in URL)
        cat_stem = req.category.lower()[:4] # "poli" for politics
        if f"/{cat_stem}" in url_lower:
             topic_score += 20

        # --- NOISE PENALTY ---
        NOISE_TERMS = [
            "apa calda", "apa rece", "intrerupere", "avarie", "curent", "electricitate",
            "trafic", "restrictii", "accident", "incendiu", "minor", "program",
            "meteo", "vremea", "prognoza", "cod galben", "cod portocaliu"
        ]
        if req.category.lower() not in ["local", "general", "all"]:
             if any(n in title_lower for n in NOISE_TERMS):
                 topic_score -= 50 # Heavier penalty

        # Penalize Off-Topic
        if any(term in title_lower for term in SUSPICIOUS_TERMS) or any(term in url_lower for term in SUSPICIOUS_TERMS):
             topic_score -= 100 

        # FACTOR 2: GEOGRAPHY (35 pts) - Kept for internal logic/sorting, removed from UI
        geo_score = 0
        target_cities = {o.city.lower() for o in outlets}
        if any(c in title_lower or c in url_lower for c in target_cities):
             geo_score = 35
        else:
             source_outlet = next((o for o in outlets if o.name == article.source), None)
             if source_outlet: geo_score = 35 

        # FACTOR 3: DATE (30 pts)
        date_score = 0
        if article.date_str:
             date_score = 30
        else:
             date_score = 10 
        
        # Remove Geo Score from Total (User Confusion Fix)
        # total_score = topic_score + geo_score + date_score
        total_score = topic_score + date_score
        article.relevance_score = int(total_score)
        article.scores = {"topic": topic_score, "geo": geo_score, "date": date_score}
        
        # LOGIC:
        # 1. Must have valid Date (score >= 30) AND Topic Score >= 20 (lowered to allow AI to decide)
        # 2. If it passes AI check, it gets in.
        
        if date_score >= 30 and topic_score >= 20:
            # Candidate for AI
            candidates_for_ai.append(article)
        elif topic_score >= 20 and date_score < 30:
            # AI DATE RESCUE MISSION
            # Relevant topic, but missing date. Try to rescue it.
            # (Runs for any topic >= 20, even if date check failed)
            try:
                 print(f"Rescuing Date for: {article.title}")
                 # We need a client. We can create one or reuse. Creating new for simplicity here since it's sporadic.
                 async with httpx.AsyncClient() as client:
                      resp = await client.get(article.url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                      if resp.status_code == 200:
                           rescued_date = await extract_date_with_ai(resp.text, article.url, current_user.gemini_api_key)
                           if rescued_date:
                                print(f"  -> Rescued! Found: {rescued_date}")
                                article.date_str = rescued_date
                                # Bump Score
                                # article.score does not exist (typo), removed to fix crash
                                article.relevance_score += 20
                                article.scores['date'] = 30
                                # Now it qualifies for AI verification or basic inclusion
                                candidates_for_ai.append(article)
                           else:
                                # Failed Rescue, still include as fallback if topic is valid
                                filtered_articles.append(article)
                      else:
                           filtered_articles.append(article)
            except Exception as e:
                 print(f"Rescue Failed: {e}")
                 filtered_articles.append(article)

        elif article.relevance_score > 30 and topic_score > 10:
             # Fallback for "Decently High Score" but maybe weak on specific keywords
             filtered_articles.append(article)

    # Batch AI Verification
    if candidates_for_ai:
        print(f"Verifying {len(candidates_for_ai)} articles with AI...")
        tasks = []
        for art in candidates_for_ai:
             tasks.append(verify_relevance_with_ai(art.title, art.url, req.category, current_user.gemini_api_key))
        
        results = await asyncio.gather(*tasks)
        
        for art, is_relevant in zip(candidates_for_ai, results):
            if is_relevant:
                # PASSED AI
                filtered_articles.append(art)
            else:
                print(f"AI Rejected: {art.title}")
    
    # Mapping
    outlet_articles_map = {o.name: [] for o in outlets}
    for article in filtered_articles:
        if article.source in outlet_articles_map:
            outlet_articles_map[article.source].append(article)

    # 2. Build HTML Table (Dark Mode Optimized)
    # REMOVED LOC COLUMN
    table_html = f"<h1 style='color: #e2e8f0; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; margin-bottom: 20px;'>Deep Analysis: {req.category} ({req.timeframe})</h1>"
    
    for outlet in outlets:
        articles = outlet_articles_map.get(outlet.name, [])
        if not articles: continue # Skip empty outlets to save space
        
        articles.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Outlet Header
        table_html += f"""
        <div style="margin-top: 32px; margin-bottom: 16px; border-bottom: 1px solid #334155; padding-bottom: 8px;">
            <h3 style="margin: 0; font-size: 1.4rem; color: #f8fafc;">
                <a href="{outlet.url}" target="_blank" style="color: #60a5fa; text-decoration: none; font-weight: bold;">{outlet.name}</a>
                <span style="color: #94a3b8; font-size: 1rem; font-weight: normal; margin-left: 10px;">({outlet.city})</span>
            </h3>
        </div>
        """
            
        # Table Header (NO LOC)
        table_html += """
        <table style="width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.95rem; margin-bottom: 24px; border: 1px solid #334155; border-radius: 6px; overflow: hidden;">
            <thead style="background-color: #1e293b; color: #e2e8f0;">
                <tr>
                    <th style="padding: 12px 16px; text-align: left; font-weight: 600; border-bottom: 1px solid #334155;">Score</th>
                    <th style="padding: 12px 16px; text-align: center; font-weight: 600; border-bottom: 1px solid #334155;">Date</th>
                    <th style="padding: 12px 16px; text-align: center; font-weight: 600; border-bottom: 1px solid #334155;">Topic</th>
                    <th style="padding: 12px 16px; text-align: left; font-weight: 600; border-bottom: 1px solid #334155;">Article</th>
                </tr>
            </thead>
            <tbody style="background-color: #0f172a;">
        """
        
        for art in articles:
            s = art.scores
            
            # Icons & Text
            date_icon = "✅" if s['date'] >= 30 else "⚠️"
            date_display = f"{date_icon} {art.date_str}" if art.date_str else f"{date_icon} N/A"
            
            # Topic Display Logic
            # Check if this article was in the "AI Verified" batch
            # We don't have a direct flag on the object unless we add it, but we can infer from score/logic
            # Start with basic score display
            ai_status = "🔴" # Default: Heuristic only
            if art in candidates_for_ai: # If it was a candidate (implies it passed pre-filter)
                 # If it's in the final list, it Passed AI (or AI failed closed to True)
                 ai_status = "🤖"
            
            topic_display = f"{ai_status} {s['topic']}"
            
            # Score Styling
            if art.relevance_score > 80:
                score_bg = "#052e16" # Dark Green
                score_text = "#4ade80" # Bright Green
                score_border = "#15803d"
            elif art.relevance_score > 50:
                score_bg = "#422006" # Dark Yellow/Brown
                score_text = "#facc15" # Bright Yellow
                score_border = "#a16207"
            else:
                score_bg = "#450a0a" 
                score_text = "#f87171" 
                score_border = "#b91c1c"
            
            score_badge = f"""
            <span style="display: inline-block; background-color: {score_bg}; color: {score_text}; border: 1px solid {score_border}; padding: 4px 8px; border-radius: 6px; font-weight: bold; min-width: 40px; text-align: center;">
                {art.relevance_score}
            </span>
            """
            
            title_color = "#f1f5f9"
            
            table_html += f"""
                <tr style="border-bottom: 1px solid #1e293b;">
                    <td style="padding: 10px 16px; border-bottom: 1px solid #1e293b;">{score_badge}</td>
                    <td style="padding: 10px 16px; text-align: center; border-bottom: 1px solid #1e293b; font-size: 0.9rem; color: #cbd5e1;">{date_display}</td>
                    <td style="padding: 10px 16px; text-align: center; border-bottom: 1px solid #1e293b; font-size: 0.9rem; color: #cbd5e1;">{topic_display}</td>
                    <td style="padding: 10px 16px; border-bottom: 1px solid #1e293b;">
                        <a href="{art.url}" target="_blank" style="display: block; color: {title_color}; text-decoration: none; font-size: 1rem; font-weight: 500; line-height: 1.4; transition: color 0.2s;">
                           <span style="border-bottom: 1px dotted #94a3b8;">{art.title}</span> <span style="font-size: 0.8em; text-decoration: none;">🔗</span>
                        </a>
                        <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px; font-family: monospace;">{art.url[:80]}{'...' if len(art.url) > 80 else ''}</div>
                    </td>
                </tr>
            """
        
        table_html += "</tbody></table>"

    digest_md = table_html # Return HTML as the 'markdown' response
    analysis_digest = [] # No digest analysis needed since we didn't generate one
    
    # 3. Construct Response
    return DigestResponse(
        digest=digest_md,
        analysis_source=analysis_source,
        analysis_digest=analysis_digest,
        articles=[a.dict() for a in all_articles] # Serialize Pydantic models
    )

# --- Analysis / Playground ---

class AnalysisRequest(BaseModel):
    text: str

@router.post("/outlets/analyze", response_model=List[KeywordData])
async def analyze_digest_text(req: AnalysisRequest, current_user: User = Depends(get_current_user)):
    """
    Direct analysis endpoint (fallback/manual).
    """
    return await analyze_text_with_gemini(req.text, api_key=current_user.gemini_api_key)

