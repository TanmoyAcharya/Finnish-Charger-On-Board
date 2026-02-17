import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import requests

st.set_page_config(page_title="Finland EV Charging Dashboard", layout="wide")

API = os.environ.get("EV_API", "http://127.0.0.1:8000")  # local default
CSV_PATH = "data/processed/chargers.csv"


def clean_operator(x):
    if x is None:
        return "Unknown"
    s = str(x)
    if "{" not in s and "}" not in s:
        return s.strip() if s.strip() else "Unknown"
    try:
        s2 = s.replace("'", '"')
        obj = json.loads(s2)
        if isinstance(obj, dict):
            if "details" in obj and isinstance(obj["details"], dict) and "name" in obj["details"]:
                return str(obj["details"]["name"])
            if "name" in obj:
                return str(obj["name"])
    except Exception:
        pass
    return "Unknown"


@st.cache_data(ttl=600)
def load_data(limit: int):
    # Try API first (local dev)
    try:
        r = requests.get(f"{API}/chargers", params={"limit": limit}, timeout=10)
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data)
        source = f"FastAPI ({API})"
        return df, source
    except Exception:
        # Fallback to CSV (Streamlit Cloud)
        df = pd.read_csv(CSV_PATH)
        df = df.head(limit)
        source = f"CSV ({CSV_PATH})"
        return df, source


st.markdown("""
# 🇫🇮 Finland EV Charging Infrastructure Dashboard
Data source: Fintraffic Digitraffic AFIR API (processed)
Built with FastAPI + Streamlit + Plotly
""")

st.sidebar.header("Controls")
limit = st.sidebar.slider("Max points", 100, 5000, 1767, 100)
map_mode = st.sidebar.radio("Map mode", ["Points", "Heatmap"])

df, source = load_data(limit)

# Clean fields
df["operator"] = df.get("operator", "").apply(clean_operator)
df["city"] = df.get("city", pd.Series([None] * len(df))).fillna("Unknown")
df["name"] = df.get("name", pd.Series([""] * len(df))).fillna("")
df["address"] = df.get("address", pd.Series([""] * len(df))).fillna("")

st.caption(f"Loaded from: **{source}**")
st.write(f"Showing **{len(df)}** charging locations")

# Overview
st.subheader("📊 Overview")
col1, col2, col3 = st.columns(3)
col1.metric("Total Chargers", int(len(df)))
col2.metric("Unique Operators", int(df["operator"].nunique()))
col3.metric("Cities Covered", int(df["city"].nunique()))

# Map
st.subheader("🗺 Map")

df_map = df.copy()
df_map["lat"] = pd.to_numeric(df_map["lat"], errors="coerce")
df_map["lon"] = pd.to_numeric(df_map["lon"], errors="coerce")
df_map = df_map.dropna(subset=["lat", "lon"])

if df_map.empty:
    st.warning("No valid coordinates to display.")
else:
    if map_mode == "Points":
        fig = px.scatter_mapbox(
            df_map,
            lat="lat",
            lon="lon",
            hover_name="name",
            hover_data=["operator", "city", "address"],
            zoom=4,
            height=650,
        )
    else:
        fig = px.density_mapbox(
            df_map,
            lat="lat",
            lon="lon",
            radius=10,
            zoom=4,
            height=650,
        )

    fig.update_layout(mapbox_style="open-street-map")
    st.plotly_chart(fig, use_container_width=True)

# Quick stats
st.subheader("Quick stats")

top_ops = df["operator"].value_counts().head(15).reset_index()
top_ops.columns = ["operator", "count"]
st.write("Top operators")
st.dataframe(top_ops, use_container_width=True)

top_cities = df["city"].value_counts().head(15).reset_index()
top_cities.columns = ["city", "count"]
st.write("Top cities")
st.dataframe(top_cities, use_container_width=True)

# Download
st.subheader("⬇️ Export")
st.download_button(
    "Download CSV (current view)",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="fin_ev_chargers.csv",
    mime="text/csv",
)
