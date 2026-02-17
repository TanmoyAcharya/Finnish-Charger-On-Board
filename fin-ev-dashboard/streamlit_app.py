import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import json

# Optional clustering (only used if checkbox enabled)
try:
    from sklearn.cluster import DBSCAN
except Exception:
    DBSCAN = None

st.set_page_config(page_title="Finland EV Charging Dashboard", layout="wide")
API = "http://127.0.0.1:8000"


def clean_operator(x):
    if x is None:
        return "Unknown"
    s = str(x)

    # already a plain name
    if "{" not in s and "}" not in s:
        return s.strip() if s.strip() else "Unknown"

    # try parse JSON-like text
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
def fetch_from_api(limit: int):
    r = requests.get(f"{API}/chargers", params={"limit": limit}, timeout=30)
    r.raise_for_status()
    return r.json()


st.markdown("""
# 🇫🇮 Finland EV Charging Infrastructure Dashboard  
Data source: Fintraffic Digitraffic AFIR API  
Built with FastAPI + Streamlit + Plotly
""")

# ---------------- Sidebar controls ----------------
st.sidebar.header("Filters")

limit = st.sidebar.slider("Max points", 100, 5000, 1767, 100)
map_mode = st.sidebar.radio("Map mode", ["Points", "Heatmap"])

enable_clusters = st.sidebar.checkbox("Show clusters (DBSCAN)", value=False)
if enable_clusters and DBSCAN is None:
    st.sidebar.warning("Install clustering support: pip install scikit-learn")

# Fetch base data first
try:
    data = fetch_from_api(limit)
except Exception as e:
    st.error("FastAPI not reachable. Start it in another terminal:")
    st.code("python -m uvicorn app.api:app --host 127.0.0.1 --port 8000 --reload")
    st.code(str(e))
    st.stop()

df = pd.DataFrame(data)
if df.empty:
    st.warning("No data returned.")
    st.stop()

# Clean fields
df["operator"] = df.get("operator", "").apply(clean_operator)
df["city"] = df.get("city", pd.Series([None] * len(df))).fillna("Unknown")
df["name"] = df.get("name", pd.Series([""] * len(df))).fillna("")
df["address"] = df.get("address", pd.Series([""] * len(df))).fillna("")

# Build dropdown options
operators = ["All"] + sorted(df["operator"].fillna("Unknown").unique().tolist())
cities = ["All"] + sorted(df["city"].fillna("Unknown").unique().tolist())

selected_operator = st.sidebar.selectbox("Operator", operators)
selected_city = st.sidebar.selectbox("City", cities)
search_text = st.sidebar.text_input("Search name/address", "")

# Apply filters -> q
q = df.copy()
if selected_operator != "All":
    q = q[q["operator"] == selected_operator]
if selected_city != "All":
    q = q[q["city"] == selected_city]
if search_text.strip():
    s = search_text.strip().lower()
    q = q[q["name"].str.lower().str.contains(s) | q["address"].str.lower().str.contains(s)]

st.write(f"Showing **{len(q)}** charging locations")

# ---------------- Overview metrics ----------------
st.subheader("📊 Overview")
col1, col2, col3 = st.columns(3)
col1.metric("Total Chargers", int(len(q)))
col2.metric("Unique Operators", int(q["operator"].nunique()))
col3.metric("Cities Covered", int(q["city"].nunique()))

# ---------------- Map ----------------
st.subheader("🗺 Map")

q_map = q.copy()
q_map["lat"] = pd.to_numeric(q_map["lat"], errors="coerce")
q_map["lon"] = pd.to_numeric(q_map["lon"], errors="coerce")
q_map = q_map.dropna(subset=["lat", "lon"])

if q_map.empty:
    st.warning("No valid coordinates to show on the map.")
else:
    if enable_clusters and DBSCAN is not None and map_mode == "Points" and len(q_map) > 20:
        coords = q_map[["lat", "lon"]].to_numpy()
        model = DBSCAN(eps=0.02, min_samples=10).fit(coords)
        q_map["cluster"] = model.labels_.astype(int)

        fig = px.scatter_mapbox(
            q_map,
            lat="lat",
            lon="lon",
            color="cluster",
            hover_name="name",
            hover_data=["operator", "city", "address"],
            zoom=4,
            height=650,
        )
    else:
        if map_mode == "Points":
            fig = px.scatter_mapbox(
                q_map,
                lat="lat",
                lon="lon",
                hover_name="name",
                hover_data=["operator", "city", "address"],
                zoom=4,
                height=650,
            )
        else:
            fig = px.density_mapbox(
                q_map,
                lat="lat",
                lon="lon",
                radius=10,
                zoom=4,
                height=650,
            )

    fig.update_layout(mapbox_style="open-street-map")
    st.plotly_chart(fig, use_container_width=True)

# ---------------- Rankings ----------------
st.subheader("🏆 Rankings")
colA, colB = st.columns(2)

op_counts = q["operator"].value_counts().head(15).reset_index()
op_counts.columns = ["operator", "count"]
colA.plotly_chart(px.bar(op_counts, x="operator", y="count"), use_container_width=True)

city_counts = q["city"].value_counts().head(15).reset_index()
city_counts.columns = ["city", "count"]
colB.plotly_chart(px.bar(city_counts, x="city", y="count"), use_container_width=True)

# ---------------- Download ----------------
st.subheader("⬇️ Export")
st.download_button(
    "Download filtered CSV",
    data=q.to_csv(index=False).encode("utf-8"),
    file_name="fin_ev_chargers_filtered.csv",
    mime="text/csv",
)

# ---------------- Preview ----------------
st.subheader("📄 Data preview")
st.dataframe(q[["name", "operator", "city", "address", "lat", "lon"]].head(200), use_container_width=True)
