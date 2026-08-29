import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Vietnam Car Price Tracker Dashboard",
    page_icon="🚗",
    layout="wide",
)

# Fetch URL from Streamlit secrets or fallback to direct URL
SHEET_URL = st.secrets.get(
    "GSHEET_URL",
    "https://docs.google.com/spreadsheets/d/<YOUR_SPREADSHEET_ID>/export?format=csv&gid=0"
)

# --- LIVE DATA LOADER (Auto-refreshes every 600s / 10 mins) ---
@st.cache_data(ttl=600)
def load_data_from_gsheet(url: str):
    # Reads the live CSV stream from Google Sheets
    df = pd.read_csv(url)
    
    # Drop empty/incomplete rows
    df = df.dropna(subset=["Model", "Trim / Variant", "Listed MSRP (VND)"]).copy()
    
    # Parse dates
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    
    # Convert VND values to Millions for clear visual formatting
    df["MSRP_M"] = df["Listed MSRP (VND)"] / 1e6
    df["Cash_Discount_M"] = df["Cash Discount (VND)"] / 1e6
    df["Net_HN_M"] = df["Net Price HN (VND)"] / 1e6
    df["Net_HCM_M"] = df["Net Price HCM (VND)"] / 1e6
    df["OnRoad_HCM_M"] = df["Estimated On-Road HCM (VND)"] / 1e6
    df["OnRoad_HN_M"] = df["Estimated On-Road HN (VND)"] / 1e6
    
    # Automated metrics
    df["Discount_Amount_M"] = df["MSRP_M"] - df["Net_HN_M"]
    df["Discount_Pct"] = (df["Discount_Amount_M"] / df["MSRP_M"]) * 100
    df["Full_Variant_Name"] = df["Brand"] + " " + df["Model"] + " - " + df["Trim / Variant"]
    
    return df

# Load data
try:
    df_raw = load_data_from_gsheet(SHEET_URL)
except Exception as e:
    st.error(f"Failed to fetch data from Google Sheets: {e}")
    st.stop()

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🔍 Filters & Refresh")

# Manual force refresh button
if st.sidebar.button("🔄 Force Refresh Data"):
    st.cache_data.clear()
    st.rerun()

all_brands = sorted(df_raw["Brand"].dropna().unique().tolist())
selected_brands = st.sidebar.multiselect("Brand", all_brands, default=all_brands)

available_models = sorted(df_raw[df_raw["Brand"].isin(selected_brands)]["Model"].dropna().unique().tolist())
selected_models = st.sidebar.multiselect("Model", available_models, default=available_models)

df_filtered = df_raw[
    (df_raw["Brand"].isin(selected_brands)) & 
    (df_raw["Model"].isin(selected_models))
].copy()

available_variants = sorted(df_filtered["Trim / Variant"].dropna().unique().tolist())
selected_variants = st.sidebar.multiselect("Variant / Trim", available_variants, default=available_variants)

if selected_variants:
    df_filtered = df_filtered[df_filtered["Trim / Variant"].isin(selected_variants)]

region = st.sidebar.radio("Active Region", ["Hà Nội (HN)", "TP. Hồ Chí Minh (HCM)"])
active_net_col = "Net_HN_M" if "HN" in region else "Net_HCM_M"

# --- RENDER REMAINING KPIS, CHARTS 1-3, AND TABLE ---
# (Keep the KPI, Chart 1, Chart 2, Chart 3, and styled table logic from the previous script)
