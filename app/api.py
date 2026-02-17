from fastapi import FastAPI, Query
from pathlib import Path
import pandas as pd
import numpy as np

app = FastAPI(title="Finland EV Charging API (AFIR)")

DATA = Path("data/processed/chargers.csv")
if not DATA.exists():
    raise RuntimeError("Missing data/processed/chargers.csv. Run scripts/build_dataset.py first.")

df = pd.read_csv(DATA)

# Ensure expected columns exist
for col in ["id", "name", "operator", "city", "address", "lat", "lon"]:
    if col not in df.columns:
        df[col] = None

@app.get("/health")
def health():
    return {"ok": True, "rows": int(len(df)), "cols": list(df.columns)}

@app.get("/chargers")
def chargers(
    city: str | None = None,
    operator: str | None = None,
    limit: int = Query(1500, ge=1, le=5000),
):
    q = df

    if city:
        q = q[q["city"].fillna("").astype(str).str.contains(city, case=False, na=False)]
    if operator:
        q = q[q["operator"].fillna("").astype(str).str.contains(operator, case=False, na=False)]

    out_cols = ["id", "name", "operator", "city", "address", "lat", "lon"]
    q = q[out_cols].head(limit).copy()

    # Convert NaN/inf to None so JSON serialization never crashes
    q.replace([np.nan, np.inf, -np.inf], None, inplace=True)

    return q.to_dict(orient="records")
