
import asyncio
import os
import google.generativeai as genai
import json
import re

# Mock the function from outlets.py
async def gemini_discover_city_outlets(city: str, country: str, api_key: str):
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

    Return a strictly valid JSON list. Example:
    [
        {{ "name": "Monitorul de Cluj", "url": "https://www.monitorulcj.ro", "type": "Online", "popularity": 10, "focus": "Local" }},
        {{ "name": "Radio Cluj", "url": "http://radiocluj.ro", "type": "Radio", "popularity": 7, "focus": "Local and National" }}
    ]
    Do not include any markdown formatting or explanation, just the JSON string.
    """
    
    print(f"DEBUG: Starting Gemini Discovery for {city}, {country}")
    model = genai.GenerativeModel('gemini-flash-latest')
    try:
        response = await model.generate_content_async(prompt, generation_config={"max_output_tokens": 4000})
        text = response.text.strip()
        print(f"--- RAW RESPONSE START ---\n{text}\n--- RAW RESPONSE END ---")
        
        # Parse logic
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            text = match.group(0)
            print("DEBUG: JSON block found.")
        else:
            print(f"DEBUG: No JSON block found in response.")
            return []
        
        try:
            data = json.loads(text)
            print(f"DEBUG: JSON parsed successfully. {len(data)} items.")
            return data
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON Parsed Error: {e}")
            return []

    except Exception as e:
        print(f"DEBUG: Critical Error: {e}")
        return []

async def main():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("No API Key found")
        return
    
    print("Testing Sofia...")
    res = await gemini_discover_city_outlets("Sofia", "Bulgaria", key)
    print("Result:", res)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
