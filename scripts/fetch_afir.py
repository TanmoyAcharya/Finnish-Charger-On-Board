import json
import requests
from pathlib import Path

BASE = "https://afir.digitraffic.fi"
LOCATIONS_URL = f"{BASE}/api/charging-network/v1/locations"
STATUSES_URL  = f"{BASE}/api/charging-network/v1/locations/statuses"

OUT_DIR = Path("data/raw")
OUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "Digitraffic-User": "fin-ev-dashboard/0.1",
    "Accept-Encoding": "gzip",
}

def fetch_all_geojson(url: str, out_path: Path) -> int:
    features = []
    cursor = None
    page = 0

    while True:
        params = {"limit": 500}
        if cursor:
            params["cursor"] = cursor

        r = requests.get(url, params=params, headers=HEADERS, timeout=60)
        r.raise_for_status()
        data = r.json()

        chunk = data.get("features", []) if isinstance(data, dict) else []
        features.extend(chunk)

        page += 1
        print(f"{out_path.name}: page {page}, +{len(chunk)} (total {len(features)})")

        cursor = (data.get("pagination") or {}).get("nextCursor") if isinstance(data, dict) else None
        if not cursor:
            break

    out_path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"Saved {len(features)} features -> {out_path}")
    return len(features)

if __name__ == "__main__":
    fetch_all_geojson(LOCATIONS_URL, OUT_DIR / "locations.geojson")
    fetch_all_geojson(STATUSES_URL,  OUT_DIR / "statuses.geojson")
