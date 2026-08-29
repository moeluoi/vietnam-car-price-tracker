import streamlit as st
import pandas as pd
import numpy as np
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
    "https://docs.google.com/spreadsheets/d/1v8kbRlDssd2GX19NzDAWwq5b-5UQjNQmVBolsg9o_GU/export?format=csv&gid=1347234593"
)

# --- LIVE DATA LOADER (Auto-refreshes every 600s / 10 mins) ---
# --- ROBUST LIVE DATA LOADER ---
@st.cache_data(ttl=600)
def load_data_from_gsheet(url: str):
    # 1. Read the live CSV from Google Sheets
    df = pd.read_csv(url)
    
    # 2. Helper function to sanitize and convert dirty text columns into pure numeric floats
    def clean_number(col_series):
        if col_series is None:
            return pd.Series(dtype=float)
        # Convert to string, remove spaces, currency symbols, and commas/dots if formatted
        s = col_series.astype(str).str.strip()
        s = s.str.replace("₫", "", regex=False)\
             .str.replace("VND", "", regex=False)\
             .str.replace(" ", "", regex=False)\
             .str.replace(",", "", regex=False)
        return pd.to_numeric(s, errors="coerce")

    # 3. Convert all monetary columns safely
    numeric_cols = [
        "Listed MSRP (VND)",
        "Cash Discount (VND)",
        "Net Price HN (VND)",
        "Net Price HCM (VND)",
        "Estimated On-Road HN (VND)",
        "Estimated On-Road HCM (VND)"
    ]
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = clean_number(df[col])
        else:
            df[col] = 0.0

    # 4. Drop empty or invalid rows
    df = df.dropna(subset=["Model", "Trim / Variant", "Listed MSRP (VND)"]).copy()
    
    # 5. Parse dates safely
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    
    # 6. Now safe to perform mathematical division
    df["MSRP_M"] = df["Listed MSRP (VND)"] / 1e6
    df["Cash_Discount_M"] = df["Cash Discount (VND)"] / 1e6
    df["Net_HN_M"] = df["Net Price HN (VND)"] / 1e6
    df["Net_HCM_M"] = df["Net Price HCM (VND)"] / 1e6
    df["OnRoad_HCM_M"] = df["Estimated On-Road HCM (VND)"] / 1e6
    df["OnRoad_HN_M"] = df["Estimated On-Road HN (VND)"] / 1e6
    
    # 7. Automated metric calculations
    df["Discount_Amount_M"] = df["MSRP_M"] - df["Net_HN_M"]
    df["Discount_Pct"] = (df["Discount_Amount_M"] / df["MSRP_M"].replace(0, np.nan)) * 100
    df["Full_Variant_Name"] = df["Brand"].astype(str) + " " + df["Model"].astype(str) + " - " + df["Trim / Variant"].astype(str)
    
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
