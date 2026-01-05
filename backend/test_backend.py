import requests

API_URL = "http://localhost:8000"

# 1. Register/Login
email = "test@example.com"
password = "password123"

# Try register
try:
    requests.post(f"{API_URL}/register", json={"email": email, "password": password})
except:
    pass

# Login
resp = requests.post(f"{API_URL}/token", data={"username": email, "password": password})
if resp.status_code != 200:
    print(f"Login failed: {resp.text}")
    exit(1)

token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Call Discovery
print("Calling discover_city...")
data = {
    "city": "Bucharest",
    "country": "Romania",
    "lat": 44.4268,
    "lng": 26.1025
}
resp = requests.post(f"{API_URL}/outlets/discover_city", json=data, headers=headers)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:200]}...")
