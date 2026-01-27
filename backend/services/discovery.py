import json
import re
import google.generativeai as genai
from typing import List, Optional
from google.api_core.exceptions import ResourceExhausted

# Import schemas from our new location
from schemas.outlets import OutletCreate

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
    # Multi-Model Fallback Strategy
    # PROBE RESULT (2025-01-17): Prod has Gemini 2.0/2.5 available!
    models_to_try = [
        'gemini-2.0-flash',        # Stable fast 2.0
        'gemini-2.0-flash-exp',    # Experimental 2.0
        'gemini-2.5-flash',        # Bleeding edge
        'gemini-1.5-flash',        # Fallbacks
        'gemini-1.5-pro'
    ]
    last_error = None
    text = None

    for model_name in models_to_try:
        try:
            print(f"DEBUG: Trying model {model_name}...")
            # recreate model instance for each try
            model = genai.GenerativeModel(model_name)
            response = await model.generate_content_async(prompt, generation_config={"max_output_tokens": 4000})
            text = response.text.strip()
            if text: break
        except Exception as e:
            print(f"DEBUG: Model {model_name} failed: {e}")
            last_error = e
            continue
            
    if not text:
        # PROBE: List available models to find out what IS there
        available_models = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
        except Exception as probe_e:
            available_models.append(f"Probe Failed: {probe_e}")
            
        # If all failed, raise the last error with the PROBE info
        raise ValueError(f"All models failed. Last Error: {last_error}. Available Models: {', '.join(available_models[:5])}")
    
    # Robust JSON finding using Regex
    import re
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        text = match.group(0)
    else:
        # If no JSON found, this IS an error worth seeing in trace
        raise ValueError(f"No JSON block found in Gemini response. Text: {text[:100]}...")
    
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
         # Propagate this too
         raise ValueError(f"JSON Decode Error: {e} | Text: {text[:50]}...")
    
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
    
    return outlets

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
