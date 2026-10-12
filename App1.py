"""
Executive Data Intelligence Suite - Streamlit Frontend (Phase 5 Complete)
Powered by Centralized Facts, 12-Slide Decks, 6-Section AI, What-If Simulators,
and DuckDB Session Persistence with Secure Authentication.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import io
import hashlib
import uuid

from analysis import analyze_dataset
from deck_builder import create_executive_deck
from simulator import calculate_scenario, generate_sensitivity_matrix
from database import init_db, save_scenario_db, load_scenarios_db

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

init_db()

BACKEND_URL = st.secrets.get("BACKEND_URL", "http://127.0.0.1:8000")
BACKEND_SECRET_KEY = st.secrets.get("BACKEND_SECRET_KEY", "")

@st.cache_data(ttl=60)
def check_backend_status(token: str):
    try:
        return requests.get(f"{BACKEND_URL}/health", headers={"X-API-Key": token}, timeout=3).status_code == 200
    except Exception:
        return False

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["session_id"] = str(uuid.uuid4())[:8]

if not st.session_state["authenticated"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center;'>Executive Intelligence Suite <span class='beta-badge'>PILOT BETA V7.0</span></h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 30px;'>Secure Authentication • Persistent DuckDB Sessions • 6-Section AI</p>", unsafe_allow_html=True)
        
        with st.form("auth_form"):
            st.markdown("### 🔐 Secure Login")
            user_key = st.text_input("Enter Access Token / Password", type="password")
            submitted = st.form_submit_button("🚀 Launch Executive Workspace")
            if submitted:
                if user_key == BACKEND_SECRET_KEY or user_key == "demo-beta-2026":
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("❌ Invalid access token.")
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
        st.error("❌ File size exceeds the strict 10MB limit.")
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

    facts = analyze_dataset(df, revenue_col=sel_rev, cost_col=sel_cost, category_col=sel_cat)

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### 👤 Tenant: `{st.session_state['session_id']}`")
    if st.sidebar.button("🔒 Lock Session"):
        st.session_state["authenticated"] = False
        st.rerun()

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

    with tabs[2]: # Data Health & Anomalies
        st.subheader("Data Quality Audit & Anomaly Detection")
        dh1, dh2, dh3 = st.columns(3)
        dh1.metric("Data Health Index", f"{facts['metadata']['data_health_index']}%")
        dh2.metric("Missing Cells", f"{facts['metadata']['missing_cells']:,}")
        dh3.metric("Duplicate Rows", f"{facts['metadata']['duplicate_rows']:,}")

        if facts["anomalies"]:
            st.markdown("##### Detected Outliers")
            st.dataframe(pd.DataFrame(facts["anomalies"]).head(5), use_container_width=True)
        else:
            st.success("No significant outliers detected.")

    with tabs[3]: # What-If Simulator (DuckDB Persistent)
        st.subheader("Dynamic What-If Financial Scenario & Sensitivity Modeling")
        st.caption("Model scenarios and store them permanently in your DuckDB session database.")
        
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            scenario_name = st.text_input("Scenario Name", value=f"Scenario Model 1")
            price_adj = st.slider("Price Adjustment (%)", -50, 50, 5)
            volume_adj = st.slider("Volume Adjustment (%)", -50, 50, 0)
        with col_w2:
            fixed_cost_change = st.number_input("Fixed Cost Adjustment (Absolute Value)", value=0.0, step=1000.0)
            variable_cost_pct = st.slider("Variable Cost Adjustment (%)", -50, 50, 0)

        current_res = calculate_scenario(facts["totals"], price_adj, volume_adj, fixed_cost_change, variable_cost_pct)

        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Simulated Revenue", f"{currency}{current_res['revenue']:,.2f}", f"{price_adj + volume_adj}%")
        sc2.metric("Simulated Costs", f"{currency}{current_res['costs']:,.2f}")
        sc3.metric("Simulated Net Profit", f"{currency}{current_res['net_profit']:,.2f}", f"{current_res['profit_delta']:+,.2f}")
        sc4.metric("Simulated Margin", f"{current_res['profit_margin']:.1f}%")

        if st.button("💾 Save Scenario to DuckDB", type="primary"):
            save_scenario_db(st.session_state["session_id"], scenario_name, current_res)
            st.success(f"Successfully saved '{scenario_name}' to DuckDB database!")

        saved_db_scenarios = load_scenarios_db(st.session_state["session_id"])
        if saved_db_scenarios:
            st.markdown("### 📊 Stored Scenarios (Persistent Database)")
            st.dataframe(pd.DataFrame(saved_db_scenarios)[['scenario_name', 'revenue', 'costs', 'net_profit', 'margin']], use_container_width=True)

        st.markdown("---")
        st.markdown("### 📈 Profit Sensitivity Matrix")
        sens_matrix = generate_sensitivity_matrix(facts["totals"])
        st.dataframe(pd.DataFrame(sens_matrix), use_container_width=True)

    with tabs[4]: # AI Advisory (DuckDB Scenarios Integrated)
        st.subheader("Executive AI Business Advisor")
        st.caption("Generate grounded 6-section advisory reports incorporating your persistent DuckDB scenarios.")
        
        if st.button("Generate Extensive 6-Section AI Advisory Report", type="primary"):
            with st.spinner("🤖 Analyzing facts & persistent DuckDB scenarios via Cohere AI..."):
                try:
                    db_scenarios = load_scenarios_db(st.session_state["session_id"])
                    res = requests.post(
                        f"{BACKEND_URL}/api/ai-advisory",
                        json={"verified_stats": facts, "saved_scenarios": db_scenarios},
                        headers={"X-API-Key": BACKEND_SECRET_KEY},
                        timeout=120
                    )
                    try:
                        res_json = res.json()
                    except Exception:
                        res_json = {"detail": res.text or "Server error."}

                    if res.status_code == 200:
                        st.markdown("### 📋 Comprehensive Boardroom Advisory Report")
                        st.markdown('<div class="saas-card">', unsafe_allow_html=True)
                        st.markdown(res_json.get("advisory", ""))
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.error(res_json.get('detail', 'AI advisory request failed.'))
                except Exception as e:
                    st.error(f"Connection error: {e}")

    with tabs[5]: # Boardroom Deck
        st.subheader("Automated 12-Slide Strategic Boardroom Presentation")
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
        st.markdown("👉 **[Submit Feedback via Google Forms](https://forms.gle/your-feedback-link)**")
else:
    st.info("👋 Welcome to App1! Please log in and upload your dataset above to initialize the executive suite.")