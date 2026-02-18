import json
import pandas as pd
from pathlib import Path

RAW = Path("data/raw")
OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def extract_features(data) -> list[dict]:
    if isinstance(data, dict) and "features" in data:
        return data.get("features") or []
    if isinstance(data, list):
        return data
    return []

def flatten_locations(features: list[dict]) -> pd.DataFrame:
    rows = []
    for f in features:
        props = (f.get("properties") or {}) if isinstance(f, dict) else {}
        geom = (f.get("geometry") or {}) if isinstance(f, dict) else {}
        coords = geom.get("coordinates") or [None, None]
        lon, lat = (coords + [None, None])[:2]

        loc_id = props.get("id") or props.get("locationId") or props.get("stationId")

        rows.append({
            "id": loc_id,
            "name": props.get("name"),
            "operator": props.get("operatorName") or props.get("operator"),
            "city": props.get("city"),
            "address": props.get("address") or props.get("streetAddress"),
            "lat": lat,
            "lon": lon,
            "raw_properties": json.dumps(props, ensure_ascii=False),
        })

    df = pd.DataFrame(rows)
    df = df.dropna(subset=["id", "lat", "lon"])
    return df

def flatten_statuses(features: list[dict]) -> pd.DataFrame:
    if not features:
        return pd.DataFrame(columns=["id", "raw_status"])

    rows = []
    for f in features:
        if isinstance(f, dict) and "properties" in f:
            props = f.get("properties") or {}
        elif isinstance(f, dict):
            props = f
        else:
            props = {}

        st_id = props.get("id") or props.get("locationId") or props.get("stationId")
        rows.append({
            "id": st_id,
            "raw_status": json.dumps(props, ensure_ascii=False),
        })

    df = pd.DataFrame(rows)
    if "id" in df.columns:
        df = df.dropna(subset=["id"])
    else:
        df = pd.DataFrame(columns=["id", "raw_status"])
    return df

if __name__ == "__main__":
    loc_data = load_json(RAW / "locations.geojson")
    st_data  = load_json(RAW / "statuses.geojson")

    loc_features = extract_features(loc_data)
    st_features  = extract_features(st_data)

    df_loc = flatten_locations(loc_features)
    df_st  = flatten_statuses(st_features)

    df = df_loc.merge(df_st, on="id", how="left")

    out_csv = OUT / "chargers.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8")
    print("Saved:", out_csv, "rows:", len(df))
    print("Statuses rows:", len(df_st))
