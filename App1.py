"""
SME Data Intelligence Suite - Streamlit Frontend (App1.py)
Automated CFO Briefs, Bank-Ready Pitch Decks, What-If Calculators, 
In-App Client Feedback, and Secure Founder Monitoring.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import io
import hashlib
import uuid
import duckdb
import os

from analysis import analyze_dataset, auto_detect_columns
from deck_builder import create_executive_deck
from simulator import calculate_scenario, generate_sensitivity_matrix
from database import (
    init_db, 
    save_scenario_db, 
    load_scenarios_db, 
    log_tenant_activity, 
    save_feedback_db
)

# 1. PAGE CONFIGURATION & STYLING
st.set_page_config(
    page_title="AI CFO Suite for Small Business",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0f172a; color: #e2e8f0; }
    section[data-testid="stSidebar"] { background-color: #090d16; border-right: 1px solid #1e293b; }
    .saas-card { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1px solid #334155; padding: 24px; border-radius: 12px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.4); margin-bottom: 20px; }
    .sme-badge { background-color: #10b981; color: #ffffff; font-size: 0.75rem; font-weight: 700; padding: 3px 10px; border-radius: 6px; vertical-align: middle; margin-left: 8px; }
    h1, h2, h3 { color: #f8fafc; letter-spacing: -0.02em; }
    .stButton>button { background-color: #2563eb; color: white; border: none; border-radius: 8px; font-weight: 600; padding: 0.6rem 1.2rem; width: 100%; transition: all 0.2s ease; }
    .stButton>button:hover { background-color: #1d4ed8; box-shadow: 0 4px 12px rgba(37,99,235,0.4); }
</style>
""", unsafe_allow_html=True)

# 2. INITIALIZE DATABASE & ENVIRONMENT SECRETS
init_db()

BACKEND_URL = st.secrets.get("BACKEND_URL", "http://127.0.0.1:8000")
BACKEND_SECRET_KEY = st.secrets.get("BACKEND_SECRET_KEY", "")

@st.cache_data(ttl=60)
def check_backend_status(token: str):
    try:
        return requests.get(f"{BACKEND_URL}/health", headers={"X-API-Key": token}, timeout=3).status_code == 200
    except Exception:
        return False

# Session State Initializations
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["session_id"] = str(uuid.uuid4())[:8]

if "sim_price" not in st.session_state: st.session_state["sim_price"] = 5
if "sim_vol" not in st.session_state: st.session_state["sim_vol"] = 0
if "sim_vc" not in st.session_state: st.session_state["sim_vc"] = 0

# 3. AUTHENTICATION / ACCESS GATE
if not st.session_state["authenticated"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center;'>AI CFO Suite <span class='sme-badge'>FOR SMALL BUSINESS</span></h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 30px;'>Automated Financial Audits • Bank-Ready Decks • On-Demand CFO Advice</p>", unsafe_allow_html=True)
        
        with st.form("auth_form"):
            st.markdown("### 🔐 Enter Business Workspace")
            client_email = st.text_input("Business Email", placeholder="owner@company.com")
            company_name = st.text_input("Company Name", placeholder="Acme Services")
            user_key = st.text_input("Access Key / Passcode", type="password")
            submitted = st.form_submit_button("🚀 Launch Business Dashboard")
            
            if submitted:
                if user_key == BACKEND_SECRET_KEY or user_key == "demo-beta-2026":
                    st.session_state["authenticated"] = True
                    st.session_state["user_email"] = client_email if client_email else f"user_{st.session_state['session_id']}@guest.com"
                    st.session_state["company_name"] = company_name if company_name else "Independent SME"
                    
                    # Track tenant registration & login
                    log_tenant_activity(
                        st.session_state["user_email"], 
                        st.session_state["company_name"], 
                        "Workspace Sign-In"
                    )
                    st.rerun()
                else:
                    st.error("❌ Invalid access key.")
        st.stop()

# 4. MAIN WORKSPACE UI
is_online = check_backend_status(BACKEND_SECRET_KEY)
if not is_online:
    st.warning("⚠️ AI Advisor Backend is starting up... Please wait a moment.")

uploaded = st.file_uploader("📁 Upload Monthly Business File (.csv or .xlsx - QuickBooks, Shopify, Excel)", type=["csv", "xlsx"])

if uploaded is not None:
    file_bytes = uploaded.getvalue()
    if len(file_bytes) / (1024 * 1024) > 10:
        st.error("❌ File size exceeds the 10MB limit.")
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
            
            # Auto-detect column mappings upon fresh upload
            st.session_state["detected_cols"] = auto_detect_columns(df)
            
            # Log file upload activity for tenant
            log_tenant_activity(
                st.session_state.get("user_email", "guest"), 
                st.session_state.get("company_name", "SME"), 
                f"Uploaded File: {uploaded.name}"
            )
        except Exception as e:
            st.error(f"Error reading file: {e}")
            st.stop()

    df = st.session_state["active_df"]
    auto_cols = st.session_state.get("detected_cols", auto_detect_columns(df))

    # 5. SIDEBAR CONTROLS & AUTO-MAPPING
    st.sidebar.markdown("### ⚙️ Business Settings")
    currency = st.sidebar.selectbox("Currency Symbol", ["$", "₦", "€", "£"])
    
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
    date_cols = [c for c in df.columns if any(k in c.lower() for k in ['date', 'time', 'year', 'month', 'period', 'day'])]

    sel_rev = st.sidebar.selectbox(
        "Sales / Revenue Column", 
        num_cols, 
        index=num_cols.index(auto_cols["revenue_col"]) if auto_cols["revenue_col"] in num_cols else 0
    )
    
    cost_options = ["None"] + num_cols
    sel_cost = st.sidebar.selectbox(
        "Expenses / Costs Column", 
        cost_options, 
        index=cost_options.index(auto_cols["cost_col"]) if auto_cols["cost_col"] in cost_options else 0
    )
    
    cat_options = ["None"] + cat_cols
    sel_cat = st.sidebar.selectbox(
        "Product / Client / Group Column", 
        cat_options, 
        index=cat_options.index(auto_cols["category_col"]) if auto_cols["category_col"] in cat_options else 0
    )
    
    date_options = ["None"] + date_cols
    sel_date = st.sidebar.selectbox(
        "Date Column (Optional)", 
        date_options, 
        index=date_options.index(auto_cols["date_col"]) if auto_cols["date_col"] in date_options else 0
    )

    facts = analyze_dataset(df, revenue_col=sel_rev, cost_col=sel_cost, category_col=sel_cat)

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### 👤 Business: `{st.session_state.get('company_name', 'SME')}`")
    if st.sidebar.button("🔒 Exit Workspace"):
        st.session_state["authenticated"] = False
        st.rerun()

    # 🛠️ FOUNDER ADMIN PANEL (PROTECTED BY PASSWORD)
    st.sidebar.markdown("---")
    with st.sidebar.expander("🛠️ Founder Admin Panel"):
        admin_pass = st.text_input("Master Password", type="password", key="admin_password_input")
        if admin_pass == "Caleb@2020":
            st.success("🔓 Admin Unlocked")
            DB_FILE = "sme_intelligence.duckdb"
            
            if os.path.exists(DB_FILE):
                conn = duckdb.connect(DB_FILE)
                
                st.markdown("#### 👥 Registered Tenants & Activity")
                try:
                    tenants_df = conn.execute("SELECT email, company_name, created_at, last_active, total_uploads FROM tenants ORDER BY last_active DESC").fetchdf()
                    st.dataframe(tenants_df, use_container_width=True)
                except Exception:
                    st.info("No tenant data recorded yet.")
                
                st.markdown("#### 💬 Client Feedback Inbox")
                try:
                    feedback_df = conn.execute("SELECT email, category, message, timestamp FROM feedback ORDER BY timestamp DESC").fetchdf()
                    st.dataframe(feedback_df, use_container_width=True)
                except Exception:
                    st.info("No feedback submitted yet.")
                    
                conn.close()
            else:
                st.info("Database file not created yet.")
        elif admin_pass:
            st.error("❌ Incorrect password")

    # 6. SME WORKSPACE TABS
    tabs = st.tabs([
        "💰 Cash & Profit Overview", 
        "🏆 Top Products & Sales", 
        "🚨 Red Flags & Audit", 
        "🧮 Pricing Calculator", 
        "🧠 AI Fractional CFO Brief", 
        "📊 Bank & Investor Pitch Deck",
        "💬 Feedback & Support"
    ])

    with tabs[0]: # Cash & Profit Overview
        st.subheader("Monthly Cash & Profit Summary")
        if facts["warnings"]:
            for warning in facts["warnings"]:
                st.warning(f"⚠️ {warning}")

        tot_rev = facts["totals"]["total_revenue"]
        tot_cost = facts["totals"]["total_costs"]
        profit = facts["totals"]["net_profit"]
        margin = facts["totals"]["profit_margin"]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Money In (Sales)", f"{currency}{tot_rev:,.2f}")
        c2.metric("Total Money Out (Costs)", f"{currency}{tot_cost:,.2f}")
        c3.metric("Take-Home Net Profit", f"{currency}{profit:,.2f}")
        c4.metric("Profit Margin", f"{margin:.1f}%")
        
        st.markdown("---")
        gcol1, gcol2 = st.columns(2)
        with gcol1:
            fig_overview = px.bar(
                x=["Sales", "Costs", "Net Profit"],
                y=[tot_rev, tot_cost, profit],
                title="Sales vs. Expenses Breakdown",
                labels={"x": "Category", "y": f"Amount ({currency})"},
                color=["Sales", "Costs", "Net Profit"],
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
                    title=f"Top {sel_cat} Share of Sales",
                    template="plotly_dark",
                    hole=0.4
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                fig_hist = px.histogram(df, x=sel_rev, title=f"Distribution of {sel_rev}", template="plotly_dark")
                st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown("### Uploaded Data Preview")
        st.dataframe(df.head(10), use_container_width=True)

    with tabs[1]: # Top Products & Sales
        st.subheader("Sales Trends & Leaderboards")
        if sel_date != "None" and sel_date in df.columns:
            trend_df = df.groupby(sel_date)[sel_rev].sum().reset_index()
            fig_trend = px.line(trend_df, x=sel_date, y=sel_rev, title=f"{sel_rev} Over Time", markers=True, template="plotly_dark")
            st.plotly_chart(fig_trend, use_container_width=True)

        if sel_cat != "None" and facts["revenue_by_category"]:
            grouped_df = pd.DataFrame(list(facts["revenue_by_category"].items()), columns=[sel_cat, sel_rev])
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.markdown("#### Top Revenue Contributors")
                st.dataframe(grouped_df.head(10), use_container_width=True)
            with col_t2:
                fig_bar = px.bar(grouped_df.head(10), x=sel_cat, y=sel_rev, title=f"Top 10 {sel_cat} by Revenue", template="plotly_dark")
                st.plotly_chart(fig_bar, use_container_width=True)

    with tabs[2]: # Red Flags & Audit
        st.subheader("Data Health Check & Red Flag Audit")
        dh1, dh2, dh3 = st.columns(3)
        dh1.metric("Data Quality Score", f"{facts['metadata']['data_health_index']}%")
        dh2.metric("Blank / Missing Cells", f"{facts['metadata']['missing_cells']:,}")
        dh3.metric("Duplicate Entries", f"{facts['metadata']['duplicate_rows']:,}")

        if facts["anomalies"]:
            st.markdown("##### 🚨 Unusual Transactions / Potential Outliers")
            st.dataframe(pd.DataFrame(facts["anomalies"]).head(5), use_container_width=True)
        else:
            st.success("✅ No suspicious transaction outliers detected.")

    with tabs[3]: # Pricing Calculator
        st.subheader("Business Growth & Price Hike Calculator")
        st.caption("Use preset buttons or manual sliders to see how price increases or cost cuts affect your profit.")
        
        st.markdown("#### ⚡ Quick Business Scenarios")
        col_p1, col_p2, col_p3 = st.columns(3)
        if col_p1.button("📈 5% Price Increase"):
            st.session_state["sim_price"] = 5
            st.session_state["sim_vol"] = 0
            st.session_state["sim_vc"] = 0
            st.rerun()

        if col_p2.button("🛍️ Sale Boost (+20% Volume, -5% Price)"):
            st.session_state["sim_price"] = -5
            st.session_state["sim_vol"] = 20
            st.session_state["sim_vc"] = 0
            st.rerun()

        if col_p3.button("✂️ 10% Cost Reduction"):
            st.session_state["sim_price"] = 0
            st.session_state["sim_vol"] = 0
            st.session_state["sim_vc"] = -10
            st.rerun()

        st.markdown("---")
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            scenario_name = st.text_input("Scenario Label", value="Growth Plan 1")
            price_adj = st.slider("Price Adjustment (%)", -50, 50, value=int(st.session_state["sim_price"]))
            volume_adj = st.slider("Sales Volume Shift (%)", -50, 50, value=int(st.session_state["sim_vol"]))
        with col_w2:
            fixed_cost_change = st.number_input("Fixed Expense Adjustment (e.g., +Rent)", value=0.0, step=500.0)
            variable_cost_pct = st.slider("Variable Expense Shift (%)", -50, 50, value=int(st.session_state["sim_vc"]))

        current_res = calculate_scenario(facts["totals"], price_adj, volume_adj, fixed_cost_change, variable_cost_pct)

        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Projected Sales", f"{currency}{current_res['revenue']:,.2f}", f"{price_adj + volume_adj}%")
        sc2.metric("Projected Expenses", f"{currency}{current_res['costs']:,.2f}")
        sc3.metric("Projected Net Profit", f"{currency}{current_res['net_profit']:,.2f}", f"{current_res['profit_delta']:+,.2f}")
        sc4.metric("Projected Margin", f"{current_res['profit_margin']:.1f}%")

        if st.button("💾 Save Plan to Workspace Database", type="primary"):
            save_scenario_db(st.session_state["session_id"], scenario_name, current_res)
            st.success(f"Saved '{scenario_name}' to database!")

        saved_db_scenarios = load_scenarios_db(st.session_state["session_id"])
        if saved_db_scenarios:
            st.markdown("### 📊 Stored Growth Models")
            st.dataframe(pd.DataFrame(saved_db_scenarios)[['scenario_name', 'revenue', 'costs', 'net_profit', 'margin']], use_container_width=True)

        st.markdown("---")
        st.markdown("### 📈 Estimated Take-Home Profit Matrix (Price vs. Sales Volume)")
        sens_matrix = generate_sensitivity_matrix(facts["totals"])
        st.dataframe(pd.DataFrame(sens_matrix), use_container_width=True)

    with tabs[4]: # AI Fractional CFO Brief
        st.subheader("On-Demand AI Fractional CFO Advisor")
        st.caption("Generate a plain-English, 6-section CFO brief evaluating your financial health and saved scenarios.")
        
        if st.button("Generate AI CFO Advice Brief", type="primary"):
            with st.spinner("🤖 Analyzing business data & scenarios..."):
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
                        st.markdown("### 📋 Monthly Business Intelligence Brief")
                        st.markdown('<div class="saas-card">', unsafe_allow_html=True)
                        st.markdown(res_json.get("advisory", ""))
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        log_tenant_activity(
                            st.session_state.get("user_email", "guest"), 
                            st.session_state.get("company_name", "SME"), 
                            "Generated AI CFO Brief"
                        )
                    else:
                        st.error(res_json.get('detail', 'AI advisory request failed.'))
                except Exception as e:
                    st.error(f"Connection error: {e}")

    with tabs[5]: # Bank & Investor Pitch Deck
        st.subheader("Automated Presentation Deck (.pptx)")
        st.caption("Generate a professional 12-slide presentation deck ready for bank loan applications, partners, or local investors.")
        
        if st.button("Generate Pitch Deck (.pptx)", type="primary"):
            with st.spinner("📊 Building professional presentation deck..."):
                try:
                    deck_bytes = create_executive_deck(facts, currency=currency, filename=uploaded.name)
                    st.session_state["deck_bytes"] = deck_bytes
                    st.success("✅ Presentation deck generated successfully!")
                    
                    log_tenant_activity(
                        st.session_state.get("user_email", "guest"), 
                        st.session_state.get("company_name", "SME"), 
                        "Generated Pitch Deck (.pptx)"
                    )
                except Exception as e:
                    st.error(f"Error generating presentation deck: {e}")

        if "deck_bytes" in st.session_state:
            st.download_button(
                label="📥 Download Bank-Ready Deck (.pptx)",
                data=st.session_state["deck_bytes"],
                file_name="Business_Financial_Overview.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                type="primary"
            )

    with tabs[6]: # Feedback & Support
        st.subheader("💬 Direct Founder Feedback & Support")
        st.caption("Encountered an issue or have a feature request? Send a direct message to the app founder.")
        
        with st.form("in_app_feedback_form"):
            fb_email = st.text_input("Your Email", value=st.session_state.get("user_email", ""))
            fb_category = st.selectbox("Topic", ["Feature Request", "Bug Report / Error", "General Question", "Praise 🎉"])
            fb_message = st.text_area("Your Message / Feedback")
            fb_submit = st.form_submit_button("📨 Submit Feedback")
            
            if fb_submit:
                if fb_message.strip():
                    save_feedback_db(fb_email, fb_category, fb_message)
                    st.success("✅ Thank you! Your feedback has been sent directly to the founder.")
                else:
                    st.warning("Please enter a message before submitting.")
else:
    st.info("👋 Welcome! Please upload your monthly business spreadsheet (.csv or .xlsx) above to begin.")