import os
import time
from datetime import datetime
import json
import re # Added for regex parsing
import httpx
import google.generativeai as genai
from bs4 import BeautifulSoup
import html # For escaping content in f-strings
import traceback # Debugging
import asyncio # Added for digest parallel requests
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import select, distinct
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from database import AsyncSessionLocal
from models import NewsOutlet, User, Country, CityMetadata, ScraperRule, NewsDigest, SpamFeedback
from dependencies import get_current_user, get_db
import scraper_engine # New Import

from datetime import datetime, timedelta
import re
import secrets
import string


# Common Headers to bypass simple bot protections
ROBUST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,uk;q=0.8",
    "Referer": "https://www.google.com/",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
}

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
    lung: Optional[float] = 0.0
    instructions: Optional[str] = None

# --- Constants ---

POLITICS_OPERATIONAL_DEFINITION = """
Politics label spec (operational)
Label name: POLITICS

Core criterion:
Assign POLITICS if the primary focus of the article is power, governance, or collective decision-making carried out by political institutions/actors, or the processes that select/control them.
“Primary focus” = the main story would still be the same if you removed all non-political details; politics is not just a cameo.

Include if ANY of these is the main subject:
A) Government & institutions (domestic)
- Executive actions: cabinet decisions, ministries, agencies, regulators acting in official capacity
- Legislature: bills, votes, committees, parliamentary negotiations
- Public administration: government programs, budgets, procurement policy (not company-specific business news)
- Local government: mayors, councils, regional authorities, public service governance

B) Elections & party politics
- Elections, campaigns, polling, debates, candidate selection, coalition talks
- Party leadership, internal party conflicts when politically consequential
- Political strategy, messaging, endorsements

C) Public policy (substance + debate)
- Policy proposals, reforms, regulation, taxation, welfare, healthcare policy, education policy, climate policy, etc.
- **Implementation of new legislation** (National or EU Directives) impacting society or business sectors.
- Political conflict over policy (who supports/opposes; parliamentary dynamics; veto threats)

D) Political accountability & legitimacy
- Resignations, impeachments, no-confidence votes
- Ethics, corruption, conflicts of interest when tied to governance (not just criminal detail)
- Constitutional crises, institutional clashes, rule-of-law disputes

E) International politics & diplomacy
- Treaties, summits, sanctions, foreign policy statements
- Diplomatic incidents, recognition disputes, geopolitical negotiations

F) Civil liberties & rights as political contestation
- Protests, civil society actions, strikes when framed around policy/government power
- Major court rulings when they reshape governance or political rights (elections, constitutional issues)

Exclude (unless politics is clearly primary):
1) Crime / courts: If it’s mainly “who did what, evidence, trial details,” label CRIME/LAW, not POLITICS. Exception: if the case directly affects governance.
2) Business / economy: Market moves, company earnings, mergers → BUSINESS. Exception: sanctions, antitrust, budgets, or **new regulations/laws** being implemented → POLITICS.
3) Disasters / weather / accidents: If the focus is the event itself → DISASTER. Exception: political accountability/policy response dominates.
4) Culture / celebrity: Politicians as celebrities (personal life) → ENTERTAINMENT unless tied to office, campaign, or legitimacy.
5) Sports: Sports story with a politician quote is still SPORTS unless it becomes policy.

Decision rules:
Rule P1 — Actor × Action (strong signal): If article contains political actors/institutions AND governance actions, assign POLITICS.
Rule P2 — Elections/party process (strong signal): If the main content concerns elections, campaigns, polling, coalitions, party leadership, assign POLITICS.
Rule P3 — Policy conflict frame (medium signal): If the article is structured as policy debate, assign POLITICS.
Rule P4 — International statecraft (strong signal): If it involves states/IGOs and diplomatic/military/economic coercion instruments, assign POLITICS.
Rule P5 — “Mention-only” veto: If political entity is mentioned but not central, do NOT assign POLITICS.
"""

class PoliticsAssessmentRequest(BaseModel):
    url: str
    title: str
    content: Optional[str] = None # Optional, if frontend already has it or we re-fetch

class PoliticsAssessmentResponse(BaseModel):
    is_politics: bool
    confidence: int # 0-100
    reasoning: str
    labels: List[str] # e.g. ["POLITICS", "HEALTH"]

# --- Helpers (Moved to scraper_engine) ---
# parse_romanian_date and extract_date_from_url removed from here


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def gemini_discover_city_outlets(city: str, country: str, lat: float, lng: float, api_key: str) -> List[OutletCreate]:
    if not api_key: return []
    genai.configure(api_key=api_key)

    prompt = f"""
    You are a news outlet discovery expert. 
    TASK: List the top 15-20 most relevant news outlets (Newspapers, TV Stations, Radio, Online Portals) based in or covering: {city}, {country}.
    
    1. PRIORITIZE local outlets dedicated to {city}.
    2. INCLUDE national outlets if they are headquartered in {city} or have a major local bureau.
    3. You may check the {city} townhall website for a media list if available, but do not stop if not found.
    4. Focus on finding and validating live Website URLs. 
    5. Assign a popularity score (1-10) based on reputation.
    6. DETERMINTE the 2-letter Country Code (ISO 3166-1 alpha-2) for {country}.

    Return a strictly valid JSON list. Example:
    [
        {{ "name": "Monitorul de Cluj", "url": "https://www.monitorulcj.ro", "country_code": "RO", "type": "Online", "popularity": 10, "focus": "Local" }},
        {{ "name": "Sydney Morning Herald", "url": "https://www.smh.com.au", "country_code": "AU", "type": "Online", "popularity": 10, "focus": "Local" }}
    ]
    Do not include any markdown formatting or explanation, just the JSON string.
    """
    
    print(f"DEBUG: Starting Gemini Discovery for {city}, {country}")
    # Update to newer stable model
    model = genai.GenerativeModel('gemini-2.0-flash')
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
            country_code=d.get('country_code', 'XX'),
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

from dependencies import get_current_user, get_current_user_optional

@router.post("/outlets/discover_city", response_model=List[OutletRead])
async def discover_city_outlets(req: CityDiscoveryRequest, current_user: Optional[User] = Depends(get_current_user_optional), db: Session = Depends(get_db)):
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
    
    api_key = current_user.gemini_api_key if current_user and current_user.gemini_api_key else os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("DEBUG: No API key (User empty and Env empty), skipping AI discovery.")
        if existing: return existing
        return []

    try:
        discovered = await gemini_discover_city_outlets(req.city, req.country, req.lat, req.lng, api_key=api_key)
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
        async with httpx.AsyncClient(follow_redirects=True, timeout=15, headers=ROBUST_HEADERS) as client:
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
    scores: Optional[Dict[str, Any]] = {}
    ai_verdict: Optional[str] = None # New field for AI Title Check status
    translated_title: Optional[str] = None # New field for Translation
    is_spam: Optional[bool] = False # Soft block status
    
class DigestResponse(BaseModel):
    digest: str
    articles: List[ArticleMetadata]
    analysis_source: Optional[List[KeywordData]] = []
    analysis_digest: Optional[List[KeywordData]] = []

@router.post("/outlets/assess_article", response_model=PoliticsAssessmentResponse)
async def assess_article_politics(req: PoliticsAssessmentRequest, current_user: User = Depends(get_current_user)):
    """
    Evaluates an article against the operational definition of POLITICS using Gemini.
    """
    if not current_user.gemini_api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key required")
    
    genai.configure(api_key=current_user.gemini_api_key)
    
    # Needs content. If not provided, fetch it (snippet).
    article_text = req.content
    if not article_text or len(article_text) < 100:
        # Fetch ephemeral
        async with httpx.AsyncClient(follow_redirects=True, timeout=10, headers=ROBUST_HEADERS) as client:
            try:
                resp = await client.get(req.url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    # Basic extraction
                    article_text = soup.get_text(separator=' ', strip=True)[:15000] # Limit context
            except:
                article_text = "Content unavailable. Rely on Title."

    prompt = f"""
    You are an expert political analyst system.
    Evaluate the following article against the provided OPERATIONAL DEFINITION OF POLITICS.
    
    DEFINITION:
    {POLITICS_OPERATIONAL_DEFINITION}
    
    ARTICLE TITLE: {req.title}
    ARTICLE CONTENT (Snippet):
    {article_text[:10000]}
    
    TASK:
    1. Determine if this article qualifies as POLITICS based on the inclusion/exclusion criteria.
    2. Provide a Confidence score (0-100).
    3. Choose appropriate labels (e.g., POLITICS, BUSINESS, CRIME).
    4. Provide brief reasoning (max 1 sentence).
    
    Return JSON:
    {{
        "is_politics": true/false,
        "confidence": 90,
        "labels": ["POLITICS", "ECONOMY"],
        "reasoning": "Primary focus is on government budget approval (Rule P1)."
    }}
    """
    
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        response = await model.generate_content_async(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return PoliticsAssessmentResponse(**data)
    except Exception as e:
        print(f"Assessment Error: {e}")
        return PoliticsAssessmentResponse(is_politics=False, confidence=0, reasoning=f"Error: {str(e)}", labels=[])

# Helper to log to stream from async function
# We will return a tuple (result_map, error_msg)


async def batch_verify_titles_debug(titles_map: Dict[int, str], definition: str, api_key: str, target_language: str = "English") -> tuple[Dict[str, Any], str, str]:
    if not api_key:
        print("DEBUG: missing API key for batch_verify_titles_debug")
        return {}, "Missing API Key", ""
    
    print(f"DEBUG: Using API Key: {api_key[:4]}...{api_key[-4:]} | Target Lang: {target_language}")
    genai.configure(api_key=api_key)
    
    items_str = "\n".join([f"{idx}. {title}" for idx, title in titles_map.items()])
    
    prompt = f"""
    You are an expert political analyst and translator.
    
    TASK 1: Classify Article
    Classify the following article titles as "POLITICS" (True) or "NOT POLITICS" (False) based on the provided Operational Definition.
    
    TASK 2: Translate
    Translate the title into **{target_language}**.
    
    DEFINITION:
    {definition}
    
    TITLES:
    {items_str}
    
    OUTPUT FORMAT:
    Return a raw JSON object mapping the EXACT PROVIDED ID (e.g. {list(titles_map.keys())[0]}) to an object containing "verdict" (boolean) and "translated" (string).
    Do NOT re-index the items. Use the numbers provided in the input list.
    
    Example: 
    {{
        "{list(titles_map.keys())[0]}": {{ "verdict": true, "translated": "Translated Title Here..." }},
        ...
    }}
    
    STRICTLY RETURN JSON ONLY.
    """
    
    try:
        # Try multiple models in order of preference to ensure compatibility
        # Based on Debug Logs (Lib 0.8.6), these are the available models:
        candidate_models = [
            "gemini-2.0-flash", 
            "gemini-flash-latest",
            "gemini-2.0-flash-lite-preview-02-05", 
            "gemini-pro-latest",
            "gemini-1.5-flash-latest" # Keep as backup
        ]
        
        # Log Library Version
        try:
             import importlib.metadata
             ver = importlib.metadata.version("google-generativeai")
             print(f"DEBUG: google-generativeai version: {ver}")
        except:
             print("DEBUG: Could not determine google-generativeai version")

        response = None
        used_model = None
        last_error = None
        
        for m_name in candidate_models:
            try:
                model = genai.GenerativeModel(m_name)
                response = await model.generate_content_async(prompt)
                used_model = m_name
                break # Success
            except Exception as e:
                print(f"DEBUG: Model {m_name} failed: {e}")
                last_error = e
                continue
        
        if not response:
             error_str = str(last_error) if last_error else "No models available"
             
             # Emergency: List available models to find out what IS supported
             try:
                available = []
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        available.append(m.name)
                available_str = ", ".join(available)
                err_msg = f"All models failed. Lib Ver: {ver}. Available: {available_str}. Last Error: {error_str}"
             except Exception as e2:
                err_msg = f"All models failed. Last error: {error_str}. (Also failed to list models: {e2})"
                
             return {}, err_msg, ""

        text = response.text.replace("```json", "").replace("```", "").strip()
        
        with open("debug_ai.log", "a") as f:
             f.write(f"\n--- BATCH ({used_model}) ---\nResponse: {text[:200]}...\n")

        # Robust Parsing
        try:
            result_map = json.loads(text)
        except json.JSONDecodeError:
            # Fallback: Try regex to find JSON-like structure
            import re
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                result_map = json.loads(match.group(0))
            else:
                raise ValueError(f"Could not extract JSON from {used_model}. Raw: {text[:100]}")

        # Convert all keys to strings for consistent comparison
        # And ensure value structure
        final_map = {}
        for k, v in result_map.items():
            str_k = str(k)
            # Handle Legacy Boolean Response (Just in case AI hallucinates or old prompt cached?)
            if isinstance(v, bool):
                final_map[str_k] = {"verdict": v, "translated": None}
            elif isinstance(v, dict):
                final_map[str_k] = {
                    "verdict": v.get("verdict", False),
                    "translated": v.get("translated")
                }
            else:
                 final_map[str_k] = {"verdict": False, "translated": None} # Fallback

        input_keys = [str(k) for k in titles_map.keys()]
        
        # Mismatch Check & Fallback
        # If complete mismatch but count matches, blindly assign in order
        if not any(k in final_map for k in input_keys) and len(final_map) == len(input_keys):
            with open("debug_ai.log", "a") as f:
                f.write("Mismatch detected. Applying fallback mapping.\n")
            result_values = list(final_map.values())
            final_map = {input_keys[i]: result_values[i] for i in range(len(input_keys))}
            
        with open("debug_ai.log", "a") as f:
             f.write(f"Mapped Keys: {list(final_map.keys())}\n")
             
        return final_map, None, text
    except Exception as e:
        with open("debug_ai.log", "a") as f:
             f.write(f"ERROR: {e}\n")
        return {}, str(e), ""

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
    city: Optional[str] = None
    
    is_public: bool = False
    public_slug: Optional[str] = None
    
    created_at: str
    
    owner_id: int
    owner_username: Optional[str] = None
    owner_is_visible: bool = True

@router.get("/outlets/", response_model=List[dict])
async def get_all_outlets(db: Session = Depends(get_db)):
    result = await db.execute(select(NewsOutlet))
    outlets = result.scalars().all()
    # Lightweight return
    return [{"id": o.id, "name": o.name, "city": o.city, "country": o.country_code, "url": o.url} for o in outlets]

@router.get("/outlets/digests/saved", response_model=List[DigestRead])
async def get_saved_digests(db: Session = Depends(get_db)):
    """Returns list of ALL saved digests (Global Stream)."""
    # Join with User to get owner details
    stmt = select(NewsDigest, User).join(User, NewsDigest.user_id == User.id).order_by(NewsDigest.created_at.desc())
    result = await db.execute(stmt)
    rows = result.all() # Returns list of (NewsDigest, User)
    
    return [
        DigestRead(
            id=d.id,
            title=d.title,
            category=d.category,
            city=d.city,
            is_public=d.is_public,
            public_slug=d.public_slug,
            created_at=d.created_at.isoformat(),
            owner_id=user.id,
            owner_username=user.username,
            owner_is_visible=user.is_username_visible
        )
        for d, user in rows
    ]

class DigestDetail(BaseModel):
    id: int
    title: str
    category: str
    city: Optional[str] = None
    summary_markdown: str
    articles: List[Dict[str, Any]]
    analysis_source: Optional[List[Dict[str, Any]]] = []
    analysis_digest: Optional[List[Dict[str, Any]]] = []
    created_at: str
    owner_id: int
    owner_username: Optional[str] = None
    owner_is_visible: bool = True

@router.get("/outlets/digests/{id}", response_model=DigestDetail)
async def get_digest_detail(id: int, db: Session = Depends(get_db)):
    """Returns full details of a saved digest."""
    stmt = select(NewsDigest, User).join(User, NewsDigest.user_id == User.id).where(NewsDigest.id == id)
    result = await db.execute(stmt)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Digest not found")
        
    digest, user = row
    
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
        city=digest.city,
        summary_markdown=digest.summary_markdown,
        articles=articles,
        analysis_source=analysis_source,
        analysis_digest=analysis_digest,
        created_at=digest.created_at.isoformat(),
        owner_id=user.id,
        owner_username=user.username,
        owner_is_visible=user.is_username_visible
    )



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
async def get_city_info(city: str, country: str, current_user: Optional[User] = Depends(get_current_user_optional), db: Session = Depends(get_db)):
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
        api_key = current_user.gemini_api_key if current_user else None
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

async def smart_scrape_outlet(outlet: NewsOutlet, category: str, timeframe: str = "24h", log_bus: any = None, api_key: str = None, scraper_rule_config: dict = None) -> dict:
    print(f"DEBUG: smart_scrape_outlet called for {outlet.url}")
    with open("stream_debug.log", "a") as f: f.write(f"START_SCRAPE: {outlet.url}\n")
    """
    Fetches content from an outlet, intelligently navigating to the category page if possible.
    Returns structured article data and raw text for AI.
    """
    
    async def log(msg: str):
         ts = datetime.now().strftime("%H:%M:%S")
         full_msg = f"[{ts}] {msg}"
         try:
             with open("stream_debug.log", "a") as f: f.write(f"SCRAPER-DEBUG: {full_msg}\n")
         except: pass
         if log_bus:
              await log_bus(full_msg)
         print(full_msg)
         
    await log(f"STARTING SCRAPE for {outlet.name} ({outlet.url})")
    timeline_events = []
    timeline_events.append({"type": "init", "start": time.time(), "label": "Init Scraper"})

    # 1. Determine Target URL
    target_url = outlet.url
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=20, headers=ROBUST_HEADERS) as client:
        # 1. Fetch Homepage
        timeline_events.append({"type": "fetch", "start": time.time(), "label": "Fetch Homepage"})
        t0_fetch = time.time()
        await log(f"[{outlet.name}] Fetching homepage: {outlet.url}")
        resp = await robust_fetch(client, outlet.url)
        if not resp or resp.status_code != 200:
            code = resp.status_code if resp else "ERR"
            await log(f"Failed to fetch {target_url}: {code}")
            return {"articles": [], "raw_text": ""}
        
        html_content = resp.text
        # Encoding fix
        if resp.encoding and resp.encoding.lower() not in ['utf-8', 'iso-8859-1']:
             try:
                 html_content = resp.content.decode(resp.encoding)
             except:
                 pass # Fallback to .text auto-decode
        
        await log(f"Fetched {len(html_content)} bytes (Encoding: {resp.encoding or 'auto'})")
        timeline_events[-1]["end"] = time.time() # End Fetch
        
        t0_parse = time.time()
        timeline_events.append({"type": "parse", "start": t0_parse, "label": "Parse Basic"})
        
        final_url = outlet.url
        # Limit HTML size to prevent CPU blocking on huge pages
        html = resp.text[:200000] 
        soup = BeautifulSoup(html, 'html.parser')
        candidates = []
        seen_urls = set()
        links_found = soup.find_all('a', href=True)
        with open("stream_debug.log", "a") as f: f.write(f"EXTRACT: Found {len(links_found)} raw <a> tags in {outlet.url}\n")
        timeline_events[-1]["end"] = time.time()

        # 2. Try to find Category Link (Universal AI Discovery)
        discovered_cat_url = None
        # Default keywords for fallback filtering logic downstream
        cat_keywords = [category.lower()]
        
        if category.lower() not in ["general", "all", "headline"] and api_key:
             await log(f"[{outlet.name}] 🧠 Asking AI to find navigation link for '{category}'...")
             discovered_cat_url = await scraper_engine.gemini_find_category_url(html_content, outlet.url, category, api_key)
             
             if discovered_cat_url:
                 await log(f"[{outlet.name}] ✅ AI Found Link: {discovered_cat_url}")
             else:
                 await log(f"[{outlet.name}] ⚠️ AI could not identify a specific link. Falling back to homepage.")
        
        # 3. Construct URLs to Scrape
        urls_to_scrape = []
        if discovered_cat_url:
            urls_to_scrape.append(discovered_cat_url)
        else:
            urls_to_scrape.append(outlet.url)
            
        await log(f"DEBUG: Active Scraping for {outlet.name}: {urls_to_scrape}")
        
        # --- NEW: SITEMAP STRATEGY ---
        # Try to fetch fresh links from sitemap directly to augment discovery
        
        # Calculate days limit from timeframe
        sitemap_days = 3 # default
        if timeframe == "24h": sitemap_days = 1
        elif timeframe == "3days": sitemap_days = 3
        elif timeframe == "1week": sitemap_days = 7
        elif timeframe == "1month": sitemap_days = 30
        
        sitemap_links = []
        print(f"DEBUG: Entering sitemap check for {outlet.name}")
        try:
             await log(f"[{outlet.name}] 🗺️ Checking sitemap...")
             # Timebox sitemap fetching to prevent hangs
             # sitemap_links = await asyncio.wait_for(
             #    scraper_engine.fetch_sitemap_urls(outlet.url, days_limit=sitemap_days), 
             #    timeout=15.0
             # )
             print("DEBUG: Sitemap disabled.")
             print(f"DEBUG: Sitemap links count: {len(sitemap_links)}")
             if sitemap_links:
                 await log(f"[{outlet.name}] 🗺️ Found {len(sitemap_links)} links via Sitemap")
        except asyncio.TimeoutError:
             print(f"DEBUG: Sitemap timeout for {outlet.name}")
             await log(f"[{outlet.name}] ⚠️ Sitemap fetch timed out. Skipping.")
        except Exception as e: 
             print(f"DEBUG: Sitemap error for {outlet.name}: {e}")
             # await log(f"DEBUG: Sitemap error: {e}")
             pass
        
        candidates_map = {} 
        
        # Process Sitemap Links directly
        if sitemap_links:
            await log(f"  -> Processing {len(sitemap_links)} sitemap entries...")
            for s_url in sitemap_links:
                # Basic metadata creation
                s_date_str = None
                date_obj = scraper_engine.extract_date_from_url(s_url)
                if date_obj: s_date_str = date_obj.strftime("%Y-%m-%d")
                
                # Add to map
                candidates_map[s_url] = ArticleMetadata(
                    source=outlet.name,
                    # Prettify Title (Slug -> Title Case)
                    title=s_url.rstrip('/').split('/')[-1].replace('-', ' ').replace('_', ' ').title() or "Untitled Article",
                    url=s_url,
                    date_str=s_date_str
                ) 
    
    # 3. Scrape All Candidates
    # import asyncio (removed to prevent shadowing)
    
    # Helper (placeholder)
    async def fetch_and_parse(target_url):
         try: pass
         except: pass

    # Refactored Loop to process multiple URLs
    combined_content = ""
    
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    for i, target_url in enumerate(urls_to_scrape):
        # Limit active scraping to avoid timeouts
        if i > 3: break 

        await log(f"[{outlet.name}] 🕵️ Deep Scan: {target_url}")
        
        resp = None
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0, headers=ROBUST_HEADERS) as client:
             try:
                 resp = await client.get(target_url)
                 if resp.status_code != 200:
                     await log(f"  -> Failed {resp.status_code}")
                     continue 
             except Exception as e:
                 await log(f"  -> Fetch Error: {e}")
                 continue 
        
        # Valid response check
        if not resp: 
             await log(f"  -> Resp is None, skipping.")
             continue
        
        await log(f"  -> Got {len(resp.text)} chars.")
        
        # NOTE: Removed the second 'try/log/async with' block that was here.
        # Now proceeding to parsing...
                
        # Parse
        soup = BeautifulSoup(resp.text, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        
        # Truncate to avoid exploding token context
        combined_content += f"\n--- SOURCE: {outlet.name} [{target_url}] ---\n{text[:10000]}\n"
        
        # LEGACY LOOP REMOVED - Relying on Standardized Engine
        await log("  -> Legacy loop bypassed. Proceeding to Engine Extraction.")

        # Standardized Link Extraction
        await log(f"  -> Calling extract_article_links...")
        extracted_items = scraper_engine.extract_article_links(resp.text, target_url)
        await log(f"  -> Extracted {len(extracted_items)} raw links via Engine.")
        
        # Rule Object Init (Reuse or Fetch from DB)
        rule_obj = None
        
        # 1. Use Override if provided (Testing)
        if scraper_rule_config:
              rule_obj = scraper_engine.ScraperRule(
                  domain="custom",
                  date_selectors=scraper_rule_config.get('date_selectors'),
                  date_regex=scraper_rule_config.get('date_regex'),
                  title_selectors=scraper_rule_config.get('title_selectors'),
                  use_json_ld=scraper_rule_config.get('use_json_ld', True),
                  use_data_layer=scraper_rule_config.get('use_data_layer', True),
                  data_layer_var=scraper_rule_config.get('data_layer_var', "dataLayer")
              )
        # 2. Fetch from DB if not provided (Persistence)
        else:
            try:
                domain_key = target_url.split("//")[-1].split("/")[0].replace("www.", "")
                # ScraperRule is already imported from models
                db_rule = db.query(ScraperRule).filter(ScraperRule.domain == domain_key).first()
                if db_rule:
                    rule_obj = scraper_engine.ScraperRule(
                        domain=db_rule.domain,
                        date_selectors=db_rule.date_selectors,
                        date_regex=db_rule.date_regex,
                        # Pass title selectors from DB for persistence
                        title_selectors=db_rule.title_selectors,
                        use_json_ld=db_rule.use_json_ld,
                        use_data_layer=db_rule.use_data_layer,
                        data_layer_var=db_rule.data_layer_var
                    )
                    # print(f"DEBUG: Loaded Persisted Rule for {domain_key}: {db_rule.title_selectors}")
            except Exception as e:
                print(f"Failed to load ScraperRule from DB: {e}")

        # Separate items needing scan vs ready items
        items_to_scan = []
        
        for item in extracted_items:
            full_url = item['url']
            raw_title = item['title']
            
            # Initial Date Check
            found_date_str = None
            url_date_obj = scraper_engine.extract_date_from_url(full_url)
            if url_date_obj: found_date_str = url_date_obj.strftime("%Y-%m-%d")
            
            clean_rt = raw_title.strip()
            is_bad_title = clean_rt.isdigit() or len(clean_rt) < 5 or (len(clean_rt) < 15 and clean_rt.replace(" ","").isdigit())
            
            # Soft Spam Check
            if item.get('is_spam'):
                 if full_url not in candidates_map:
                    candidates_map[full_url] = ArticleMetadata(
                        source=outlet.name,
                        title=raw_title, # Keep original title
                        url=full_url,
                        date_str=None, 
                        is_spam=True,
                        relevance_score=0
                    )
                 continue # Skip Deep Scan

            if not found_date_str or is_bad_title:
                items_to_scan.append({
                    "url": full_url, 
                    "title": raw_title, 
                    "date": found_date_str,
                    "is_bad_title": is_bad_title
                })
            else:
                # Add directly
                if full_url not in candidates_map:
                    candidates_map[full_url] = ArticleMetadata(
                        source=outlet.name,
                        title=raw_title,
                        url=full_url,
                        date_str=found_date_str
                    )

        # Parallel Worker
        sem = asyncio.Semaphore(5) # max 5 concurrent scans
        
        async def process_deep_scan_safe(item):
            async with sem:
                full_url = item["url"]
                raw_title = item["title"]
                found_date_str = item["date"]
                is_bad_title = item["is_bad_title"]
                
                ev = {"type": "deep_scan", "start": time.time(), "label": f"Deep Scan: {full_url.split('/')[-1][:20]}"}
                timeline_events.append(ev)
                
                try:
                    await asyncio.sleep(0.5) 
                    async with httpx.AsyncClient(headers=ROBUST_HEADERS, verify=False, timeout=15, follow_redirects=True) as s_client:
                         s_resp = await s_client.get(full_url)
                         if s_resp.status_code == 200:
                             effective_rule = rule_obj or scraper_engine.ScraperRule(domain="fallback", use_json_ld=True, use_data_layer=True)
                             
                             # Extract Date
                             if not found_date_str:
                                 found_date_str = scraper_engine.extract_date_from_html(s_resp.text, full_url, custom_rule_override=effective_rule)
                             
                             # Extract Title (Deep Scan Override)
                             # Unconditional Deep Extraction (Matches Test Mode Behavior)
                             deep_title = scraper_engine.extract_title_from_html(s_resp.text, full_url, custom_rule_override=effective_rule)
                             
                             if deep_title:
                                 raw_title = deep_title
                except: pass
                
                ev["end"] = time.time()
                return (full_url, raw_title, found_date_str)

        # Execute Parallel
        tasks = [process_deep_scan_safe(i) for i in items_to_scan]
        if tasks:
            await log(f"Launching {len(tasks)} parallel deep scans (5 concurrent)...")
            scan_results = await asyncio.gather(*tasks)
            
            for res_url, res_title, res_date in scan_results:
                 if res_url in candidates_map:
                     c = candidates_map[res_url]
                     if res_date: c.date_str = res_date
                     if len(res_title) > len(c.title): c.title = res_title
                 else:
                     candidates_map[res_url] = ArticleMetadata(
                        source=outlet.name,
                        title=res_title,
                        url=res_url,
                        date_str=res_date
                     )

    all_extracted_articles = list(candidates_map.values())

    # Return aggregated result (matching the expected dict structure)

    
    return {
        "text": combined_content,
        "articles": all_extracted_articles,
        "timeline_events": timeline_events
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
    city: Optional[str] = None
    timeframe: Optional[str] = None
    summary_markdown: str
    articles: List[Dict[str, Any]] # Will be serialized to JSON
    selected_article_urls: Optional[List[str]] = None
    analysis_source: Optional[List[Dict[str, Any]]] = None # Will be serialized to JSON
    analysis_digest: Optional[List[Dict[str, Any]]] = None

class DigestRead(DigestCreate):
    id: int
    created_at: datetime
    is_public: bool = False
    public_slug: Optional[str] = None
    owner_id: int
    owner_username: Optional[str] = None
    
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
    print(f"DEBUG: Saving digest '{digest.title}' for user {current_user.id}")
    import json
    
    # AI TITLE GENERATION
    final_title = digest.title
    # If the default title is generic "Digest", try to improve it
    # If the default title is generic "Digest", try to improve it
    # We check if title is None, or contains "digest" (case insensitive)
    if current_user.gemini_api_key and (not final_title or "digest" in final_title.lower()) and len(digest.summary_markdown) > 50:
        try:
            print(f"DEBUG: Generating AI Title for digest...")
            import google.generativeai as genai # Ensure import
            genai.configure(api_key=current_user.gemini_api_key)
            model_title = genai.GenerativeModel('gemini-1.5-flash')
            
            title_prompt = f"""
            Generate a short, 3-7 word newspaper-style headline for this news summary.
            It must be specific to the events described.
            Do not use quotes. Do not use "Digest" or "Summary".
            
            Summary:
            {digest.summary_markdown[:4000]}
            
            Headline:
            """
            
            title_resp = await model_title.generate_content_async(title_prompt)
            ai_title = title_resp.text.strip().replace('"', '').replace("**", "").replace("Headline:", "").strip()
            if ai_title and len(ai_title) < 100:
               final_title = ai_title
               print(f"DEBUG: AI Title Generated: {final_title}")
        except Exception as e:
            print(f"DEBUG: AI Title Failed: {e}")

    try:
        db_digest = NewsDigest(
            user_id=current_user.id,
            title=final_title,
            category=digest.category,
            city=digest.city,
            timeframe=digest.timeframe,
            summary_markdown=digest.summary_markdown,
            articles_json=json.dumps(digest.articles),
            selected_article_urls=json.dumps(digest.selected_article_urls) if digest.selected_article_urls else None,
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
            city=db_digest.city,
            timeframe=db_digest.timeframe,
            summary_markdown=db_digest.summary_markdown,
            articles=json.loads(db_digest.articles_json),
            selected_article_urls=json.loads(db_digest.selected_article_urls) if db_digest.selected_article_urls else None,
            analysis_source=json.loads(db_digest.analysis_source) if db_digest.analysis_source else [],
            created_at=db_digest.created_at,
            is_public=db_digest.is_public,
            public_slug=db_digest.public_slug,
            owner_id=db_digest.user_id,
            owner_username=current_user.username
        )
    except Exception as e:
        print(f"CRITICAL: Save Digest failed: {e}")
        import traceback
        traceback.print_exc()
        # EXPOSE ERROR DETAILS TO FRONTEND
        raise HTTPException(status_code=500, detail=f"SAVE ERROR: {str(e)} Type: {type(e).__name__}")

@router.put("/digests/{digest_id}", response_model=DigestRead)
async def update_digest(
    digest_id: int,
    digest: DigestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing digest (overwrite content)."""
    stmt = select(NewsDigest).where(NewsDigest.id == digest_id, NewsDigest.user_id == current_user.id)
    result = await db.execute(stmt)
    db_digest = result.scalars().first()
    
    if not db_digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    
    import json
    
    db_digest.title = digest.title
    db_digest.category = digest.category
    db_digest.city = digest.city
    db_digest.timeframe = digest.timeframe
    db_digest.summary_markdown = digest.summary_markdown
    db_digest.articles_json = json.dumps(digest.articles)
    
    # Update conditionals
    if digest.selected_article_urls:
        db_digest.selected_article_urls = json.dumps(digest.selected_article_urls)
    if digest.analysis_source:
        db_digest.analysis_source = json.dumps(digest.analysis_source)
    if digest.analysis_digest:
        db_digest.analysis_digest = json.dumps(digest.analysis_digest)
        
    await db.commit()
    await db.refresh(db_digest)
    
    return DigestRead(
        id=db_digest.id,
        title=db_digest.title,
        category=db_digest.category,
        city=db_digest.city,
        timeframe=db_digest.timeframe,
        summary_markdown=db_digest.summary_markdown,
        articles=json.loads(db_digest.articles_json),
        selected_article_urls=json.loads(db_digest.selected_article_urls) if db_digest.selected_article_urls else None,
        analysis_source=json.loads(db_digest.analysis_source) if db_digest.analysis_source else [],
        created_at=db_digest.created_at,
        is_public=db_digest.is_public,
        public_slug=db_digest.public_slug,
        owner_id=db_digest.user_id,
        owner_username=current_user.username
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
    print(f"DEBUG: list_digests found {len(digests)} items for user {current_user.id}")
    
    # Manual mapping to handle JSON deserialization
    # Manual mapping with Safety Checks
    safe_digests = []
    for d in digests:
        try:
             safe_digests.append(DigestRead(
                id=d.id,
                title=d.title,
                category=d.category,
                city=d.city,
                timeframe=d.timeframe,
                summary_markdown=d.summary_markdown,
                articles=json.loads(d.articles_json) if d.articles_json else [],
                selected_article_urls=json.loads(d.selected_article_urls) if d.selected_article_urls else None,
                analysis_source=json.loads(d.analysis_source) if d.analysis_source else [],
                created_at=d.created_at or datetime.now(), # Fallback for old/broken rows
                is_public=getattr(d, 'is_public', False), # Safe getattr
                public_slug=getattr(d, 'public_slug', None),
                owner_id=d.user_id,
                owner_username=current_user.username
            ))
        except Exception as e:
             # DEBUG: Return broken digest so we can see the error in frontend
             safe_digests.append(DigestRead(
                id=d.id,
                title=f"ERR: {type(e).__name__}",
                category="Error",
                city=d.city or "Unknown",
                timeframe="24h",
                summary_markdown=f"### Serialization Error\n\n{str(e)}",
                articles=[],
                selected_article_urls=[],
                analysis_source=[],
                created_at=d.created_at or datetime.now(),
                is_public=False,
                public_slug="error",
                owner_id=d.user_id,
                owner_username="System"
            ))
             
    return safe_digests

@router.delete("/digests/{digest_id}")
async def delete_digest(
    digest_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a saved digest. Only the owner can delete it."""
    stmt = select(NewsDigest).where(NewsDigest.id == digest_id)
    result = await db.execute(stmt)
    digest = result.scalar_one_or_none()
    
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
        
    # Strict Permission Check
    if digest.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this digest")
    
    await db.delete(digest)
    await db.commit()
    return {"status": "success", "message": "Digest deleted"}

def generate_slug(length=8):
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

@router.post("/outlets/digests/{digest_id}/share")
async def share_digest(digest_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Enable sharing for a digest and return its public slug."""
    stmt = select(NewsDigest).where(NewsDigest.id == digest_id, NewsDigest.user_id == current_user.id)
    result = await db.execute(stmt)
    digest = result.scalars().first()
    
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    
    if not digest.public_slug:
        # Generate unique slug
        while True:
            slug = generate_slug()
            stmt_slug = select(NewsDigest).where(NewsDigest.public_slug == slug)
            res_slug = await db.execute(stmt_slug)
            exists = res_slug.scalars().first()
            if not exists:
                digest.public_slug = slug
                break
    
    digest.is_public = True
    await db.commit()
    await db.refresh(digest)
    return {"slug": digest.public_slug, "is_public": True}

@router.get("/digests/public/{slug}", response_model=DigestDetail)
async def get_public_digest(slug: str, db: Session = Depends(get_db)):
    """Get a public digest by slug (No Auth required)."""
    print(f"DEBUG: Fetching public digest slug='{slug}'")
    stmt = select(NewsDigest).where(NewsDigest.public_slug == slug) # Query by slug FIRST to see if it exists
    result = await db.execute(stmt)
    digest = result.scalars().first()
    
    if not digest:
        print(f"DEBUG: Slug '{slug}' NOT FOUND in DB.")
        raise HTTPException(status_code=404, detail="Digest not found or private")

    print(f"DEBUG: Found digest {digest.id}. is_public={digest.is_public}")
    if not digest.is_public:
        print(f"DEBUG: Digest {digest.id} is NOT PUBLIC.")
        raise HTTPException(status_code=404, detail="Digest not found or private")
    
    # Helper to parse JSON fields safely
    def safe_json(field):
        import json
        try: return json.loads(field) if field else []
        except: return []

    return DigestDetail(
        id=digest.id,
        title=digest.title,
        category=digest.category,
        city=digest.city,
        summary_markdown=digest.summary_markdown,
        articles=safe_json(digest.articles_json),
        analysis_source=safe_json(digest.analysis_source),
        analysis_digest=safe_json(digest.analysis_digest),
        created_at=(digest.created_at or datetime.now()).isoformat(),
        owner_id=digest.user_id # Required by DigestDetail
    )

@router.post("/digests/public/{slug}/translate_articles")
async def translate_public_digest_articles(slug: str, db: Session = Depends(get_db)):
    """
    Translates article titles to English using AI for a public digest.
    Updates the DB so future visitors see translations immediately.
    """
    stmt = select(NewsDigest).where(NewsDigest.public_slug == slug)
    result = await db.execute(stmt)
    digest = result.scalars().first()
    
    if not digest or not digest.is_public:
        raise HTTPException(status_code=404, detail="Digest not found")
        
    articles = json.loads(digest.articles_json) if digest.articles_json else []
    if not articles:
        return {"status": "empty", "articles": []}
        
    # check if owner has key (we use owner's key since they own the public page)
    stmt_user = select(User).where(User.id == digest.user_id)
    res_user = await db.execute(stmt_user)
    owner = res_user.scalars().first()
    
    if not owner or not owner.gemini_api_key:
        raise HTTPException(status_code=400, detail="Owner AI key missing")
        
    # Identify items needing translation
    to_translate = []
    indices = []
    
    for i, art in enumerate(articles):
        # Skip if already translated OR if it looks English (ASCII check is a cheap proxy, or just force AI)
        if not art.get('translated_title'):
             to_translate.append(art.get('title', ''))
             indices.append(i)
             
    if not to_translate:
        return {"status": "already_translated", "articles": articles}
        
    # AI Translation
    try:
        genai.configure(api_key=owner.gemini_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = "Translate these news headlines to English. Return a JSON list of strings." + json.dumps(to_translate)
        resp = await model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
        translations = json.loads(resp.text)
        
        if len(translations) != len(to_translate):
            # Fallback if length mismatch
            print("Translation length mismatch, using raw mapping")
        
        updated_count = 0
        for idx, trans in zip(indices, translations):
            if isinstance(trans, str):
                articles[idx]['translated_title'] = trans
                updated_count += 1
                
        # Save back to DB
        digest.articles_json = json.dumps(articles)
        await db.commit()
        
        return {"status": "success", "updated": updated_count, "articles": articles}
        
    except Exception as e:
        print(f"Translation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        Input is likely in French, Romanian, or English. Do NOT reject based on language.
        Title: {title}
        URL: {url}
        
        Rules:
        1. Context matters. "Water cutoff" is NOT Politics. "Mayor announces water cutoff" IS Politics/Administration.
        2. "Traffic accident" is NOT Politics.
        3. Local Administration, Budget, City Council, Public Services, Urban Planning, and Public Spending ARE Relevant.
        4. If it mentions a Politician, Party (RN, PS, etc.), Mayor, or Law, return TRUE.
        5. If uncertain or title is ambiguous but sounds like local news/admin, return TRUE (Fail Open).
        
        Respond with exactly ONE word: TRUE or FALSE.
        """
        
        response = await model.generate_content_async(prompt)
        ans = response.text.strip().upper()
        return "TRUE" in ans
    except Exception as e:
        print(f"AI Verification Failed: {e}")
        return True # Fail open to avoid dropping potentially good articles if API fails

# Removed OLD extract_date_with_ai (Moved to scraper_engine)

from fastapi.responses import StreamingResponse
import json
import asyncio

class SummarizeRequest(BaseModel):
    articles: List[dict]
    category: str
    city: str
    timeframe_label: Optional[str] = None

@router.post("/outlets/digest/summarize")
async def summarize_selected_articles(req: SummarizeRequest, current_user: User = Depends(get_current_user)):
    """
    Generates a contrasted summary of *selected* articles using Gemini.
    Uses Chunked Processing for large sets to ensure full coverage.
    """
    if not req.articles:
        return {"summary": "No articles selected."}
        
    api_key = current_user.gemini_api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="Missing Gemini API Key. Please set it in Settings.")
        
    genai.configure(api_key=api_key)
    genai.configure(api_key=api_key)
    # Model Fallback Strategy (Updated aliases)
    # Model Fallback Strategy (Updated aliases)
    MODELS_TO_TRY = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite-preview-02-05", 
        "gemini-1.5-flash", 
        "gemini-1.5-pro",
        "gemini-pro"
    ]
    
    # 1. GENERATE SOURCE INDEX PROGRAMMATICALLY
    # This ensures 100% accuracy and perfectly formatted links (no LLM hallucination).
    source_index_md = "\n\n## Global Source Index\n"
    for idx, art in enumerate(req.articles):
        # Clean URL
        url = art.get('url', '#')
        if url and not url.startswith('http'):
             # Attempt to guess protocol or leave broken (better than localhost)
             if not url.startswith('/'): url = 'https://' + url
        
        title = art.get('title', 'Source').replace('[', '(').replace(']', ')') # Escape brackets
        src = art.get('source', 'Unknown')
        # Format: - [1] [Title](url) (Source)
        source_index_md += f"- [{idx+1}] [{title}]({url}) *({src})*\n"

    # 2. CHUNKED PROCESSING
    BATCH_SIZE = 200 # Increased to 200 to maximize Context Window (1M) and reduce API Call Count
    chunks = [req.articles[i:i + BATCH_SIZE] for i in range(0, len(req.articles), BATCH_SIZE)]
    
    partial_reports = []
    
    async def process_chunk(chunk_idx, chunk_articles):
        start_idx = chunk_idx * BATCH_SIZE + 1
        end_idx = start_idx + len(chunk_articles) - 1
        
        context = ""
        for i, art in enumerate(chunk_articles):
            global_id = start_idx + i
            txt = art.get('content_summary', '') or art.get('title', '')
            src = art.get('source', 'Unknown')
            # We don't need URL in context for the LLM anymore if we handle index externally,
            # BUT the LLM needs to know WHICH [n] to use.
            context += f"SOURCE [{global_id}]: {txt} (from {src})\n\n"
            
        prompt = f"""
        You are writing a section of a MASSIVELY DETAILED INTELLIGENCE REPORT for {req.city}.
        This section covers Sources [{start_idx}] to [{end_idx}].
        
        SOURCE DATA:
        {context}
        
        MANDATES:
        1. **CITATION STRICTNESS**: Use ONLY the `[n]` format provided in the source headers.
        2. **NO HALLUCINATION**: Do not cite sources outside the range [{start_idx}-{end_idx}].
        3. **DEEP DIVE**: Write a detailed analysis of the themes found in strictly THESE sources.
        5. **ANTI-CLUMPING**: Discuss details. Do not just list citations.
        6. **PROPAGANDA ANALYSIS**: Explicitly compare how different sources portray the SAME event. Highlight specific contradictions, omitted facts, or tonal bias between outlets (e.g., "While [Source A] verifies X, [Source B] frames it as Y").
        7. **FORMAT**: Use Markdown. Do NOT include a "Source Index" at the end (it is handled externally).
        8. **HEADLINE**: The very first line of your output MUST be a newspaper-style H1 Headline illustrating the major stories (e.g. # Mayor announces new budget).
        
        Analyze the conflict, nuances, and details within this batch.
        """
        
        last_error = None
        for model_name in MODELS_TO_TRY:
            try:
                # print(f"DEBUG: Summarizing chunk {chunk_idx} with {model_name}...")
                model = genai.GenerativeModel(model_name)
                response = await model.generate_content_async(prompt)
                
                # Handle TRIGGERED SAFETY FILTERS (Empty Text)
                try:
                    return f"\n### Analysis of Sources {start_idx}-{end_idx}\n{response.text}"
                except ValueError:
                    print(f"Chunk {chunk_idx} blocked by safety filters on {model_name}.")
                    return f"\n### Analysis of Sources {start_idx}-{end_idx}\n(Analysis Redacted by Safety Filters)"
                    
            except Exception as e:
                print(f"[{model_name}] Generation Failed: {e}")
                last_error = e
                # Continue to next model regardless of error type (404, 429, 500, etc.)
                continue
        
        # If loop finishes, all models failed
        return f"\n### Analysis of Sources {start_idx}-{end_idx}\n(Quota Exceeded on all models: {str(last_error)})"

    # Run chunks in parallel
    tasks = [process_chunk(i, c) for i, c in enumerate(chunks)]
    chunk_results = await asyncio.gather(*tasks)
    
    # 3. SYNTHESIS / CONSOLIDATION
    # If we have multiple chunks, we must unify them to avoid "Batch 1... Batch 2..." fragmentation.
    combined_raw_analysis = "\n\n".join(chunk_results)
    
    # Calculate Date Range from Articles for Title
    try:
        from datetime import datetime
        dates = []
        for a in req.articles:
            d_str = a.get('date_str')
            if d_str:
                # Try simple ISO parsing; might need more robust if date_str varies
                try: dates.append(datetime.fromisoformat(d_str).date())
                except: pass
        
        if dates:
            min_d, max_d = min(dates), max(dates)
            # Format: 8.1.2026 - 11.1.2026
            fmt = lambda d: f"{d.day}.{d.month}.{d.year}"
            date_range_str = f"{fmt(min_d)} - {fmt(max_d)}"
        else:
            from datetime import date
            date_range_str = date.today().strftime("%d.%m.%Y")
            
    except Exception as e:
        print(f"Date Calc Error: {e}")
        from datetime import date
        date_range_str = date.today().strftime("%d.%m.%Y")
        
    report_title = f"# {req.city}: {req.category} Report ({req.timeframe_label or date_range_str})"

    if len(chunks) > 1:
        synthesis_prompt = f"""
        You are the Chief Editor of a high-level Intelligence Report.
        You have received detailed section drafts from field agents.
        
        DRAFTS:
        {combined_raw_analysis}
        
        MISSION:
        1. **UNIFY**: Merge these drafts into ONE seamless, cohesive narrative history.
        2. **PRESERVE DETAILS**: Do not Summarize away the specifics. Keep the verified facts.
        3. **PRESERVE CITATIONS**: You MUST retain the `[n]` citations exactly as they appear.
           - CRITICAL: Do NOT re-number citations. If a fact has `[55]`, keep `[55]`.
        4. **COMPARATIVE LENS**: Highlight conflicting narratives. If Source A and Source B disagree on a key fact, note it explicitly.
        5. **STRUCTURE**: Start directly with the first section header (e.g. ## Executive Summary or ## Key Developments).
        6. **NO CHAT**: Do NOT output conversational filler. The output must start with the Headline.
        6. **HEADLINE**: The very first line of your output MUST be a newspaper-style H1 Headline illustrating the key theme of the entire report (e.g. # Infrastructure Crisis Deepens in Kyiv).
        
        Write the final consolidated report in Markdown.
        """
        try:
            consolidation_response = await model.generate_content_async(synthesis_prompt)
            # Ensure we don't double up titles if the model ignores instruction, strip leading H1 if matches ours
            reply = consolidation_response.text.strip()
            
            # TITLE LOGIC: Use AI-Generated Title if present (starts with # ), otherwise fallback to default
            if reply.startswith("# "):
                 full_body = reply # Use AI's structure entirely
            else:
                 full_body = f"{report_title}\n\n" + reply # Fallback to default header
                 
        except Exception as e:
            print(f"Synthesis error: {e}")
            full_body = f"{report_title}\n(Synthesis failed, showing raw batched reports)\n" + combined_raw_analysis
    else:
        # Single batch processing
        reply = chunk_results[0].replace(f"### Analysis of Sources 1-{len(req.articles)}", "").strip()
        
        # TITLE LOGIC: Use AI-Generated Title if present (starts with # ), otherwise fallback to default
        if reply.startswith("# "):
             full_body = reply 
        else:
             full_body = f"{report_title}\n\n" + reply

    # Combine Body + Index
    final_markdown = full_body + source_index_md
    
    return {"summary": final_markdown}

class AnalyticsRequest(BaseModel):
    articles: List[dict]
    city: str = "Unknown City"

@router.post("/outlets/digest/analytics")
async def generate_analytics(req: AnalyticsRequest, current_user: User = Depends(get_current_user)):
    if not req.articles:
        return []
        
    api_key = current_user.gemini_api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="Missing Gemini API Key. Please set it in Settings.")
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash-exp', generation_config={"response_mime_type": "application/json"})
    
    # Remove Article Cap; Use MapReduce
    BATCH_SIZE = 50 
    
    # Split articles into batches
    batches = [req.articles[i:i + BATCH_SIZE] for i in range(0, len(req.articles), BATCH_SIZE)]
    print(f"Analytics: Processing {len(req.articles)} articles in {len(batches)} batches.")

    all_keywords_map = {} # Key: word_lower, Value: {word, translation, importance_sum, count, sentiment_counts, source_ids_set}

    async def process_batch(batch_idx, batch_articles):
        context = ""
        for idx, art in enumerate(batch_articles):
            global_idx = (batch_idx * BATCH_SIZE) + idx
            txt = art.get('content_summary', '') or art.get('title', '')
            src = art.get('source', 'Unknown')
            context += f"SOURCE_ID_{global_idx}: {src} - {txt}\n"

        prompt = f"""
        Analyze these articles regarding '{req.city}'.
        
        DATA:
        {context}
        
        TASK:
        Extract AT LEAST 200 (TWO HUNDRED) distinct keywords/entities/topics from this batch.
        Aim for 5-7 meaningful keywords for EACH article.
        
        STRATEGY:
        - Include MAJOR THEMES (to capture dominant trends).
        - Include SPECIFIC DETAILS (names, places, unique IDs) to ensure count diversity after deduplication.
        
        Focus on specific:
        - People (Politicians, CEOs, Activists)
        - Organizations (Companies, Parties, Groups)
        - Locations (Cities, Specific Buildings)
        - Events (Protests, Laws, Meetings, Scandals)
        
        Filter out generic media terms (e.g. "News", "Report", "Update", "Article", "Journal").
        
        For each keyword:
        1. Score importance (0-100).
        2. Determine sentiment: Positive, Negative, or Neutral.
        3. Provide English 'translation' (or same word).
        4. List source IDs (e.g. SOURCE_ID_5) where this keyword appears.
        
        OUTPUT JSON:
        [
          {{ "word": "Term", "translation": "Term", "importance": 90, "sentiment": "Neutral", "source_ids": ["SOURCE_ID_X"] }}
        ]
        """
        try:
            response = await model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
            text = response.text
            # Clean JSON
            if text.strip().startswith("```"):
                text = text.strip().split("\n", 1)[1]
                if text.strip().endswith("```"):
                     text = text.strip().rsplit("\n", 1)[0]
            
            return json.loads(text)
        except Exception as e:
            print(f"Batch {batch_idx} failed: {e}")
            return []

    # Run Batches in Parallel
    tasks = [process_batch(i, b) for i, b in enumerate(batches)]
    results = await asyncio.gather(*tasks)

    # REDUCE / COMBINE
    for batch_res in results:
        for kw in batch_res:
            w = kw.get('word', '').strip()
            if not w: continue
            k = w.lower()
            
            if k not in all_keywords_map:
                all_keywords_map[k] = {
                    "word": w,
                    "translation": kw.get("translation", w),
                    "importance_sum": 0,
                    "count": 0,
                    "sentiments": {"Positive": 0, "Negative": 0, "Neutral": 0},
                    "source_ids": set() # Store JSON strings of article metadata
                }
            
            entry = all_keywords_map[k]
            entry["importance_sum"] += kw.get("importance", 50)
            entry["count"] += 1
            
            s = kw.get("sentiment", "Neutral")
            if s in entry["sentiments"]: entry["sentiments"][s] += 1
            
            # Map Source ID back to Article Object
            for sid in kw.get("source_ids", []):
                try:
                    # Robust Regex Extraction (Handles formatting variations)
                    match = re.search(r"SOURCE_ID_(\d+)", str(sid), re.IGNORECASE)
                    if match:
                         idx = int(match.group(1))
                         if 0 <= idx < len(req.articles):
                              art = req.articles[idx]
                              # Store as JSON string for deduplication in Set
                              meta = json.dumps({"title": art.get('title'), "url": art.get('url'), "source": art.get('source')})
                              entry["source_ids"].add(meta)
                except:
                    continue

    # Finalize List
    final_keywords = []
    for k, v in all_keywords_map.items():
        # Decode Sources
        sources = [json.loads(s) for s in v["source_ids"]]
        
        # FILTER ORPHANS: If no sources mapped, skip this keyword to prevent "0 sources" bug
        if not sources: 
            continue

        # Average importance
        avg_imp = int(v["importance_sum"] / v["count"])
        
        # Majority Sentiment
        best_sent = max(v["sentiments"], key=v["sentiments"].get)
        
        final_keywords.append({
            "word": v["word"],
            "translation": v["translation"],
            "importance": avg_imp,
            "sentiment": best_sent,
            "sources": sources
        })
        
    # Sort by importance
    final_keywords.sort(key=lambda x: x['importance'], reverse=True)
    

    return {"keywords": final_keywords}

@router.post("/outlets/digest/stream")
async def generate_digest_stream(req: DigestRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Streams log updates and final result as NDJSON.
    """
    
    async def process_stream():
        # Queue for cross-task communication
        stream_queue = asyncio.Queue()
        
        # Callback wrapper to put logs into queue
        async def queue_logger(msg: str):
            await stream_queue.put({"type": "log", "message": msg})

        yield json.dumps({"type": "log", "message": "Initializing Secure Pipeline..."}) + "\n"
        
        # SESSION FIX: Create local session for stream lifespan
        rules_map = {}
        outlets = []
        
        # Stream-level Deduplication State
        stream_seen_fingerprints = set()
        
        try:
             # Explicit internal imports to prevent any scope weirdness
             import traceback
             import hashlib # Added for deduplication fingerprinting
             from sqlalchemy import select
             from models import NewsOutlet, ScraperRule
             
             async with AsyncSessionLocal() as session:
                 with open("stream_debug.log", "a") as f: f.write(f"\n=== STREAM INIT IDS: {req.outlet_ids} ===\n")
                 
                 # 1. Fetch Outlets
                 stmt = select(NewsOutlet).where(NewsOutlet.id.in_(req.outlet_ids))
                 result = await session.execute(stmt)
                 outlets = result.scalars().all()
                 
                 with open("stream_debug.log", "a") as f: f.write(f"DEBUG: Found {len(outlets)} outlets.\n")
                 
                 if not outlets:
                      yield json.dumps({"type": "error", "message": "No outlets found"}) + "\n"
                      return
    
                 # 2. Fetch Spam Rules (User Feedback)
                 from models import SpamFeedback
                 stmt_spam = select(SpamFeedback)
                 res_spam = await session.execute(stmt_spam)
                 spam_records = res_spam.scalars().all()
                 
                 spam_urls = {s.url for s in spam_records if s.url}
                 spam_titles_lower = {s.title.lower() for s in spam_records if s.title}
                 
                 yield json.dumps({"type": "log", "message": f"Loaded {len(spam_records)} spam signatures..."}) + "\n"

                 # 3. Fetch Scraper Rules
                 stmt_rules = select(ScraperRule)
                 res_rules = await session.execute(stmt_rules)
                 all_rules = res_rules.scalars().all()
                 
                 for r in all_rules:
                     try:
                         rules_map[r.domain] = json.loads(r.config_json)
                     except: pass
                 
                 yield json.dumps({"type": "log", "message": f"Loaded {len(rules_map)} custom rules..."}) + "\n"
                 yield json.dumps({"type": "log", "message": f"Targeting {len(outlets)} sources..."}) + "\n"
                 
                 # EXPUNGE to allow usage after session closes
                 for o in outlets:
                     session.expunge(o)

        except Exception as e:
             err = f"DB FETCH ERROR: {str(e)}\n"
             try:
                 err += traceback.format_exc()
             except: err += " (Traceback failed)"
             
             print(err)
             try:
                 with open("stream_debug.log", "a") as f: f.write(err)
             except: pass
             yield json.dumps({"type": "error", "message": f"System Error: {str(e)}"}) + "\n"
             return
        
        # WORKER FUNCTION
        async def scraper_worker():
            try:
                with open("stream_debug.log", "a") as f: f.write("DEBUG: Worker Started (Parallel Mode).\n")
                
                # Concurrency Limit (5 concurrent outlets)
                sem = asyncio.Semaphore(5)
                
                async def process_outlet(outlet):
                    async with sem:
                        try:
                             with open("stream_debug.log", "a") as f: f.write(f"DEBUG: Processing {outlet.name}...\n")
                             # Find Rule
                             from urllib.parse import urlparse
                             domain = urlparse(outlet.url).netloc.replace("www.", "").lower()
                             rule_config = rules_map.get(domain)

                             # Fallback check (e.g. root domain)
                             if not rule_config:
                                 parts = domain.split('.')
                                 if len(parts) > 2:
                                     root = ".".join(parts[-2:])
                                     rule_config = rules_map.get(root)

                             # Verbose Log to Stream
                             has_rule = "YES" if rule_config else "NO"
                             await stream_queue.put({"type": "log", "message": f"Processing {outlet.name} (Rule: {has_rule})..."})

                             # Pass queue_logger which is Awaitable (not a generator)
                             # Pass current_user.gemini_api_key for AI Navigation
                             res = await smart_scrape_outlet(outlet, req.category, req.timeframe, log_bus=queue_logger, api_key=current_user.gemini_api_key, scraper_rule_config=rule_config)
                                                     
                             if res.get("articles"):
                                  raw_arts = res["articles"]
                                  new_arts = []
                                  
                                  # STRICT DEDUPLICATION
                                  for art in raw_arts:
                                       # Handle both Dict and Object (Pydantic)
                                       title = art.get('title', '') if isinstance(art, dict) else getattr(art, 'title', '')
                                       url = art.get('url', '') if isinstance(art, dict) else getattr(art, 'url', '')
                                       
                                       # Normalize: Strip whitespace, strip query params from URL
                                       # Normalize: Strip whitespace, strip query params, strip protocol/www/trailing slash
                                       import re
                                       clean_title = str(title).strip().lower()
                                       # Remove https://, http://, www.
                                       clean_url = str(url).split('?')[0].split('#')[0].strip().lower()
                                       clean_url = re.sub(r'^https?://(www\.)?', '', clean_url).strip('/')
                                       
                                       # Log for debug
                                       # await stream_queue.put({"type": "log", "message": f"Dedupe Check: {clean_url}"})
                                       
                                       # Compute fingerprint
                                       fp = hashlib.md5((clean_title + clean_url).encode()).hexdigest()
                                       if fp in stream_seen_fingerprints:
                                            continue # Skip duplicate
                                       
                                       # Database Spam Check (using set for speed)
                                       # Assuming spam_records is a list of objects, we need a fast lookup.
                                       # The earlier code loaded a set? No, verify_outlets.py logic...
                                       # Let's trust the SpamFeedback we loaded earlier? 
                                       # Wait, I didn't see spam_records being used in previous code view.
                                       # Let's just restore deduplication for now.
                                       
                                       stream_seen_fingerprints.add(fp)
                                       new_arts.append(art)
                                  
                                  if not new_arts:
                                       return # Nothing new from this source
                                  
                                  # INCREMENTAL AI VERIFICATION (Fixes Timeout Issue)
                                  if req.category == "Politics" and current_user.gemini_api_key:
                                       await stream_queue.put({"type": "log", "message": f"🤖 AI Verifying {len(new_arts)} items from {outlet.name}..."})
                                       
                                       # Create title map for batch verification
                                       titles_map = {i: a.title for i, a in enumerate(new_arts)}
                                       
                                       try:
                                            # Call the debug function we fixed earlier
                                            verdicts, err_msg, raw_ai_log = await batch_verify_titles_debug(
                                                 titles_map, 
                                                 POLITICS_OPERATIONAL_DEFINITION, # Ensure this is available in scope
                                                 current_user.gemini_api_key
                                            )
                                            
                                            if err_msg:
                                                 await stream_queue.put({"type": "log", "message": f"⚠️ AI Batch Error: {err_msg}"})
                                            
                                            # Log Raw AI output to stream for debugging
                                            if raw_ai_log:
                                                 short_log = raw_ai_log.replace('\n', ' ')[:200]
                                                 await stream_queue.put({"type": "log", "message": f"🤖 AI RAW: {short_log}..."})

                                            # Apply Verdicts
                                            for i, art in enumerate(new_arts):
                                                 k = str(i) # keys returned as strings
                                                 if k in verdicts:
                                                      v = verdicts[k]
                                                      is_verified = v.get("verdict", False)
                                                      art.ai_verdict = "VERIFIED" if is_verified else "REJECTED"
                                                      if v.get("translated"):
                                                           art.translated_title = v.get("translated")
                                       except Exception as e:
                                            await stream_queue.put({"type": "log", "message": f"⚠️ AI Check Error: {e}"})

                                  # INCREMENTAL SEND
                                  await stream_queue.put({"type": "data", "articles": new_arts})
                                  await stream_queue.put({"type": "log", "message": f"Found {len(new_arts)} articles from {outlet.name}"})
                             
                             if res.get("timeline_events"):
                                  await stream_queue.put({"type": "timeline", "source": outlet.name, "events": res["timeline_events"]})

                        except Exception as e:
                             print(f"DEBUG: Error processing outlet {outlet.name}: {e}")
                             await stream_queue.put({"type": "log", "message": f"⚠️ Error processing {outlet.name}: {str(e)}"})
                             # Do NOT crash the worker, just fail this outlet

                # Run in Parallel
                tasks = [process_outlet(o) for o in outlets]
                await asyncio.gather(*tasks)
                
                # Signal phase change
                print(f"DEBUG: WORKER FINISHED.")
            except Exception as e:
                print(f"DEBUG: WORKER ERROR: {e}")
                tb_str = traceback.format_exc()
                print(tb_str)
                await stream_queue.put({"type": "error", "message": f"Worker Critical: {e}"})
                await stream_queue.put({"type": "log", "message": f"TRACE:\n{tb_str}"})
            finally:
                await stream_queue.put(None) # Sentinel

        # Start Worker
        task = asyncio.create_task(scraper_worker())
        
        all_articles = []
        all_timeline_events = {} # Map[Source, Events]
        
        # Consumer Loop
        yield json.dumps({"type": "log", "message": "🔵 STREAM CONNECTED (v0.113 - DATE FIX)"}) + "\n"
        
        # SEND EXPECTED METADATA (Fixes "Unknown" User)
        yield json.dumps({
            "type": "meta",
            "owner_id": current_user.id,
            "owner_username": current_user.username
        }) + "\n"
        
        while True:
            try:
                # Keep-alive: If no data for 20s (e.g. valid long processing), send a ping
                item = await asyncio.wait_for(stream_queue.get(), timeout=20.0)
            except asyncio.TimeoutError:
                yield json.dumps({"type": "ping"}) + "\n"
                continue

            if item is None:
                break
            
            if item["type"] == "log":
                yield json.dumps(item) + "\n"
            elif item["type"] == "error":
                yield json.dumps(item) + "\n"
            elif item["type"] == "data":
                new_articles = item["articles"]
                all_articles.extend(new_articles)
                print(f"DEBUG: CONSUMER RECEIVED {len(new_articles)} NEW ARTICLES (Total: {len(all_articles)})")
                
                # IMMEDIATE PARTIAL YIELD per user request for incremental updates
                try:
                     # CALCULATE FRESHNESS LOCALLY FOR INCREMENTAL UPDATE (Fixes Red Dates)
                     # We must replicate the cutoff logic here because the final loop hasn't run yet.
                     from datetime import datetime, timedelta
                     now = datetime.now()
                     cutoff_date = now - timedelta(days=1)
                     if req.timeframe == "3days": cutoff_date = now - timedelta(days=3)
                     elif req.timeframe == "1week": cutoff_date = now - timedelta(days=7)
                     elif req.timeframe == "1month": cutoff_date = now - timedelta(days=30)
                     
                     # HARD CUTOFF (5x Timeframe) - Reject outright
                     hard_cutoff_date = now - timedelta(days=5) # 24h -> 5 days
                     if req.timeframe == "3days": hard_cutoff_date = now - timedelta(days=14)
                     elif req.timeframe == "1week": hard_cutoff_date = now - timedelta(days=30)
                     elif req.timeframe == "1month": hard_cutoff_date = now - timedelta(days=60)
                     
                     for art in new_articles:
                         if art.date_str:
                             try:
                                 d_obj = datetime.strptime(art.date_str, "%Y-%m-%d")
                                 d_obj = datetime.strptime(art.date_str, "%Y-%m-%d")
                                 
                                 # STRICT FILTER: Discard if older than Hard Cutoff
                                 if d_obj < hard_cutoff_date:
                                     continue

                                 is_fresh = d_obj >= cutoff_date
                                 
                                 # Ensure scores dict exists
                                 if not art.scores: art.scores = {}
                                 
                                 art.scores["is_fresh"] = is_fresh
                                 art.scores["date"] = 30 if is_fresh else 0
                                 
                                 if is_fresh and "is_fresh" not in art.scores:
                                      # Force update if missing
                                      art.scores["is_fresh"] = True
                             except: pass

                     # Convert Pydantic models to dicts for JSON serialization
                     # Re-filter new_articles to exclude dropped ones
                     final_articles = []
                     
                     # Hard Junk Filter Terms (Generic)
                     JUNK_TERMS = ["site relocation"] # Kept minimal as per user feedback

                     for a in new_articles:
                         try:
                             # 1. Deduplication (Stream Level)
                             norm_title = a.title.lower().strip()
                             norm_url = a.url.split('?')[0].rstrip('/')
                             fingerprint = f"{norm_title}|{norm_url}"
                             if norm_title in stream_seen_fingerprints or fingerprint in stream_seen_fingerprints:
                                 continue
                                 continue
                             stream_seen_fingerprints.add(norm_title)
                             stream_seen_fingerprints.add(fingerprint)

                             # 2. Hard Junk Filter (Generic + User Marked Spam)
                             # Generic Terms
                             if "site relocation" in norm_title or "moved" in norm_title: continue
                             
                             # User Marked Spam
                             if a.url in spam_urls or norm_title in spam_titles_lower:
                                  print(f"DEBUG: Rejected SPAM {a.title}")
                                  continue

                             # 3. Hard Date Cutoff
                             if a.date_str:
                                 d_obj = datetime.strptime(a.date_str, "%Y-%m-%d")
                                 if d_obj < hard_cutoff_date: continue
                             
                             final_articles.append(a)
                         except:
                             final_articles.append(a)

                     serializable_new = [a.dict() for a in final_articles]
                     yield json.dumps({
                         "type": "partial_articles", 
                         "articles": serializable_new, 
                         "category": req.category
                     }, default=str) + "\n"
                     yield json.dumps({"type": "log", "message": f"Streaming {len(new_articles)} new items to frontend..."}) + "\n"
                except Exception as e:
                     print(f"Serialization Error: {e}")
                     yield json.dumps({"type": "log", "message": "⚠️ Error streaming partial batch."}) + "\n"

                yield json.dumps({"type": "log", "message": f"Accumulated {len(all_articles)} items..."}) + "\n"
            elif item["type"] == "timeline":
                all_timeline_events[item["source"]] = item["events"]
        
        print(f"DEBUG: CONSUMER EXITED LOOP. Total Articles: {len(all_articles)}")
        yield json.dumps({"type": "log", "message": "✅ Scraping finished. Starting Post-Processing & AI Check..."}) + "\n"
        
        # --- POST-PROCESSING SAFETY WRAPPER ---
        # Wrap ALL scoring/filtering/AI logic to catch silent crashes (e.g. from bad dates/NoneTypes)
        try:
            # Generate Master Timeline
            try:
                 scraper_engine.generate_master_timeline(all_timeline_events)
            except Exception as e:
                 print(f"Master Timeline Error: {e}")
        
            await task # Ensure clean exit check

            # ... (Rest of logic: Scoring, Rescue, AI)
            
            # COPY OF THE DIGEST LOGIC (REFACTORED)
            
            yield json.dumps({"type": "log", "message": "Ranking & Scoring Articles..."}) + "\n"
            
            # 0. Timeframe Calculation
            # 0. Timeframe Calculation
            from datetime import datetime, timedelta
            now = datetime.now()
            
            # Primary Cutoff (Green vs Red Date)
            cutoff_date = now - timedelta(days=1) # Default 24h
            
            # Hard Cutoff (5x Timeframe) - Articles older than this are DISCARDED
            hard_cutoff_date = now - timedelta(days=5) # 24h -> 5 days
            
            if req.timeframe == "3days":
                cutoff_date = now - timedelta(days=3)
                hard_cutoff_date = now - timedelta(days=14) # 3d -> 2 weeks
            elif req.timeframe == "1week":
                cutoff_date = now - timedelta(days=7)
                hard_cutoff_date = now - timedelta(days=30) # 7d -> 1 month
                
            with open("stream_debug.log", "a") as f: 
                 f.write(f"DEBUG: Timeframe {req.timeframe}. Hard Cutoff: {hard_cutoff_date.date()}\n")
                
            yield json.dumps({"type": "log", "message": f"Timeframe: {req.timeframe} (Cutoff: {cutoff_date.date()})"}) + "\n"

            candidates_for_ai = []
            filtered_articles = [] # Final list
            analysis_source = [] # We skip detailed keyword analysis for stream to save time/quota

            total_scraped = len(all_articles)
            yield json.dumps({"type": "log", "message": f"Scoring {total_scraped} raw articles..."}) + "\n"
            
            # Helper lists
            BLOCKED_DOMAINS = ["google.com", "apple.com", "youronlinechoices", "facebook.com", "twitter.com", "instagram.com", "tiktok.com", "youtube.com"]
            SUSPICIOUS_TERMS = [
                "recipe", "retet", "receta", "recette", "rezept", "ricett", "mancare", "food", "kitchen", "bucatarie", "essen", "cucina",
                "horoscop", "horoscope", "horoskop", "zodiac", "zodiaque", "astrology",
                "can-can", "cancan", "paparazzi", "gossip", "tabloid", "klatsch", "potins", "cookie", "gdpr", "privacy", "termeni", "conditii"
            ]
            NOISE_TERMS = [
                "apa calda", "apa rece", "intrerupere", "avarie", "curent", "electricitate",
                "trafic", "restrictii", "accident", "incendiu", "minor", "program",
                "meteo", "vremea", "prognoza", "cod galben", "cod portocaliu"
            ]

            # DEDUPLICATION SETS
            seen_urls = set()
            seen_titles = set()
            unique_articles = []
            
            for article in all_articles:
                 # URL Normalization for Dedupe
                 norm_url = article.url.split("?")[0].rstrip("/")
                 if norm_url in seen_urls: continue
                 
                 # Title Dedupe (Simple lowercasing)
                 norm_title = article.title.lower().strip()
                 if norm_title in seen_titles: continue
                 
                 seen_urls.add(norm_url)
                 seen_titles.add(norm_title)
                 
                 # SPAM BLOCK
                 if any(d in article.url for d in BLOCKED_DOMAINS): continue
                 # CATEGORY BLOCK
                 if "/category/" in article.url or "/page/" in article.url or "/tag/" in article.url or "/eticheta/" in article.url or "/author/" in article.url or "/autor/" in article.url: continue
                
                 # Find Source Outlet for strict filtering
                 source_outlet = next((o for o in outlets if o.name == article.source), None)
                 if source_outlet and "#" in article.url and article.url.split("#")[0] == source_outlet.url: continue

                 # SCORING
                 topic_score = 0
                 title_lower = article.title.lower()
                 url_lower = article.url.lower()
                 
                 # ... (reusing existing scoring logic) ...
                 # Simple heuristic for category matching
                 if req.category.lower() in title_lower or req.category.lower() in url_lower:
                     topic_score += 30
                     
                 # Contextual URL Boost
                 cat_stem = req.category.lower()[:4] 
                 if f"/{cat_stem}" in url_lower:
                      topic_score += 20
                      
                 # Generic "Admin" boost
                 if req.category in ["Politics", "Admin"]:
                     if any(k in title_lower for k in ["primar", "consiliu", "presedinte", "ministru", "guvern", "parlament"]):
                         topic_score += 40
                     elif any(k in title_lower for k in ["scandal", "acuzatii", "demisie", "alegeri"]):
                         topic_score += 50
                     elif "sibi" in title_lower:
                         topic_score += 10
                 
                 # EXPLICIT PENALTIES
                 if req.category.lower() not in ["local", "general", "all"]:
                      if any(n in title_lower for n in NOISE_TERMS):
                          topic_score -= 50

                 # Penalize Off-Topic
                 if any(term in title_lower for term in SUSPICIOUS_TERMS) or any(term in url_lower for term in SUSPICIOUS_TERMS):
                      topic_score -= 100
                 
                 # Date Logic (STRICT FILTER)
                 date_score = 0
                 is_within_timeframe = False
                 
                 if article.date_str:
                      try:
                           # STRICT LIFESPAN CHECK: Discard if older than Hard Cutoff
                           d_obj = datetime.strptime(article.date_str, "%Y-%m-%d")
                           
                           if d_obj < hard_cutoff_date:
                               # Article is too old for this digest scope
                               continue

                           # Standard Green/Red Scoring
                           if d_obj >= cutoff_date:
                               date_score = 30
                               is_within_timeframe = True
                      except: pass
                
                 total_score = topic_score 
                 
                 # Date Bonus/Penalty
                 if is_within_timeframe:
                     date_score = 30
                     total_score += date_score
                 elif article.date_str:
                     # INVALID DATE (Old) -> Strict Rejection as requested
                     date_score = 0
                     total_score = 0 
                 else:
                     # Undated -> Allow (maybe?) or Strict? 
                     # User said "check the dates... mark ones outside with red".
                     # Implies strictly checking KNOWN dates.
                     # If date is unknown, we can't be sure it's outside.
                     # Let's keep undated as "neutral" (0 bonus) but ALLOWED if topic is high to avoid empty report again.
                     date_score = 0
                 
                 article.relevance_score = int(total_score)
                 # Inject Metadata for Frontend
                 article.scores = {
                     "topic": topic_score, 
                     "date": date_score, 
                     "is_fresh": is_within_timeframe,
                     "is_old": (article.date_str and not is_within_timeframe)
                 }
                 
                 # Filter thresholds (Keep permissive but transparent)
                 # User wants EVERYTHING in the table
                 unique_articles.append(article)

            # AI TITLE PRE-FILTER
            # Filter logic:
            # 1. Take top candidates (e.g. all unique_articles which passed heuristic, or top N)
            # 2. Batch verify titles
            # 3. Filter out rejections OR Penalize
            
            candidates_to_verify = unique_articles # For now verify all that passed basic filters
        
            # LOG API KEY STATUS
            has_key = bool(current_user.gemini_api_key)
            yield json.dumps({"type": "log", "message": f"🔍 AI Check Prepared: {len(candidates_to_verify)} candidates. API Key Present: {has_key}"}) + "\n"
            
            if candidates_to_verify and current_user.gemini_api_key:
                 yield json.dumps({"type": "log", "message": f"🤖 AI Pre-Filtering {len(candidates_to_verify)} titles..."}) + "\n"
                 
                 # Prepare batch (Assign IDs for stability)
                 titles_map = {i: art.title for i, art in enumerate(candidates_to_verify)}
                 
                 # Chunking (Gemini has limits, maybe 50 at a time)
                 chunk_size = 10 # Keep small for reliability
                 parallel_limit = 5 # Process 5 batches concurrently
                 verified_results = {}
                 
                 title_ids = list(titles_map.keys())
                 
                 # Pre-calculate all batches
                 all_batches = []
                 for i in range(0, len(title_ids), chunk_size):
                     chunk_ids = title_ids[i:i+chunk_size]
                     chunk_map = {k: titles_map[k] for k in chunk_ids}
                     all_batches.append(chunk_map)
                
                 total_batches = len(all_batches)
                 
                 # Process in Parallel Groups
                 for i in range(0, total_batches, parallel_limit):
                     batch_group = all_batches[i:i+parallel_limit]
                     
                     # Prepare Tasks
                     user_lang = current_user.preferred_language if current_user.preferred_language else "English"
                     tasks = [
                         batch_verify_titles_debug(b, POLITICS_OPERATIONAL_DEFINITION, current_user.gemini_api_key, user_lang)
                         for b in batch_group
                     ]
                     
                     # Process Results as they complete
                     completed_in_group = 0
                     for task in asyncio.as_completed(tasks):
                         res, err, raw_debug = await task
                         completed_in_group += 1
                         
                         if raw_debug:
                              # Send a snippet of the raw AI response to frontend for debugging
                              short_debug = raw_debug.replace('\n', ' ')[:200]
                              yield json.dumps({"type": "log", "message": f"🤖 AI RAW: {short_debug}..."}) + "\n"
                         
                         if err:
                              yield json.dumps({"type": "log", "message": f"⚠️ Batch AI Error: {err}"}) + "\n"
                         else:
                              verified_results.update(res)
                         
                         
                         # Granular Heartbeat
                         current_total = i + completed_in_group
                         msg = f"Verified batches {current_total}/{total_batches} ({len(verified_results)} verified)..."
                         yield json.dumps({"type": "log", "message": msg}) + "\n"
                         
                         try:
                             with open("stream_debug.log", "a") as f: f.write(f"DEBUG: {msg}\n")
                         except: pass
                 
                 with open("stream_debug.log", "a") as f: f.write("DEBUG: Exited AI loop normally.\n")
                 
                 # Apply verdicts & Translation
                 with open("stream_debug.log", "a") as f: f.write(f"DEBUG: Processing verdicts for {len(candidates_to_verify)} candidates...\n")
                 
                 for i, art in enumerate(candidates_to_verify):
                     if i % 50 == 0:
                          with open("stream_debug.log", "a") as f: f.write(f"DEBUG: Applied verdicts for {i} articles...\n")
                     
                     # Result keys are strings in JSON
                     data = verified_results.get(str(i), verified_results.get(i))
                     
                     # Handle new Dict vs old Bool structure (Just in case)
                     verdict = False
                     translated = None
                     
                     if isinstance(data, bool):
                         verdict = data
                     elif isinstance(data, dict):
                         verdict = data.get("verdict", False)
                         translated = data.get("translated")
                     
                     # Store Translation
                     if translated:
                         art.translated_title = translated

                     if verdict is True:
                         # CONFIRMED POLITICS
                         art.relevance_score += 20 # Bonus
                         art.ai_verdict = "VERIFIED"
                     elif verdict is False:
                         # CONFIRMED NOT POLITICS
                         art.relevance_score -= 10 # Penalty but keep
                         art.ai_verdict = "REJECTED"
                     else:
                         # Error/Missing
                         art.ai_verdict = "UNKNOWN"
            else:
                 yield json.dumps({"type": "log", "message": "⚠️ Skipping AI Filter (No API Key or No Candidates)"}) + "\n"
            
            # POST-TRANSLATION DEDUPLICATION
            # Remove duplicates that became identical after translation
            final_articles = []
            seen_final_titles = set()
            
            for art in unique_articles:
                # Use translated title for check if available
                check_title = (art.translated_title or art.title).lower().strip()
                # Remove basic punctuation for fuzzy match
                import string
                check_title = check_title.translate(str.maketrans('', '', string.punctuation))
                
                if check_title in seen_final_titles:
                     continue
                
                seen_final_titles.add(check_title)
                final_articles.append(art)
                
            filtered_articles = final_articles
            
            with open("stream_debug.log", "a") as f: f.write(f"DEBUG: AI Loop Done. Filtering {len(filtered_articles)} articles (Deduped from {len(unique_articles)}).\n")

            # FINAL COMPILE
            yield json.dumps({"type": "log", "message": "Compiling HTML Digest..."}) + "\n"
            with open("stream_debug.log", "a") as f: f.write("DEBUG: Starting Table Generation...\n")
            
            # Create HTML Table
            
            start_str = cutoff_date.strftime("%b %d")
            end_str = now.strftime("%b %d")
            period_label = f"{start_str} - {end_str}"
            table_html = f"<h1 style='color: #e2e8f0; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; margin-bottom: 20px;'>Deep Analysis: {req.category} <span style='font-size:0.6em; color:#94a3b8;'>({period_label})</span></h1>"
            
            # Grouping
            outlet_articles_map = {o.name: [] for o in outlets}
            for article in filtered_articles:
                if article.source in outlet_articles_map:
                    outlet_articles_map[article.source].append(article)
            
            # Sort Outlets
            sorted_outlets = sorted(outlets, key=lambda o: max([a.relevance_score for a in outlet_articles_map[o.name]] or [0]), reverse=True)
            
            for outlet in sorted_outlets:
                arts = outlet_articles_map.get(outlet.name, [])
                if not arts: continue
                
                # Split Articles into Fresh and Stale
                fresh_articles = []
                stale_articles = []
                
                for art in arts:
                    if art.scores.get('is_fresh'):
                        fresh_articles.append(art)
                    else:
                        stale_articles.append(art)
                
                # Helper for Date Sorting
                def get_sort_key(x):
                    # Primary: Date (Newest First)
                    # Secondary: Relevance Score (Highest First)
                    d_val = datetime.min
                    if x.date_str:
                        try:
                            # Attempt to parse standard format
                            d_val = datetime.strptime(x.date_str, "%Y-%m-%d")
                        except:
                            pass # Keep as min date if parsing fails
                            
                    return (d_val, x.relevance_score)

                # Sort both lists
                try:
                    fresh_articles.sort(key=get_sort_key, reverse=True)
                    stale_articles.sort(key=get_sort_key, reverse=True)
                except Exception as e:
                    # Log but continue if sorting fails
                    print(f"Sorting Error: {e}")
                    pass

                # Helper to Render Rows
                def render_article_rows(article_list):
                    rows = ""
                    for art in article_list:
                        s = art.scores
                        topic_display = f"{s.get('topic', 0)}"
                        date_color = "#4ade80" if s.get('is_fresh') else "#7f1d1d"
                        date_display = f"<span style='color: {date_color}; font-weight: bold;'>{art.date_str}</span>" if art.date_str else f"<span style='color: #94a3b8;'>N/A</span>"
                        date_display += f"""<span class="scraper-debug-trigger" data-url="{art.url}" style="cursor: pointer; margin-left: 6px; font-size: 0.8em; opacity: 0.6;" title="Debug Date Extraction">🔧</span>"""

                        # Score Styling
                        if art.relevance_score > 80:
                            score_bg = "#052e16"; score_text = "#4ade80"; score_border = "#15803d"
                        elif art.relevance_score > 50:
                            score_bg = "#422006"; score_text = "#facc15"; score_border = "#a16207"
                        else:
                            score_bg = "#450a0a"; score_text = "#f87171"; score_border = "#b91c1c"
                        
                        safe_url = html.escape(art.url); safe_title = html.escape(art.title)
                        
                        # Translation Logic
                        title_html = f'<span class="title-original">{safe_title}</span>'
                        if art.translated_title:
                            safe_trans = html.escape(art.translated_title)
                            title_html += f'<span class="title-translated" style="display: none; color: #fbbf24; font-style: italic;">{safe_trans}</span>' # Yellow styling for translation

                        # Manual Assess Button
                        score_badge = f"""
                        <button class="politics-assess-trigger" data-url="{safe_url}" data-title="{safe_title}"
                                style="display: inline-flex; align-items: center; gap: 4px; background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; padding: 4px 8px; border-radius: 6px; font-weight: bold; font-size: 0.7rem; cursor: pointer; transition: all 0.2s;"
                                onmouseover="this.style.backgroundColor='#334155'; this.style.color='white';"
                                onmouseout="this.style.backgroundColor='#1e293b'; this.style.color='#94a3b8';">
                            🤖 Assess
                        </button>
                        """
                        
                        # AI Status Column Logic
                        verdict_icon = "❓"
                        if hasattr(art, 'ai_verdict'):
                            if art.ai_verdict == "VERIFIED": verdict_icon = "✅"
                            elif art.ai_verdict == "REJECTED": verdict_icon = "❌"
                            elif art.ai_verdict == "UNKNOWN": verdict_icon = "❓"
                        
                        rows += f"""
                        <tr style="border-bottom: 1px solid #1e293b; transition: background-color 0.2s;">
                            <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b;">{score_badge}</td>
                            <td style="padding: 12px 16px; text-align: center; border-bottom: 1px solid #1e293b;">{verdict_icon}</td>
                            <td style="padding: 12px 16px; text-align: center; border-bottom: 1px solid #1e293b; white-space: nowrap;">{date_display}</td>
                            <td style="padding: 12px 16px; text-align: center; border-bottom: 1px solid #1e293b;">{topic_display}</td>
                            <td style="padding: 12px 16px; border-bottom: 1px solid #1e293b;">
                                <a href="{safe_url}" target="_blank" style="color: #e2e8f0; text-decoration: none; font-weight: 500; display: block; margin-bottom: 4px;">{title_html}</a>
                            </td>
                        </tr>
                        """
                    return rows

                table_html += f"""
                <div style="margin-top: 32px; margin-bottom: 16px; border-bottom: 1px solid #334155; padding-bottom: 8px;">
                    <h3 style="margin: 0; font-size: 1.4rem; color: #f8fafc;">
                        <a href="{outlet.url}" target="_blank" style="color: #60a5fa; text-decoration: none; font-weight: bold;">{outlet.name}</a>
                        <span style="color: #94a3b8; font-size: 1rem; font-weight: normal; margin-left: 10px;">({outlet.city})</span>
                        <span class="scraper-debug-trigger" data-url="{outlet.url}" style="cursor: pointer; font-size: 0.8em; margin-left: 8px; vertical-align: middle; opacity: 0.5;" title="Debug Scraper Rules">🔧</span>
                    </h3>
                </div>
                """
                    
                # Table Header
                table_html += """
                <table style="width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.95rem; margin-bottom: 24px; border: 1px solid #334155; border-radius: 6px; overflow: hidden;">
                    <thead style="background-color: #1e293b; color: #e2e8f0;">
                        <tr>
                            <th style="padding: 12px 16px; text-align: left; font-weight: 600; border-bottom: 1px solid #334155;">Assess</th>
                            <th style="padding: 12px 16px; text-align: center; font-weight: 600; border-bottom: 1px solid #334155;">AI Check</th>
                            <th style="padding: 12px 16px; text-align: center; font-weight: 600; border-bottom: 1px solid #334155;">Date</th>
                            <th style="padding: 12px 16px; text-align: center; font-weight: 600; border-bottom: 1px solid #334155;">Topic</th>
                            <th style="padding: 12px 16px; text-align: left; font-weight: 600; border-bottom: 1px solid #334155;">Article</th>
                        </tr>
                    </thead>
                    <tbody style="background-color: #0f172a;">
                """

                # 1. Render Fresh Articles (Main Body)
                table_html += render_article_rows(fresh_articles)
                table_html += "</tbody>"

                # 2. Render Stale Articles (Collapsible)
                if stale_articles:
                    table_html += f"""
                    <tbody style="border-top: 2px solid #334155;">
                        <tr>
                            <td colspan="5" style="padding: 0;">
                                <details style="background-color: #0f172a;">
                                    <summary style="padding: 12px 16px; cursor: pointer; color: #94a3b8; font-size: 0.85rem; font-weight: 600; user-select: none; background-color: #1e293b; border-bottom: 1px solid #334155;">
                                        🔻 Show {len(stale_articles)} Older / Undated Articles
                                    </summary>
                                    <table style="width: 100%; border-collapse: separate; border-spacing: 0;">
                                        {render_article_rows(stale_articles)}
                                    </table>
                                </details>
                            </td>
                        </tr>
                    </tbody>
                    """
                
                table_html += "</table>"
                    
                
            table_html += "</tbody></table>"
            
            try:
                with open("stream_debug.log", "a") as logf:
                    logf.write(f"\n--- NEW STREAM START ---\n")
                    
                    # Send Partial Updates (Split Payload)
                    yield json.dumps({"type": "log", "message": "Sending Digest components..."}) + "\n"
                    logf.write("DEBUG: Sending Partial Digest HTML...\n")
                    
                    # 1. HTML Content
                    html_size_mb = len(table_html) / 1024 / 1024
                    yield json.dumps({"type": "log", "message": f"📦 Generating HTML Digest ({html_size_mb:.2f} MB)..."}) + "\n"
                    logf.write(f"DEBUG: Sending Partial Digest HTML ({html_size_mb:.2f} MB)...\n")
                    
                    if html_size_mb > 15:
                         yield json.dumps({"type": "log", "message": "⚠️ Warning: Digest is very large, browser may lag."}) + "\n"

                    yield json.dumps({"type": "partial_digest", "html": table_html}, default=str) + "\n"
                    
                    # 2. Analysis Data
                    logf.write("DEBUG: Sending Partial Analysis...\n")
                    yield json.dumps({"type": "partial_analysis", "source": [k.dict() for k in (analysis_source or [])]}, default=str) + "\n"

                    # 3. Articles (Chunked)
                    article_chunk_size = 50
                    total_articles = len(filtered_articles)
                    logf.write(f"DEBUG: Sending {total_articles} articles in chunks of {article_chunk_size}...\n")
                    
                    for i in range(0, total_articles, article_chunk_size):
                         chunk = filtered_articles[i:i+article_chunk_size]
                         logf.write(f"DEBUG: Sending Article Chunk {i//article_chunk_size + 1}...\n")
                         yield json.dumps({
                             "type": "partial_articles", 
                             "articles": [a.dict() for a in chunk], 
                             "category": req.category
                         }, default=str) + "\n"
                         
                         await asyncio.sleep(0.01)

                    # 4. Completion Signal
                    logf.write("DEBUG: Sending DONE signal...\n")
                    yield json.dumps({"type": "done"}) + "\n"
                    logf.write("DEBUG: Stream Finished Successfully.\n")
                
            except Exception as e:
                # Inner Exception (Stream Error)
                with open("stream_debug.log", "a") as logf:
                    logf.write(f"CRITICAL STREAM ERROR: {e}\n")
                    import traceback
                    traceback.print_exc(file=logf)
                
                print(f"CRITICAL STREAM ERROR: {e}")
                yield json.dumps({"type": "error", "message": f"Server Stream Error: {str(e)}"}) + "\n"
        
        except Exception as e:
            # Outer Exception (Post-Processing Crash)
            print(f"DEBUG: Post-Processing Crash: {e}")
            import traceback
            traceback.print_exc()
            
            # Send error to frontend so it stops waiting
            yield json.dumps({"type": "log", "message": f"⚠️ Digest Generation Warning: {str(e)}"}) + "\n"
            yield json.dumps({"type": "error", "message": "Partial Digest Only (Server Error)"}) + "\n"
            
            # If we crashed but sent partial articles, send DONE to render what we have
            if len(all_articles) > 0:
                 yield json.dumps({"type": "done"}) + "\n"

    # yield json.dumps({"type": "log", "message": "Processing..."}) + "\n" # OLD PLACEHOLDER
    
    return StreamingResponse(process_stream(), media_type="application/x-ndjson")

# Existing Endpoint (unchanged for backward compat)
@router.post("/outlets/digest", response_model=DigestResponse)
async def generate_digest(req: DigestRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    (Legacy/Simple) Aggregates news.
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

    # 0. Timeframe Calculation
    from datetime import datetime, timedelta
    now = datetime.now()
    cutoff_date = now - timedelta(days=1) # Default 24h
    if req.timeframe == "3days":
        cutoff_date = now - timedelta(days=3)
    elif req.timeframe == "1week":
        cutoff_date = now - timedelta(days=7)
    
    # Reset cutoff to start of day? No, rolling window is fine or user preference.
    # Let's clean it to be strictly comparative.


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
        if "/category/" in article.url or "/page/" in article.url or "/tag/" in article.url or "/eticheta/" in article.url or "/author/" in article.url or "/autor/" in article.url: continue
        
        # Find Source Outlet for strict filtering
        source_outlet = next((o for o in outlets if o.name == article.source), None)
        
        # Filter out anchor links on same page
        if source_outlet and "#" in article.url and article.url.split("#")[0] == source_outlet.url: continue

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

        # FACTOR 3: DATE (Strict Filtering)
        date_score = 0
        is_within_timeframe = False
        
        if article.date_str:
             try:
                 # Auto-detect format (YYYY-MM-DD usually)
                 # fast parse
                 d_obj = datetime.strptime(article.date_str, "%Y-%m-%d")
                 if d_obj >= cutoff_date:
                     date_score = 30
                     is_within_timeframe = True
             except:
                 pass
        
        # User Rule: 
        # "if the date of an article falls within the digest time frame then multiply the topic-score by 1"
        # "If the date falls outside of the time-frame or the date is N/A the the score is 0"
        
        if is_within_timeframe:
             # Valid Date
             total_score = topic_score + date_score
        else:
             # Invalid / Old Date
             total_score = 0

        article.relevance_score = int(total_score)
        article.scores = {"topic": topic_score, "geo": geo_score, "date": date_score}
        
        # LOGIC:
        # 1. Must have valid Date (score >= 30) AND Topic Score >= 20 (lowered to allow AI to decide)
        # 2. If it passes AI check, it gets in.
        
        if date_score >= 30 and topic_score >= 20:
            # Candidate for AI
            candidates_for_ai.append(article)
        else:
            # Check rule availability efficiently
            from urllib.parse import urlparse
            try:
                 domain_key = urlparse(article.url).netloc.replace("www.", "").lower()
                 has_custom_rule = domain_key in rules_map
            except: 
                 has_custom_rule = False
            
            # Expanded Rescue Condition
            if (topic_score >= 15 or has_custom_rule) and date_score < 30 and topic_score > -50:
                # AI/RULE DATE RESCUE MISSION
                # Relevant topic OR User has custom rule. (But not spam)
                try:
                    print(f"DEBUG: Triggering Rescue for {article.title} (HasRule: {has_custom_rule})")
                    async with httpx.AsyncClient(headers=ROBUST_HEADERS, verify=False, timeout=10) as rescue_client:
                      resp = await robust_fetch(rescue_client, article.url)
                      if resp and resp.status_code == 200:
                           
                           rescued_date = None
                           
                           # 1. Try Rule-Based Extraction
                           from urllib.parse import urlparse
                           domain = urlparse(article.url).netloc.replace("www.", "").lower()
                           rule_config = rules_map.get(domain)
                           
                           if rule_config:
                                rule_obj = scraper_engine.ScraperRule(
                                    domain="custom",
                                    date_selectors=rule_config.get('date_selectors'),
                                    date_regex=rule_config.get('date_regex'),
                                    use_json_ld=rule_config.get('use_json_ld', True)
                                )
                                rescued_date = scraper_engine.extract_date_from_html(resp.text, article.url, custom_rule_override=rule_obj)
                                if rescued_date: print(f"DEBUG: Rule Rescued Date: {rescued_date} (Type: {type(rescued_date)})")

                           # 2. Fallback to AI
                           if not rescued_date:
                                rescued_date = await scraper_engine.extract_date_with_ai(resp.text, article.url, current_user.gemini_api_key)

                           if rescued_date and "429" in str(rescued_date):
                                # RATE LIMIT HIT
                                print(f"  -> Rate Limit 429: {rescued_date}")
                                analysis_source.append(KeywordData(word="RATE_LIMIT", importance=1, type="System:RateLimit", sentiment="Warning"))
                           elif rescued_date:
                                # Validate Rescued Date against Cutoff!
                                try:
                                    # Normalize to datetime
                                    d_obj = None
                                    if isinstance(rescued_date, datetime):
                                        d_obj = rescued_date
                                        # Format to string for article.date_str
                                        rescued_date = d_obj.strftime("%Y-%m-%d")
                                    else:
                                        # Parse string
                                        # Clean potential "YYYY-MM-DDT..."
                                        c_date = str(rescued_date).split("T")[0]
                                        d_obj = datetime.strptime(c_date, "%Y-%m-%d")
                                        rescued_date = c_date

                                    if d_obj >= cutoff_date:
                                         print(f"  -> Rescued Valid Date: {rescued_date}")
                                         article.date_str = rescued_date
                                         # Bump Score
                                         article.relevance_score = topic_score + 30 + 20 
                                         article.scores['date'] = 30
                                         # Now it qualifies for AI verification or basic inclusion
                                         candidates_for_ai.append(article)
                                    else:
                                         print(f"  -> Rescued OLD Date: {rescued_date} (Too Old)")
                                         article.date_str = rescued_date
                                         article.relevance_score = 0 
                                         filtered_articles.append(article) 
                                except:
                                     pass
                           else:
                                # Failed Rescue
                                article.relevance_score = 0 
                                filtered_articles.append(article)
                      else:
                           article.relevance_score = 0
                           filtered_articles.append(article)
                except Exception as e:
                    print(f"Rescue Failed: {e}")
                    article.relevance_score = 0 
                    filtered_articles.append(article)

            elif article.relevance_score > 30 and topic_score > 10:
             # Fallback for "Decently High Score" but maybe weak on specific keywords
             filtered_articles.append(article)


    # Mark heuristically accepted articles as VERIFIED
    for art in filtered_articles:
        if not art.ai_verdict:
            art.ai_verdict = "VERIFIED"

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
                art.ai_verdict = "VERIFIED"
                filtered_articles.append(art)
            else:
                print(f"AI Rejected: {art.title}")
    
    # --- SORTING ---
    # Sort by Date Descending (Newest First)
    def date_sorter(art):
        if not art.date_str: return "0000-00-00"
        return art.date_str
    filtered_articles.sort(key=date_sorter, reverse=True)

    # --- TRANSLATION ---
    if filtered_articles and current_user.gemini_api_key:
        print(f"Translating {len(filtered_articles)} titles...")
        try:
            # Robust Chunked Translation
            # Strategy: Translate Top 100 items PER SOURCE (Fair coverage)
            articles_to_translate = []
            
            # Group by Source
            from collections import defaultdict
            by_source = defaultdict(list)
            for art in filtered_articles:
                by_source[art.source].append(art)
                
            # Take Top 200 from each (Increased from 100 for better coverage)
            LIMIT_PER_SOURCE = 200
            for source, arts in by_source.items():
                # Assumes arts are already sorted by Date (which they are)
                articles_to_translate.extend(arts[:LIMIT_PER_SOURCE])
            
            print(f"Translating {len(articles_to_translate)} articles (Fair Limit: {LIMIT_PER_SOURCE}/source)...")
            
            chunk_size = 25
            chunks = [articles_to_translate[i:i + chunk_size] for i in range(0, len(articles_to_translate), chunk_size)]
            
            genai.configure(api_key=current_user.gemini_api_key)
            model_tr = genai.GenerativeModel('gemini-flash-latest')
            
            async def translate_chunk(i, chunk):
                titles_p = [art.title for art in chunk]
                
                tr_prompt = f"""
                Translate the following news headlines to English. 
                Return a JSON List of Objects with keys "src" (original) and "dst" (translated).
                Input:
                {json.dumps(titles_p, ensure_ascii=False)}
                
                Response Format:
                [{{"src": "Original Title", "dst": "Translated Title"}}, ...]
                """
                
                try:
                    tr_resp = await model_tr.generate_content_async(tr_prompt)
                    tr_text = tr_resp.text.replace("```json","").replace("```","").strip()
                    
                    import re
                    json_match = re.search(r'\[.*\]', tr_text, re.DOTALL)
                    if json_match:
                        raw_list = json.loads(json_match.group(0))
                        
                        # 1. Map by Normalized Key
                        def normalize(s): return re.sub(r'[\W_]+', '', s.lower())
                        
                        tr_map = {normalize(item.get("src", "")): item.get("dst", "").strip() for item in raw_list}
                        
                        # 2. Check alignment for Index Fallback
                        use_index_fallback = (len(raw_list) == len(chunk))
                        
                        for idx, art in enumerate(chunk):
                            norm_title = normalize(art.title)
                            
                            # Try Map
                            if norm_title in tr_map:
                                art.translated_title = tr_map[norm_title]
                            elif use_index_fallback:
                                # Fallback to Index
                                art.translated_title = raw_list[idx].get("dst", "").strip()
                                
                except Exception as e:
                    print(f"Translation Chunk {i} Failed: {e}")
                    pass

            # Run in Parallel
            tasks = [translate_chunk(i, chunk) for i, chunk in enumerate(chunks)]
            await asyncio.gather(*tasks)

        except Exception as e:
            print(f"Translation Setup Failed: {e}")
            pass

    # Mapping
    outlet_articles_map = {o.name: [] for o in outlets}
    for article in filtered_articles:
        if article.source in outlet_articles_map:
            outlet_articles_map[article.source].append(article)

    # 2. Build HTML Table (Dark Mode Optimized)
    # REMOVED LOC COLUMN
    
    start_str = cutoff_date.strftime("%b %d")
    end_str = now.strftime("%b %d")
    period_label = f"{start_str} - {end_str}"
    
    table_html = f"<h1 style='color: #e2e8f0; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; margin-bottom: 20px;'>Deep Analysis: {req.category} <span style='font-size:0.6em; color:#94a3b8;'>({period_label})</span></h1>"
    
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
            date_icon = "✅" if s['date'] >= 30 and art.relevance_score > 0 else "⚠️"
            
            date_color = "#4ade80" if art.relevance_score > 0 else "#7f1d1d" # Green vs Bordeaux Red
            date_display = f"<span style='color: {date_color}; font-weight: bold;'>{art.date_str}</span>" if art.date_str else f"<span style='color: #7f1d1d;'>N/A</span>"
            
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

