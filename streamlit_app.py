import streamlit as st
from pymongo import MongoClient
import os
from google_maps_to_mongodb import scrape_and_store

# ─── LOAD .env MANUALLY (no python-dotenv needed) ─────────────────────────────
def load_env():
    """Reads .env file manually for local dev. No external package required."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

load_env()

# ─── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nearby Shops Finder",
    page_icon="🛍️",
    layout="wide",
)

# ─── CUSTOM CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    .header-box {
        background: linear-gradient(135deg, #1f8a5b 0%, #145c3d 100%);
        color: white;
        padding: 2rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .header-box h1 { margin: 0; font-size: 2.2rem; }
    .header-box p  { margin: 0.3rem 0 0; opacity: 0.85; }

    .shop-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .shop-card h3  { margin: 0 0 0.4rem; color: #1a202c; }
    .shop-card p   { margin: 0.2rem 0; color: #4a5568; font-size: 0.92rem; }
    .badge {
        display: inline-block;
        background: #d1fae5;
        color: #065f46;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .result-count {
        background: #f0fdf4;
        border-left: 4px solid #1f8a5b;
        padding: 0.6rem 1rem;
        border-radius: 0 6px 6px 0;
        color: #065f46;
        font-weight: 600;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ─── CONNECT DB ───────────────────────────────────────────────────────────────
@st.cache_resource
def get_collection():
    # Try multiple sources for MONGO_URL
    mongo_url = None
    
    # 1. Try Streamlit secrets first (for cloud)
    try:
        mongo_url = st.secrets["MONGO_URL"]
    except:
        pass
    
    # 2. Fall back to environment variable (for local)
    if not mongo_url:
        mongo_url = os.getenv("MONGO_URL")
    
    # 3. Validate
    if not mongo_url or mongo_url.strip() == "":
        st.error("❌ MONGO_URL not found in secrets or environment variables!")
        st.stop()
    
    # Clean the URL (remove any accidental whitespace)
    mongo_url = mongo_url.strip()
    
    try:
        client = MongoClient(mongo_url)
        # Test connection
        client.admin.command('ping')
        return client["test"]["shops"]
    except Exception as e:
        st.error(f"❌ MongoDB connection failed: {str(e)}")
        st.stop()

collection = get_collection()

# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-box">
    <h1>🛍️ Nearby Shops Finder</h1>
    <p>Find trusted shops and businesses around you</p>
</div>
""", unsafe_allow_html=True)

# ─── SEARCH BAR ───────────────────────────────────────────────────────────────
col1, col2 = st.columns([5, 1])
with col1:
    query = st.text_input(
        "",
        placeholder="e.g. restaurant near DD Nagar Gwalior",
        label_visibility="collapsed"
    )
with col2:
    search_btn = st.button("🔍 Search", use_container_width=True)

# ─── SEARCH LOGIC ─────────────────────────────────────────────────────────────
if search_btn and query.strip():
    with st.spinner("Fetching data from Google Maps & saving to DB..."):
        try:
            scrape_and_store(query.strip())
            st.success("✅ Data fetched and saved successfully!")
        except Exception as e:
            st.warning(f"Scraper note: {e}")

    shops = list(collection.find(
        {
            "$or": [
                {"shopName":  {"$regex": query, "$options": "i"}},
                {"address":   {"$regex": query, "$options": "i"}},
                {"category":  {"$regex": query, "$options": "i"}},
            ]
        },
        {
            "_id": 0,
            "shopName": 1, "category": 1, "address": 1,
            "contactNumber": 1, "shopImage": 1,
            "latitude": 1, "longitude": 1,
        }
    ))

    if shops:
        st.markdown(
            f'<div class="result-count">📍 {len(shops)} shop(s) found for "{query}"</div>',
            unsafe_allow_html=True
        )

        # ── MAP ──
        if any(s.get("latitude") and s.get("longitude") for s in shops):
            import pandas as pd
            map_data = pd.DataFrame([
                {"lat": s["latitude"], "lon": s["longitude"], "name": s["shopName"]}
                for s in shops if s.get("latitude") and s.get("longitude")
            ])
            st.map(map_data)

        # ── CARDS ──
        cols = st.columns(2)
        for i, shop in enumerate(shops):
            with cols[i % 2]:
                img_html = (
                    f'<img src="{shop["shopImage"]}" '
                    f'style="width:100%;max-height:160px;object-fit:cover;'
                    f'border-radius:6px;margin-bottom:0.5rem">'
                    if shop.get("shopImage") else ""
                )
                st.markdown(f"""
                <div class="shop-card">
                    {img_html}
                    <span class="badge">{shop.get('category','Others')}</span>
                    <h3>{shop.get('shopName','—')}</h3>
                    <p>📍 {shop.get('address') or 'NA'}</p>
                    <p>📞 {shop.get('contactNumber') or 'NA'}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No shops found. Try a different search term.")

elif search_btn and not query.strip():
    st.warning("Please enter a search term.")