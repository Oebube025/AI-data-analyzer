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
    page_title="Executive Intelligence Suite (Advanced Roadmap)",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0f172a; color: #e2e8f0; }
    section[data-testid="stSidebar"] { background-color: #090d16; border-right: 1px solid #1e293b; }
    .saas-card { background-color: #1e293b; border: 1px solid #334155; padding: 32px; border-radius: 12px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.4); margin-bottom: 20px; }
    .beta-badge { background-color: #2563eb; color: #ffffff; font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 4px; vertical-align: middle; margin-left: 8px; }
    h1, h2, h3 { color: #f8fafc; letter-spacing: -0.02em; }
    .stButton>button { background-color: #2563eb; color: white; border: none; border-radius: 8px; font-weight: 600; padding: 0.6rem 1.2rem; width: 100%; }
    .stButton>button:hover { background-color: #1d4ed8; }
</style>
""", unsafe_allow_html=True)

BACKEND_URL = st.secrets.get("BACKEND_URL", "https://ai-data-analyzer-backend-your-service.onrender.com")
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

    def audit_data_quality(self, active_df: pd.DataFrame):
        total = active_df.size
        if total == 0: return 0.0, 0, 0, []
        missing = active_df.isna().sum().sum()
        health = max(0.0, min(100.0, ((total - missing) / total) * 100))
        issues = [f"Found {missing:,} missing cells."] if missing > 0 else []
        return round(health, 1), missing, active_df.duplicated().sum(), issues

if "app_state" not in st.session_state:
    st.session_state["app_state"] = "welcome"
    st.session_state["authenticated"] = False

if st.session_state["app_state"] == "welcome":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center;'>Executive Intelligence Suite <span class='beta-badge'>ROADMAP V6</span></h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 30px;'>DuckDB Accelerated Analytics & AI Reporting</p>", unsafe_allow_html=True)
        st.markdown('<div class="saas-card">', unsafe_allow_html=True)
        if st.button("Launch Advanced Workspace", type="primary"):
            st.session_state["app_state"] = "main"
            st.session_state["authenticated"] = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# MAIN WORKSPACE
is_online = check_backend_status(BACKEND_SECRET_KEY)
uploaded = st.file_uploader("Upload Dataset (.csv or .xlsx)", type=["csv", "xlsx"])

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
            # Register in backend DuckDB
            requests.post(f"{BACKEND_URL}/api/analyze", files={"file": (uploaded.name, file_bytes, "text/csv")}, headers={"X-API-Key": BACKEND_SECRET_KEY})
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

    df = st.session_state["active_df"]
    engine = BusinessDataEngine(df)
    df_cleaned = engine.clean_text_numeric()

    st.sidebar.markdown("### ⚙️ Mapping & Simulation")
    currency = st.sidebar.selectbox("Currency", ["₦", "$", "€", "£"])
    valid_nums = [c for c in engine.num_cols if not any(k in c.lower() for k in ['id', 'code', 'year'])]
    sel_rev = st.sidebar.selectbox("Revenue Column", valid_nums if valid_nums else engine.num_cols)
    sel_cost = st.sidebar.selectbox("Cost Column", ["None"] + (valid_nums if valid_nums else engine.num_cols))

    tabs = st.tabs(["Command Center", "What-If Simulator", "SQL & AI Query", "Boardroom Deck", "Feedback"])

    with tabs[0]: # Command Center
        st.subheader("Financial Command Center")
        tot_rev = df_cleaned[sel_rev].sum() if sel_rev in df_cleaned else 0.0
        tot_cost = df_cleaned[sel_cost].sum() if sel_cost != "None" and sel_cost in df_cleaned else 0.0
        profit = tot_rev - tot_cost
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Revenue", f"{currency}{tot_rev:,.2f}")
        c2.metric("Total Costs", f"{currency}{tot_cost:,.2f}")
        c3.metric("Net Profit", f"{currency}{profit:,.2f}")
        st.dataframe(df_cleaned.head(10), use_container_width=True)

    with tabs[1]: # What-If Simulator (Roadmap Phase 4)
        st.subheader("Dynamic What-If Scenario Modeling")
        st.caption("Test real-time sensitivity adjustments on your financial metrics.")
        
        price_adj = st.slider("Price Adjustment (%)", -20, 20, 5)
        volume_adj = st.slider("Volume Adjustment (%)", -20, 20, 0)

        if st.button("Run Simulation", type="primary"):
            payload = {
                "price_factor": 1 + (price_adj / 100),
                "volume_factor": 1 + (volume_adj / 100),
                "revenue_col": sel_rev,
                "cost_col": sel_cost
            }
            try:
                res = requests.post(f"{BACKEND_URL}/api/simulate", json=payload, headers={"X-API-Key": BACKEND_SECRET_KEY}).json()
                s_rev = res["simulated_revenue"]
                s_cost = res["simulated_cost"]
                s_prof = res["simulated_profit"]

                sc1, sc2, sc3 = st.columns(3)
                sc1.metric("Simulated Revenue", f"{currency}{s_rev:,.2f}", f"{price_adj + volume_adj}%")
                sc2.metric("Simulated Costs", f"{currency}{s_cost:,.2f}")
                sc3.metric("Simulated Profit", f"{currency}{s_prof:,.2f}")
            except Exception as e:
                st.error(f"Simulation failed: {e}")

    with tabs[2]: # SQL & AI Query (Roadmap Phase 1 & 2)
        st.subheader("DuckDB SQL & Intelligence Engine")
        sql_input = st.text_area("Enter DuckDB SQL Query", value="SELECT * FROM dataset LIMIT 5")
        if st.button("Execute Query"):
            try:
                res = requests.post(f"{BACKEND_URL}/api/query", json={"sql_query": sql_input}, headers={"X-API-Key": BACKEND_SECRET_KEY}).json()
                if isinstance(res, list):
                    st.dataframe(pd.DataFrame(res), use_container_width=True)
                else:
                    st.error(res.get("detail", "Query Error"))
            except Exception as e:
                st.error(f"Error: {e}")

    with tabs[3]: # Boardroom Deck (Roadmap Phase 3)
        st.subheader("Automated Insight-to-Deck PowerPoint")
        if st.button("Generate PowerPoint Deck with Charts"):
            prs = Presentation()
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            chart_data = CategoryChartData()
            chart_data.categories = ["Revenue", "Costs", "Net Profit"]
            chart_data.add_series("Financials", (tot_rev, tot_cost, profit))
            slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1), Inches(1), Inches(10), Inches(5), chart_data)
            
            buf = io.BytesIO()
            prs.save(buf)
            buf.seek(0)
            st.download_button("Download Presentation (.pptx)", data=buf, file_name="Executive_Presentation.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

    with tabs[4]: # Feedback
        st.subheader("Beta Feedback")
        st.markdown("[Open Google Feedback Form](https://forms.gle/your-feedback-link)")
else:
    st.info("Please upload a dataset to initialize the advanced workspace.")