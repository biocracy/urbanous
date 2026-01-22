import os
import requests
import json
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env')
api_key = os.getenv("GEMINI_API_KEY")

model = "imagen-4.0-ultra-generate-001" 

url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict?key={api_key}"

payload = {
    "instances": [
        {"prompt": "A highly detailed architectural sketch of a futuristic city tower, masterpiece, 8k"}
    ],
    "parameters": {
        "sampleCount": 1,
        "aspectRatio": "16:9"
    }
}

print(f"Testing generation with {model}...")
try:
    resp = requests.post(url, json=payload, timeout=60) # Increased timeout for Ultra
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print("Success! Response contains keys:", resp.json().keys())
    else:
        print("Error:", resp.text)
except Exception as e:
    print(f"Exception: {e}")
