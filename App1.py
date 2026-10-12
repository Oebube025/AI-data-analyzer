"""
Executive Data Intelligence Suite - Streamlit Frontend (Phase 0 Patched)
Restores missing features, secure What-If simulation, and clean UI.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import io
import hashlib
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches

st.set_page_config(
    page_title="Executive Intelligence Suite | Pilot Beta",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0f172a; color: #e2e8f0; }
    section[data-testid="stSidebar"] { background-color: #090d16; border-right: 1px solid #1e293b; }
    .saas-card { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1px solid #334155; padding: 28px; border-radius: 12px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.4); margin-bottom: 20px; }
    .beta-badge { background-color: #2563eb; color: #ffffff; font-size: 0.75rem; font-weight: 700; padding: 3px 10px; border-radius: 6px; vertical-align: middle; margin-left: 8px; }
    h1, h2, h3 { color: #f8fafc; letter-spacing: -0.02em; }
    .stButton>button { background-color: #2563eb; color: white; border: none; border-radius: 8px; font-weight: 600; padding: 0.6rem 1.2rem; width: 100%; transition: all 0.2s ease; }
    .stButton>button:hover { background-color: #1d4ed8; box-shadow: 0 4px 12px rgba(37,99,235,0.4); }
</style>
""", unsafe_allow_html=True)

BACKEND_URL = st.secrets.get("BACKEND_URL", "http://127.0.0.1:8000")
BACKEND_SECRET_KEY = st.secrets.get("BACKEND_SECRET_KEY", "")

@st.cache_data(ttl=60)
def check_backend_status(token: str):
    try:
        return requests.get(f"{BACKEND_URL}/health", headers={"X-API-Key": token}, timeout=3).status_code == 200
    except Exception:
        return False

class BusinessDataEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        self.cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()

    def clean_text_numeric(self):
        cleaned = self.df.copy()
        for col in cleaned.columns:
            if col not in self.num_cols:
                sample = cleaned[col].dropna().head(20).astype(str)
                if sample.str.contains(r'[₦$€£,\(\)]', regex=True).any():
                    try:
                        converted = sample.str.replace(r'[₦$€£,]', '', regex=True).str.replace(r'\((.*?)\)', r'-\1', regex=True)
                        pd.to_numeric(converted, errors='raise')
                        cleaned[col] = cleaned[col].astype(str).str.replace(r'[₦$€£,]', '', regex=True).str.replace(r'\((.*?)\)', r'-\1', regex=True)
                        cleaned[col] = pd.to_numeric(cleaned[col], errors='coerce')
                    except Exception:
                        pass
        return cleaned

if "app_state" not in st.session_state:
    st.session_state["app_state"] = "welcome"
    st.session_state["authenticated"] = False

if st.session_state["app_state"] == "welcome":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center;'>Executive Intelligence Suite <span class='beta-badge'>PILOT BETA V6.2</span></h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 30px;'>Automated Analytics, Scenario Modeling & Boardroom AI</p>", unsafe_allow_html=True)
        st.markdown('<div class="saas-card">', unsafe_allow_html=True)
        if st.button("🚀 Launch Executive Workspace", type="primary"):
            st.session_state["app_state"] = "main"
            st.session_state["authenticated"] = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 0.8rem; color: #64748b;'>Secure Server-Side Processing • Pilot Beta Environment</p>", unsafe_allow_html=True)
    st.stop()

# MAIN WORKSPACE
is_online = check_backend_status(BACKEND_SECRET_KEY)
if not is_online:
    st.warning("⚠️ Backend API is waking up or offline. Please check your Render service status.")

uploaded = st.file_uploader("📁 Upload Executive Dataset (.csv or .xlsx - Max 10MB)", type=["csv", "xlsx"])

if uploaded is not None:
    file_bytes = uploaded.getvalue()
    file_size_mb = len(file_bytes) / (1024 * 1024)

    if file_size_mb > 10:
        st.error("❌ File size exceeds the strict 10MB limit. Please upload a smaller dataset.")
        st.stop()

    file_hash = hashlib.md5(file_bytes).hexdigest()

    if "file_hash" not in st.session_state or st.session_state["file_hash"] != file_hash:
        st.session_state["file_hash"] = file_hash
        st.session_state["current_filename"] = uploaded.name
        try:
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")
            except Exception:
                df = pd.read_excel(io.BytesIO(file_bytes))

            st.session_state["active_df"] = df.copy()
            
            # Check backend response
            resp = requests.post(
                f"{BACKEND_URL}/api/analyze", 
                files={"file": (uploaded.name, file_bytes, "text/csv")}, 
                headers={"X-API-Key": BACKEND_SECRET_KEY}
            )
            if resp.status_code != 200:
                st.warning(f"Backend analysis warning: {resp.json().get('detail', 'Unknown error')}")
        except Exception as e:
            st.error(f"Error parsing file: {e}")
            st.stop()

    df = st.session_state["active_df"]
    engine = BusinessDataEngine(df)
    df_cleaned = engine.clean_text_numeric()

    st.sidebar.markdown("### ⚙️ Executive Mapping")
    currency = st.sidebar.selectbox("Display Currency", ["₦", "$", "€", "£"])
    valid_nums = [c for c in engine.num_cols if not any(k in c.lower() for k in ['id', 'code', 'year'])]
    sel_rev = st.sidebar.selectbox("Revenue Column", valid_nums if valid_nums else engine.num_cols)
    sel_cost = st.sidebar.selectbox("Cost Column", ["None"] + (valid_nums if valid_nums else engine.num_cols))
    
    cat_col_options = ["None"] + engine.cat_cols
    sel_cat = st.sidebar.selectbox("Category / Group Column", cat_col_options)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔒 Pilot Beta Notice")
    st.sidebar.info("Data is processed securely for this session. Please review our privacy terms before uploading sensitive enterprise data.")

    # Tabs restored from earlier versions plus new enhancements
    tabs = st.tabs(["📊 Command Center", "📈 Trends & Leaderboard", "🔍 Data Health & Anomalies", "🎛️ What-If Simulator", "🧠 AI Advisory", "📈 Boardroom Deck", "📝 Feedback"])

    with tabs[0]: # Command Center
        st.subheader("Executive Financial Command Center")
        tot_rev = df_cleaned[sel_rev].sum() if sel_rev in df_cleaned else 0.0
        tot_cost = df_cleaned[sel_cost].sum() if sel_cost != "None" and sel_cost in df_cleaned else 0.0
        profit = tot_rev - tot_cost
        margin = (profit / tot_rev * 100) if tot_rev > 0 else 0.0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Revenue", f"{currency}{tot_rev:,.2f}")
        c2.metric("Total Costs", f"{currency}{tot_cost:,.2f}")
        c3.metric("Net Profit", f"{currency}{profit:,.2f}")
        c4.metric("Profit Margin", f"{margin:.1f}%")
        
        st.markdown("### Dataset Preview")
        st.dataframe(df_cleaned.head(10), use_container_width=True)

    with tabs[1]: # Trends & Leaderboard (Restored feature)
        st.subheader("Performance Trends & Leaderboards")
        if sel_cat != "None" and sel_cat in df_cleaned and sel_rev in df_cleaned:
            grouped = df_cleaned.groupby(sel_cat)[sel_rev].sum().reset_index().sort_values(by=sel_rev, ascending=False)
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.markdown("#### Top Categories by Revenue")
                st.dataframe(grouped.head(10), use_container_width=True)
            with col_t2:
                fig = px.bar(grouped.head(10), x=sel_cat, y=sel_rev, title=f"Top 10 {sel_cat} by {sel_rev}", template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Please select a valid Category Column in the sidebar to view leaderboards and category breakdowns.")

    with tabs[2]: # Data Health & Anomalies (Restored feature)
        st.subheader("Data Quality Audit & Anomaly Detection")
        total_cells = df.size
        missing_cells = df.isna().sum().sum()
        health = max(0.0, min(100.0, ((total_cells - missing_cells) / max(1, total_cells)) * 100))
        
        dh1, dh2 = st.columns(2)
        dh1.metric("Data Health Index", f"{health:.1f}%", f"{missing_cells} missing cells")
        dh2.metric("Duplicate Rows", f"{df.duplicated().sum():,}")

        if sel_rev in df_cleaned:
            q1 = df_cleaned[sel_rev].quantile(0.25)
            q3 = df_cleaned[sel_rev].quantile(0.75)
            iqr = q3 - q1
            upper_bound = q3 + 1.5 * iqr
            outliers = df_cleaned[df_cleaned[sel_rev] > upper_bound]
            st.markdown(f"#### Potential Revenue Outliers / Anomalies (> Q3 + 1.5*IQR)")
            if not outliers.empty:
                st.dataframe(outliers.head(10), use_container_width=True)
            else:
                st.success("No significant outliers detected in revenue distribution.")

    with tabs[3]: # What-If Simulator (Pure Pandas implementation)
        st.subheader("Dynamic What-If Financial Scenario Modeling")
        st.caption("Adjust pricing, volume, and cost structures to model real-time profit sensitivity.")
        
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            price_adj = st.slider("Price Adjustment (%)", -50, 50, 5)
            volume_adj = st.slider("Volume Adjustment (%)", -50, 50, 0)
        with col_w2:
            fixed_cost_change = st.number_input("Fixed Cost Adjustment (Absolute Value)", value=0.0, step=1000.0)
            variable_cost_pct = st.slider("Variable Cost Adjustment (%)", -50, 50, 0)

        if st.button("Calculate Scenario", type="primary"):
            base_rev = df_cleaned[sel_rev].sum() if sel_rev in df_cleaned else 0.0
            base_cost = df_cleaned[sel_cost].sum() if sel_cost != "None" and sel_cost in df_cleaned else 0.0
            
            sim_rev = base_rev * (1 + price_adj / 100.0) * (1 + volume_adj / 100.0)
            sim_cost = (base_cost * (1 + variable_cost_pct / 100.0)) + fixed_cost_change
            sim_profit = sim_rev - sim_cost

            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("Simulated Revenue", f"{currency}{sim_rev:,.2f}", f"{price_adj + volume_adj}%")
            sc2.metric("Simulated Costs", f"{currency}{sim_cost:,.2f}")
            sc3.metric("Simulated Net Profit", f"{currency}{sim_profit:,.2f}", f"{sim_profit - profit:+,.2f}")

    with tabs[4]: # AI Advisory (Restored feature)
        st.subheader("Executive AI Business Advisor")
        st.caption("Generate professional AI insights based on your verified dataset statistics.")
        if st.button("Generate AI Advisory Report", type="primary"):
            stats_summary = f"Dataset: {uploaded.name}, Records: {len(df):,}, Total Revenue: {tot_rev:,.2f}, Total Costs: {tot_cost:,.2f}, Net Profit: {profit:,.2f}, Margin: {margin:.1f}%"
            try:
                res = requests.post(
                    f"{BACKEND_URL}/api/ai-advisory",
                    json={"verified_stats": stats_summary},
                    headers={"X-API-Key": BACKEND_SECRET_KEY},
                    timeout=30
                )
                if res.status_code == 200:
                    st.markdown(res.json().get("advisory", ""))
                else:
                    st.error(res.json().get("detail", "AI advisory request failed."))
            except Exception as e:
                st.error(f"Connection error: {e}")

    with tabs[5]: # Boardroom Deck
        st.subheader("Automated Boardroom Presentation Generator")
        st.caption("Compile your verified financial metrics directly into an executive PowerPoint presentation.")
        if st.button("Generate PowerPoint Presentation"):
            prs = Presentation()
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            chart_data = CategoryChartData()
            chart_data.categories = ["Revenue", "Costs", "Net Profit"]
            chart_data.add_series("Financials", (tot_rev, tot_cost, profit))
            slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1), Inches(1), Inches(10), Inches(5), chart_data)
            
            buf = io.BytesIO()
            prs.save(buf)
            buf.seek(0)
            st.download_button("📥 Download Executive Presentation (.pptx)", data=buf, file_name="Executive_Presentation.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

    with tabs[6]: # Feedback
        st.subheader("Pilot Beta Feedback & Support")
        st.markdown("We value your input as an initial tester for App1 v6.2!")
        st.markdown("👉 **[Submit Feedback via Google Forms](https://forms.gle/your-feedback-link)**")
else:
    st.info("👋 Welcome to App1! Please upload your dataset above to initialize the executive suite.")