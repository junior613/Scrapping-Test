import requests
import os
from dotenv import load_dotenv

load_dotenv()
SCRAPPA_API_KEY = os.getenv("SCRAPPA_API_KEY")

def test(source, url):
    headers = {"X-API-KEY": SCRAPPA_API_KEY, "Accept": "application/json"}
    params = {"query": "Hotels Douala"}
    print(f"\n--- Final Verification: {source} ---")
    try:
        response = requests.get(url, params=params, headers=headers, timeout=20)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            # Try all possible result keys
            results = (
                data.get('organic_results', []) or 
                data.get('local_results', []) or 
                data.get('data', []) or 
                data.get('results', []) or
                (data if isinstance(data, list) else [])
            )
            print(f"Success! Found {len(results)} results.")
            if len(results) > 0:
                print(f"First result title: {results[0].get('title') or results[0].get('name')}")
            else:
                print(f"Keys found in data: {list(data.keys())}")
        else:
            print(f"Failed: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

test("Google Search", "https://scrappa.co/api/search")
test("Google Maps", "https://scrappa.co/api/maps/simple-search")
test("LinkedIn", "https://scrappa.co/api/linkedin/search")
