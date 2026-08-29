import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Vietnam Car Price Tracker Dashboard",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 1. DATA SOURCE (GOOGLE SHEETS) ---
SHEET_URL = st.secrets.get(
    "GSHEET_URL",
    "https://docs.google.com/spreadsheets/d/1v8kbRlDssd2GX19NzDAWwq5b-5UQjNQmVBolsg9o_GU/export?format=csv&gid=13472345930"
)

# --- 2. ROBUST LIVE DATA LOADER ---
@st.cache_data(ttl=600)
def load_data_from_gsheet(url: str):
    df = pd.read_csv(url)
    
    # Helper function to sanitize text strings into clean floats
    def clean_number(col_series):
        if col_series is None:
            return pd.Series(dtype=float)
        s = col_series.astype(str).str.strip()
        s = (
            s.str.replace("₫", "", regex=False)
            .str.replace("VND", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", "", regex=False)
        )
        return pd.to_numeric(s, errors="coerce")

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

    # Drop empty or invalid metadata rows
    df = df.dropna(subset=["Model", "Trim / Variant", "Listed MSRP (VND)"]).copy()
    
    # Parse dates safely
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    
    # Convert VND values to Millions for readable visualization
    df["MSRP_M"] = df["Listed MSRP (VND)"] / 1e6
    df["Cash_Discount_M"] = df["Cash Discount (VND)"] / 1e6
    df["Net_HN_M"] = df["Net Price HN (VND)"] / 1e6
    df["Net_HCM_M"] = df["Net Price HCM (VND)"] / 1e6
    df["OnRoad_HCM_M"] = df["Estimated On-Road HCM (VND)"] / 1e6
    df["OnRoad_HN_M"] = df["Estimated On-Road HN (VND)"] / 1e6
    
    # Automated metric formulas
    df["Discount_Amount_M"] = df["MSRP_M"] - df["Net_HN_M"]
    df["Discount_Pct"] = (df["Discount_Amount_M"] / df["MSRP_M"].replace(0, np.nan)) * 100
    df["Full_Variant_Name"] = df["Brand"].astype(str) + " " + df["Model"].astype(str) + " - " + df["Trim / Variant"].astype(str)
    
    return df

# Load the live data
try:
    df_raw = load_data_from_gsheet(SHEET_URL)
except Exception as e:
    st.error(f"Failed to fetch data from Google Sheets: {e}")
    st.stop()

# --- 3. SIDEBAR CONTROLS & FILTERS ---
st.sidebar.header("🔍 Filters & Refresh")

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

region = st.sidebar.radio("Active Region for Net Price", ["Hà Nội (HN)", "TP. Hồ Chí Minh (HCM)"])
active_net_col = "Net_HN_M" if "HN" in region else "Net_HCM_M"

st.sidebar.markdown("---")
st.sidebar.caption("💡 *Synced live with Google Sheets.*")

# --- 4. MAIN DASHBOARD CONTENT ---
st.title("🚗 Vietnam Automobile Price & Promo Tracker")
st.markdown("Real-time pricing analysis across market segments, listed MSRP, and cash discounts.")

if df_filtered.empty:
    st.warning("⚠️ No data matches your current filter selection. Please reset or broaden your filters in the sidebar.")
    st.stop()

# --- 5. KPI SUMMARY CARDS ---
st.subheader("📌 Key Market Highlights")

top_cash_trims = df_filtered.sort_values(by="Cash_Discount_M", ascending=False).head(3)
top_pct_trims = df_filtered.sort_values(by="Discount_Pct", ascending=False).head(3)
lowest_price_trims = df_filtered.sort_values(by=active_net_col, ascending=True).head(3)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("##### 💰 Top Cash Discounts")
    for idx, (_, row) in enumerate(top_cash_trims.iterrows(), 1):
        st.metric(
            label=f"#{idx} {row['Brand']} {row['Model']} ({row['Trim / Variant']})",
            value=f"{row['Cash_Discount_M']:,.0f}M VND",
            delta=f"-{row['Discount_Pct']:.1f}% vs MSRP",
            delta_color="normal"
        )

with col2:
    st.markdown("##### 📉 Top Discount Percentage (%)")
    for idx, (_, row) in enumerate(top_pct_trims.iterrows(), 1):
        st.metric(
            label=f"#{idx} {row['Brand']} {row['Model']} ({row['Trim / Variant']})",
            value=f"{row['Discount_Pct']:.2f}%",
            delta=f"-{row['Discount_Amount_M']:,.0f}M VND",
            delta_color="normal"
        )

with col3:
    st.markdown("##### 🏷️ Lowest Entry Prices")
    for idx, (_, row) in enumerate(lowest_price_trims.iterrows(), 1):
        st.metric(
            label=f"#{idx} {row['Brand']} {row['Model']} ({row['Trim / Variant']})",
            value=f"{row[active_net_col]:,.0f}M VND",
            delta=f"MSRP: {row['MSRP_M']:,.0f}M",
            delta_color="off"
        )

st.markdown("---")

# --- 6. CHARTS 1 & 2 ---
row1_col1, row1_col2 = st.columns([6, 5])

# Chart 1: Clustered Column Chart (MSRP vs Net Price)
with row1_col1:
    st.subheader("📊 Chart 1: Listed MSRP vs. Net Price")
    
    chart1_data = df_filtered.copy()
    fig1 = go.Figure()
    
    fig1.add_trace(go.Bar(
        x=chart1_data["Full_Variant_Name"],
        y=chart1_data["MSRP_M"],
        name="Listed MSRP",
        marker_color="#1f77b4",
        text=chart1_data["MSRP_M"].apply(lambda v: f"{v:,.0f}M"),
        textposition="outside"
    ))
    
    fig1.add_trace(go.Bar(
        x=chart1_data["Full_Variant_Name"],
        y=chart1_data[active_net_col],
        name=f"Net Price ({region.split()[0]})",
        marker_color="#e74c3c",
        text=chart1_data[active_net_col].apply(lambda v: f"{v:,.0f}M"),
        textposition="outside"
    ))
    
    fig1.update_layout(
        barmode="group",
        xaxis_tickangle=-45,
        yaxis_title="Price (Million VND)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=30, b=120),
        height=480,
    )
    st.plotly_chart(fig1, use_container_width=True)

# Chart 2: Ranked Horizontal Bar Chart (Cash Discounts by Model)
with row1_col2:
    st.subheader("🏆 Chart 2: Top Cash Discounts by Model")
    
    model_discount_df = (
        df_filtered.groupby(["Brand", "Model"])["Cash_Discount_M"]
        .max()
        .reset_index()
        .sort_values(by="Cash_Discount_M", ascending=True)
    )
    model_discount_df["Model_Label"] = model_discount_df["Brand"] + " " + model_discount_df["Model"]
    
    fig2 = px.bar(
        model_discount_df,
        x="Cash_Discount_M",
        y="Model_Label",
        orientation="h",
        text="Cash_Discount_M",
        color="Cash_Discount_M",
        color_continuous_scale="Greens",
        labels={"Cash_Discount_M": "Max Cash Discount (Million VND)", "Model_Label": "Model"}
    )
    
    fig2.update_traces(
        texttemplate="%{text:,.0f}M VND",
        textposition="outside"
    )
    fig2.update_layout(
        coloraxis_showscale=False,
        margin=dict(l=20, r=40, t=30, b=40),
        height=480,
        xaxis=dict(range=[0, max(model_discount_df["Cash_Discount_M"].max() * 1.25, 50)])
    )
    st.plotly_chart(fig2, use_container_width=True)

# --- 7. CHART 3 (TIMELINE) ---
st.subheader("📈 Chart 3: Estimated On-Road Price TP. HCM Over Time")

timeline_df = df_filtered.dropna(subset=["Date"]).sort_values(by="Date")

if timeline_df["Date"].nunique() > 1:
    fig3 = px.line(
        timeline_df,
        x="Date",
        y="OnRoad_HCM_M",
        color="Full_Variant_Name",
        markers=True,
        labels={"OnRoad_HCM_M": "On-Road HCM (Million VND)", "Date": "Recorded Date", "Full_Variant_Name": "Variant"}
    )
    fig3.update_layout(
        hovermode="x unified",
        margin=dict(l=20, r=20, t=20, b=40),
        height=400,
        legend=dict(orientation="h", yanchor="top", y=-0.25)
    )
    st.plotly_chart(fig3, use_container_width=True)
else:
    fig3 = px.bar(
        timeline_df,
        x="Full_Variant_Name",
        y="OnRoad_HCM_M",
        color="Brand",
        text="OnRoad_HCM_M",
        labels={"OnRoad_HCM_M": "Estimated On-Road HCM (Million VND)", "Full_Variant_Name": "Variant"}
    )
    fig3.update_traces(texttemplate="%{text:,.0f}M", textposition="outside")
    fig3.update_layout(xaxis_tickangle=-45, height=420)
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")

# --- 8. DYNAMIC DATA TABLE ---
st.subheader("📋 Model Price & Discount Summary Table")

display_cols = [
    "Date", "Brand", "Model", "Trim / Variant", 
    "Listed MSRP (VND)", "Net Price HN (VND)", "Net Price HCM (VND)",
    "Cash Discount (VND)", "Discount_Amount_M", "Discount_Pct", 
    "Estimated On-Road HCM (VND)", "Promo Details & Gifts"
]

valid_display_cols = [c for c in display_cols if c in df_filtered.columns]
styled_table = df_filtered[valid_display_cols].copy()

if "Date" in styled_table.columns:
    styled_table["Date"] = styled_table["Date"].dt.strftime("%Y-%m-%d")

format_dict = {}
for col in ["Listed MSRP (VND)", "Net Price HN (VND)", "Net Price HCM (VND)", "Cash Discount (VND)", "Estimated On-Road HCM (VND)"]:
    if col in styled_table.columns:
        format_dict[col] = "{:,.0f} ₫"
if "Discount_Amount_M" in styled_table.columns:
    format_dict["Discount_Amount_M"] = "{:,.1f}M"
if "Discount_Pct" in styled_table.columns:
    format_dict["Discount_Pct"] = "{:.2f}%"

st.dataframe(
    styled_table.style.format(format_dict),
    use_container_width=True,
    height=360
)
