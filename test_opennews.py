import requests

BASE_URL = "http://localhost:8000"

def test_auth():
    print("Testing Auth...")
    # Register
    email = "test@example.com"
    password = "password123"
    api_key = "dummy_gemini_key"
    
    try:
        resp = requests.post(f"{BASE_URL}/register", json={"email": email, "password": password, "gemini_api_key": api_key})
        if resp.status_code == 200:
            print("Register Success")
            token = resp.json()["access_token"]
        elif resp.status_code == 400 and "already registered" in resp.text:
             print("User already exists, logging in...")
             resp = requests.post(f"{BASE_URL}/token", data={"username": email, "password": password})
             resp.raise_for_status()
             token = resp.json()["access_token"]
        else:
            print(f"Register Failed: {resp.text}")
            return None
            
        print(f"Got Token: {token[:10]}...")
        return token
    except Exception as e:
        print(f"Auth Exception: {e}")
        return None

def test_agent(token):
    print("Testing Agent Endpoint (Discover City)...")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "city": "Cluj-Napoca",
        "country": "Romania",
        "force_refresh": False
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/outlets/discover_city", json=payload, headers=headers)
        if resp.status_code == 200:
            print(f"Discover Success: Found {len(resp.json())} outlets")
        elif resp.status_code == 429:
             print("Quota Exceeded (Expected for dummy key)")
        else:
             print(f"Discover Failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Agent Exception: {e}")

if __name__ == "__main__":
    token = test_auth()
    if token:
        test_agent(token)
