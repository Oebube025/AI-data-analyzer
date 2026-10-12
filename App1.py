"""
Executive Data Intelligence Suite - Streamlit Frontend (Phase 3 6-Section AI Integrated)
Powered by Centralized Fact Sheet (analysis.py), 12-Slide Deck Generator (deck_builder.py),
Rich Plotly Graph Integrations, and 6-Section Structured AI Reporting.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import io
import hashlib

from analysis import analyze_dataset
from deck_builder import create_executive_deck

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

if "app_state" not in st.session_state:
    st.session_state["app_state"] = "welcome"
    st.session_state["authenticated"] = False

if st.session_state["app_state"] == "welcome":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center;'>Executive Intelligence Suite <span class='beta-badge'>PILOT BETA V6.8</span></h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 30px;'>6-Section AI Reporting • 12-Slide Decks • Rich Visual Analytics</p>", unsafe_allow_html=True)
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
            st.session_state.pop("deck_bytes", None)
        except Exception as e:
            st.error(f"Error parsing file: {e}")
            st.stop()

    df = st.session_state["active_df"]

    # Sidebar controls for mapping
    st.sidebar.markdown("### ⚙️ Executive Mapping")
    currency = st.sidebar.selectbox("Display Currency", ["₦", "$", "€", "£"])
    
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
    date_cols = [c for c in df.columns if any(k in c.lower() for k in ['date', 'time', 'year', 'month', 'period'])]
    
    valid_nums = [c for c in num_cols if not any(k in c.lower() for k in ['id', 'code', 'year'])]
    sel_rev = st.sidebar.selectbox("Revenue Column", valid_nums if valid_nums else num_cols)
    sel_cost = st.sidebar.selectbox("Cost Column", ["None"] + (valid_nums if valid_nums else num_cols))
    sel_cat = st.sidebar.selectbox("Category / Group Column", ["None"] + cat_cols)
    sel_date = st.sidebar.selectbox("Date / Time Column (Optional)", ["None"] + date_cols)

    # GENERATE CENTRALIZED FACT SHEET
    facts = analyze_dataset(df, revenue_col=sel_rev, cost_col=sel_cost, category_col=sel_cat)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔒 Pilot Beta Notice")
    st.sidebar.info("Data is processed securely for this session using centralized fact sheets.")

    tabs = st.tabs(["📊 Command Center", "📈 Trends & Leaderboard", "🔍 Data Health & Anomalies", "🎛️ What-If Simulator", "🧠 AI Advisory", "📈 Boardroom Deck", "📝 Feedback"])

    with tabs[0]: # Command Center
        st.subheader("Executive Financial Command Center")
        if facts["warnings"]:
            for warning in facts["warnings"]:
                st.warning(f"⚠️ {warning}")

        tot_rev = facts["totals"]["total_revenue"]
        tot_cost = facts["totals"]["total_costs"]
        profit = facts["totals"]["net_profit"]
        margin = facts["totals"]["profit_margin"]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Revenue", f"{currency}{tot_rev:,.2f}")
        c2.metric("Total Costs", f"{currency}{tot_cost:,.2f}")
        c3.metric("Net Profit", f"{currency}{profit:,.2f}")
        c4.metric("Profit Margin", f"{margin:.1f}%")
        
        st.markdown("---")
        
        gcol1, gcol2 = st.columns(2)
        with gcol1:
            fig_overview = px.bar(
                x=["Revenue", "Costs", "Net Profit"],
                y=[tot_rev, tot_cost, profit],
                title="Financial Overview Breakdown",
                labels={"x": "Metric", "y": f"Amount ({currency})"},
                color=["Revenue", "Costs", "Net Profit"],
                template="plotly_dark"
            )
            st.plotly_chart(fig_overview, use_container_width=True)
            
        with gcol2:
            if sel_cat != "None" and facts["revenue_by_category"]:
                pie_df = pd.DataFrame(list(facts["revenue_by_category"].items()), columns=[sel_cat, sel_rev])
                fig_pie = px.pie(
                    pie_df.head(6), 
                    names=sel_cat, 
                    values=sel_rev, 
                    title=f"Top {sel_cat} Revenue Share",
                    template="plotly_dark",
                    hole=0.4
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                fig_hist = px.histogram(df, x=sel_rev, title=f"Distribution of {sel_rev}", template="plotly_dark")
                st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown("### Dataset Preview")
        st.dataframe(df.head(10), use_container_width=True)

    with tabs[1]: # Trends & Leaderboard
        st.subheader("Performance Trends & Leaderboards")
        
        if sel_date != "None" and sel_date in df.columns and sel_rev in df.columns:
            st.markdown("#### Time-Series Trend Analysis")
            trend_df = df.groupby(sel_date)[sel_rev].sum().reset_index()
            fig_trend = px.line(trend_df, x=sel_date, y=sel_rev, title=f"{sel_rev} Trend Over Time", markers=True, template="plotly_dark")
            st.plotly_chart(fig_trend, use_container_width=True)

        if sel_cat != "None" and facts["revenue_by_category"]:
            grouped_df = pd.DataFrame(list(facts["revenue_by_category"].items()), columns=[sel_cat, sel_rev])
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.markdown("#### Top Categories by Revenue")
                st.dataframe(grouped_df.head(10), use_container_width=True)
            with col_t2:
                fig_bar = px.bar(grouped_df.head(10), x=sel_cat, y=sel_rev, title=f"Top 10 {sel_cat} by {sel_rev}", template="plotly_dark")
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Select a valid Category Column in the sidebar to view leaderboards and category bar charts.")

    with tabs[2]: # Data Health & Anomalies
        st.subheader("Data Quality Audit & Anomaly Detection")
        dh1, dh2, dh3 = st.columns(3)
        dh1.metric("Data Health Index", f"{facts['metadata']['data_health_index']}%")
        dh2.metric("Missing Cells", f"{facts['metadata']['missing_cells']:,}")
        dh3.metric("Duplicate Rows", f"{facts['metadata']['duplicate_rows']:,}")

        st.markdown("#### Revenue Outliers & Correlation Analysis")
        acols1, acols2 = st.columns(2)
        with acols1:
            if facts["anomalies"]:
                st.markdown("##### Detected Outliers")
                st.dataframe(pd.DataFrame(facts["anomalies"]).head(5), use_container_width=True)
            else:
                st.success("No significant outliers detected.")
        with acols2:
            if sel_cost != "None" and sel_cost in df.columns:
                fig_scatter = px.scatter(df, x=sel_cost, y=sel_rev, title="Cost vs. Revenue Correlation", template="plotly_dark")
                st.plotly_chart(fig_scatter, use_container_width=True)

    with tabs[3]: # What-If Simulator
        st.subheader("Dynamic What-If Financial Scenario Modeling")
        st.caption("Adjust pricing, volume, and cost structures to model real-time profit sensitivity.")
        
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            price_adj = st.slider("Price Adjustment (%)", -50, 50, 5)
            volume_adj = st.slider("Volume Adjustment (%)", -50, 50, 0)
        with col_w2:
            fixed_cost_change = st.number_input("Fixed Cost Adjustment (Absolute Value)", value=0.0, step=1000.0)
            variable_cost_pct = st.slider("Variable Cost Adjustment (%)", -50, 50, 0)

        tot_rev = facts["totals"]["total_revenue"]
        tot_cost = facts["totals"]["total_costs"]
        profit = facts["totals"]["net_profit"]

        if st.button("Calculate Scenario", type="primary"):
            sim_rev = tot_rev * (1 + price_adj / 100.0) * (1 + volume_adj / 100.0)
            sim_cost = (tot_cost * (1 + variable_cost_pct / 100.0)) + fixed_cost_change
            sim_profit = sim_rev - sim_cost

            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("Simulated Revenue", f"{currency}{sim_rev:,.2f}", f"{price_adj + volume_adj}%")
            sc2.metric("Simulated Costs", f"{currency}{sim_cost:,.2f}")
            sc3.metric("Simulated Net Profit", f"{currency}{sim_profit:,.2f}", f"{sim_profit - profit:+,.2f}")

    with tabs[4]: # AI Advisory (6-Section Strategic Report)
        st.subheader("Executive AI Business Advisor")
        st.caption("Generate grounded, extensive 6-section AI advisory reports with strict number verification.")
        
        if st.button("Generate Extensive 6-Section AI Advisory Report", type="primary"):
            with st.spinner("🤖 Analyzing verified fact sheet via Cohere AI (Extensive 6-Section Grounding)..."):
                try:
                    res = requests.post(
                        f"{BACKEND_URL}/api/ai-advisory",
                        json={"verified_stats": facts},
                        headers={"X-API-Key": BACKEND_SECRET_KEY},
                        timeout=120
                    )
                    if res.status_code == 200:
                        st.markdown("### 📋 Comprehensive Boardroom Advisory Report")
                        st.markdown('<div class="saas-card">', unsafe_allow_html=True)
                        st.markdown(res.json().get("advisory", ""))
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.error(res.json().get('detail', 'AI advisory request failed.'))
                except Exception as e:
                    st.error(f"Connection error: {e}")

    with tabs[5]: # Boardroom Deck
        st.subheader("Automated 12-Slide Strategic Boardroom Presentation")
        st.caption("Compile your verified financial metrics, category breakdowns, and audit notes into a professional multi-slide executive presentation.")
        
        if st.button("Generate Strategic Boardroom Deck (.pptx)", type="primary"):
            with st.spinner("📊 Building professional 12-slide strategic boardroom deck..."):
                try:
                    deck_bytes = create_executive_deck(facts, currency=currency, filename=uploaded.name)
                    st.session_state["deck_bytes"] = deck_bytes
                    st.success("✅ Strategic boardroom deck generated successfully!")
                except Exception as e:
                    st.error(f"Error generating presentation: {e}")

        if "deck_bytes" in st.session_state:
            st.download_button(
                label="📥 Download Strategic Boardroom Deck (.pptx)",
                data=st.session_state["deck_bytes"],
                file_name="Executive_Boardroom_Deck.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                type="primary"
            )

    with tabs[6]: # Feedback
        st.subheader("Pilot Beta Feedback & Support")
        st.markdown("We value your input as an initial tester for App1 v6.8!")
        st.markdown("👉 **[Submit Feedback via Google Forms](https://forms.gle/your-feedback-link)**")
else:
    st.info("👋 Welcome to App1! Please upload your dataset above to initialize the executive suite.")