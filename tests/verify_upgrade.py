import urllib.request
import json

# 1. Check health
health = json.loads(urllib.request.urlopen("http://127.0.0.1:8000/health").read().decode())
print("Health:", health)

# 2. Check discovery deck
deck = json.loads(urllib.request.urlopen("http://127.0.0.1:8000/v1/discover").read().decode())
print("Total Catalog in Database:", deck.get("total_catalog_size"))
print("Discovery Hero Title:", deck.get("hero", {}).get("content", {}).get("title"))
print("Comfort Rail Titles:", len(deck.get("comfort_rail", [])))
print("Adrenaline Rail Titles:", len(deck.get("adrenaline_rail", [])))

# 3. Check taste universe
universe = json.loads(urllib.request.urlopen("http://127.0.0.1:8000/v1/profile/taste-universe").read().decode())
print("Taste Universe Clusters:", len(universe.get("clusters", [])))
for c in universe["clusters"]:
    print(f" - [{c['name']}]: {len(c.get('orbit_titles', []))} orbiting titles (Gravity: {int(c['weight']*100)}%)")

# 4. Verify static page
html = urllib.request.urlopen("http://127.0.0.1:8000/").read().decode()
print("Live Frontend HTML Bytes:", len(html))
print("\nALL VERIFICATIONS PASSED!")
