import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import io
import time
import hashlib
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches, Pt

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
    .saas-card { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1px solid #334155; padding: 32px; border-radius: 12px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.4); margin-bottom: 20px; }
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
        st.markdown("<br><br><h1 style='text-align: center;'>Executive Intelligence Suite <span class='beta-badge'>PILOT BETA V6</span></h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 30px;'>DuckDB Accelerated Analytics, What-If Simulation & Boardroom AI</p>", unsafe_allow_html=True)
        st.markdown('<div class="saas-card">', unsafe_allow_html=True)
        if st.button("🚀 Launch Executive Workspace", type="primary"):
            st.session_state["app_state"] = "main"
            st.session_state["authenticated"] = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 0.8rem; color: #64748b;'>Secure Server-Side Intelligence • End-to-End Encrypted Session State</p>", unsafe_allow_html=True)
    st.stop()

# MAIN WORKSPACE
is_online = check_backend_status(BACKEND_SECRET_KEY)
if not is_online:
    st.warning("⚠️ Backend API is waking up or offline. Please check your Render service status or local server.")

uploaded = st.file_uploader("📁 Upload Executive Dataset (.csv or .xlsx - Max 10MB)", type=["csv", "xlsx"])

if uploaded is not None:
    file_bytes = uploaded.getvalue()
    file_hash = hashlib.md5(file_bytes).hexdigest()

    if "file_hash" not in st.session_state or st.session_state["file_hash"] != file_hash:
        st.session_state["file_hash"] = file_hash
        st.session_state["current_filename"] = uploaded.name
        st.session_state["raw_file_bytes"] = file_bytes
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8") if uploaded.name.lower().endswith('.csv') else pd.read_excel(io.BytesIO(file_bytes))
            st.session_state["active_df"] = df.copy()
            requests.post(f"{BACKEND_URL}/api/analyze", files={"file": (uploaded.name, file_bytes, "text/csv")}, headers={"X-API-Key": BACKEND_SECRET_KEY})
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

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔒 Pilot Beta Notice")
    st.sidebar.info("Data is processed securely in-memory via DuckDB and cleared upon session reset.")

    tabs = st.tabs(["📊 Command Center", "🎛️ What-If Simulator", "⚡ DuckDB SQL Engine", "📈 Boardroom Deck", "📝 Feedback"])

    with tabs[0]: # Command Center
        st.subheader("Executive Financial Command Center")
        tot_rev = df_cleaned[sel_rev].sum() if sel_rev in df_cleaned else 0.0
        tot_cost = df_cleaned[sel_cost].sum() if sel_cost != "None" and sel_cost in df_cleaned else 0.0
        profit = tot_rev - tot_cost
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Revenue", f"{currency}{tot_rev:,.2f}")
        c2.metric("Total Costs", f"{currency}{tot_cost:,.2f}")
        c3.metric("Net Profit", f"{currency}{profit:,.2f}")
        
        st.markdown("### Dataset Preview & Audited Records")
        st.dataframe(df_cleaned.head(10), use_container_width=True)

    with tabs[1]: # What-If Simulator
        st.subheader("Dynamic What-If Financial Scenario Modeling")
        st.caption("Adjust pricing and volume parameters below to model real-time profit sensitivity.")
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            price_adj = st.slider("Price Adjustment (%)", -50, 50, 5)
        with col_s2:
            volume_adj = st.slider("Volume Adjustment (%)", -50, 50, 0)

        if st.button("Run Advanced Simulation", type="primary"):
            payload = {
                "price_factor": 1 + (price_adj / 100),
                "volume_factor": 1 + (volume_adj / 100),
                "revenue_col": sel_rev,
                "cost_col": sel_cost
            }
            try:
                response = requests.post(f"{BACKEND_URL}/api/simulate", json=payload, headers={"X-API-Key": BACKEND_SECRET_KEY})
                res = response.json()
                if response.status_code == 200:
                    s_rev = res["simulated_revenue"]
                    s_cost = res["simulated_cost"]
                    s_prof = res["simulated_profit"]

                    sc1, sc2, sc3 = st.columns(3)
                    sc1.metric("Simulated Revenue", f"{currency}{s_rev:,.2f}", f"{price_adj}% Price")
                    sc2.metric("Simulated Costs", f"{currency}{s_cost:,.2f}")
                    sc3.metric("Simulated Net Profit", f"{currency}{s_prof:,.2f}", f"{s_prof - profit:+,.2f}")
                else:
                    st.error(f"Simulation failed: {res.get('detail', 'Unknown backend error')}")
            except Exception as e:
                st.error(f"Connection error: {e}")

    with tabs[2]: # SQL Engine
        st.subheader("DuckDB In-Memory SQL Intelligence Engine")
        st.caption("Query your dataset instantly using standard SQL statements.")
        sql_input = st.text_area("SQL Query", value="SELECT * FROM dataset LIMIT 10")
        if st.button("Execute SQL Query"):
            try:
                response = requests.post(f"{BACKEND_URL}/api/query", json={"sql_query": sql_input}, headers={"X-API-Key": BACKEND_SECRET_KEY})
                res = response.json()
                if response.status_code == 200 and isinstance(res, list):
                    st.dataframe(pd.DataFrame(res), use_container_width=True)
                else:
                    st.error(res.get("detail", "Query Execution Error"))
            except Exception as e:
                st.error(f"Error: {e}")

    with tabs[3]: # Boardroom Deck
        st.subheader("Automated Insight-to-Deck Presentation Generator")
        st.caption("Compile your verified financial metrics directly into an executive PowerPoint presentation with native charts.")
        if st.button("Generate & Download PowerPoint Deck"):
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

    with tabs[4]: # Feedback
        st.subheader("Pilot Beta Feedback & Support")
        st.markdown("We value your input as an initial tester for App1 v6!")
        st.markdown("👉 **[Submit Feedback via Google Forms](https://forms.gle/your-feedback-link)**")
else:
    st.info("👋 Welcome to App1! Please upload your dataset above to initialize the executive suite.")