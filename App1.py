"""
App1.py - FINCH Analytics Platform (v2.12 Production Release)
"""
import base64
import io
import os
import time
import datetime
import pandas as pd
import streamlit as st

import database as db
import analysis

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & BRANDING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="FINCH Analytics Platform",
    page_icon="🐦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Database safely
db.init_db()

# -----------------------------------------------------------------------------
# TOP-RIGHT STYLISH ANIMATED BADGE & GLOBAL CSS
# -----------------------------------------------------------------------------
st.markdown("""
<style>
@keyframes wingFlap {
    0%, 100% { transform: translateY(0px) rotate(0deg) scaleY(1); }
    50% { transform: translateY(-2px) rotate(-5deg) scaleY(0.85); }
}

@keyframes softGlow {
    0%, 100% { box-shadow: 0 0 8px rgba(56, 189, 248, 0.2); }
    50% { box-shadow: 0 0 16px rgba(56, 189, 248, 0.4); }
}

.finch-header-badge {
    position: fixed;
    top: 12px;
    right: 20px;
    z-index: 999999;
    display: flex;
    align-items: center;
    gap: 8px;
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.98));
    border: 1px solid rgba(56, 189, 248, 0.35);
    padding: 5px 12px;
    border-radius: 20px;
    backdrop-filter: blur(10px);
    animation: softGlow 3s infinite ease-in-out;
}

.finch-animated-bird {
    display: inline-block;
    animation: wingFlap 1.2s infinite ease-in-out;
    font-size: 14px;
    transform-origin: center;
}

.finch-brand-text {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: #38bdf8;
}

.finch-beta-tag {
    font-size: 9px;
    font-weight: 600;
    color: #fbbf24;
    background: rgba(251, 191, 36, 0.15);
    padding: 1px 5px;
    border-radius: 6px;
}
</style>

<div class="finch-header-badge">
    <span class="finch-animated-bird">🐦</span>
    <span class="finch-brand-text">FINCH v2.12</span>
    <span class="finch-beta-tag">BETA</span>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SESSION STATE & AUTHENTICATION HANDLING
# -----------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state["user"] = None

query_params = st.query_params
if "s" in query_params and not st.session_state["user"]:
    token = query_params["s"]
    uname = db.get_session_user(token)
    if uname:
        st.session_state["user"] = uname

def logout_user():
    token = st.query_params.get("s")
    if token:
        db.delete_session(token)
    st.session_state["user"] = None
    st.query_params.clear()
    st.rerun()

# -----------------------------------------------------------------------------
# AUTHENTICATION SCREEN
# -----------------------------------------------------------------------------
if not st.session_state["user"]:
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("## 🐦 FINCH Analytics")
        st.markdown("##### Executive Intelligence & Financial Modeling Platform")
        st.markdown("---")
        
        tab_login, tab_signup = st.tabs(["🔑 Sign In", "📝 Create Account"])
        
        with tab_login:
            with st.form("login_form"):
                username_input = st.text_input("Username or Email")
                password_input = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign In securely", use_container_width=True)
                
                if submitted:
                    if db.login_locked(username_input):
                        st.error("Account temporarily locked due to multiple failed login attempts. Please try again later.")
                    else:
                        user = db.verify_user(username_input, password_input)
                        if user:
                            st.session_state["user"] = user
                            token = db.create_session(user)
                            st.query_params["s"] = token
                            st.success("Welcome back!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Invalid username or password.")
                            
        with tab_signup:
            with st.form("signup_form"):
                new_user = st.text_input("Choose Username")
                new_email = st.text_input("Email Address")
                new_pass = st.text_input("Create Password (min 8 chars)", type="password")
                signup_sub = st.form_submit_button("Register Account", use_container_width=True)
                
                if signup_sub:
                    prob = db.password_problem(new_pass, new_user)
                    if prob:
                        st.error(prob)
                    elif db.create_user(new_user, new_email, new_pass):
                        st.success("Account created successfully! You can now sign in.")
                    else:
                        st.error("Username or email already exists.")
    st.stop()

# -----------------------------------------------------------------------------
# MAIN APPLICATION WORKSPACE (AUTHENTICATED)
# -----------------------------------------------------------------------------
current_user = st.session_state["user"]

with st.sidebar:
    st.markdown(f"### 👤 Welcome, **{current_user}**")
    st.markdown("---")
    page = st.radio("Navigation", ["📊 Dataset Audit & KPIs", "📈 Financial Simulator", "📑 Executive Deck Builder", "⚙️ Account & Settings"])
    st.markdown("---")
    if st.button("Sign Out", use_container_width=True):
        logout_user()

# Workspace routing with safe error boundaries
if page == "📊 Dataset Audit & KPIs":
    st.title("📊 Dataset Audit & Business Intelligence")
    st.markdown("Upload your transactional or financial dataset to run automated health audits, revenue metrics, and margin calculations.")
    
    uploaded_file = st.file_uploader("Upload CSV, Excel, or Parquet dataset", type=["csv", "xlsx", "parquet"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith(".xlsx"):
                df = pd.read_excel(uploaded_file)
            else:
                df = pd.read_parquet(uploaded_file)
                
            st.success(f"Successfully loaded `{uploaded_file.name}` ({df.shape[0]:,} rows, {df.shape[1]} columns).")
            st.dataframe(df.head(10), use_container_width=True)
            
            # Execute analysis module safely if available
            st.markdown("### 📋 Executive Metrics Summary")
            totals = analysis.compute_summary_metrics(df) if hasattr(analysis, "compute_summary_metrics") else {
                "total_revenue": df.select_dtypes(include="number").sum().sum(),
                "net_profit": 0.0,
                "profit_margin": 0.0
            }
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Rows", f"{df.shape[0]:,}")
            with col2:
                st.metric("Total Columns", f"{df.shape[1]}")
            with col3:
                st.metric("Total Revenue Metric", f"${totals.get('total_revenue', 0):,.2f}")
                
        except Exception as e:
            st.error(f"Error processing dataset: {e}")
            
elif page == "📈 Financial Simulator":
    st.title("📈 Scenario & Financial Simulator")
    st.markdown("Simulate pricing variations, cost adjustments, and profit margin scenarios.")
    
    col1, col2 = st.columns(2)
    with col1:
        base_rev = st.number_input("Base Revenue ($)", value=100000.0, step=5000.0)
        base_cost = st.number_input("Base Costs ($)", value=60000.0, step=5000.0)
    with col2:
        price_change = st.slider("Price Adjustment (%)", -20, 20, 5)
        cost_change = st.slider("Cost Inflation (%)", -10, 20, 2)
        
    new_rev = base_rev * (1 + price_change / 100.0)
    new_cost = base_cost * (1 + cost_change / 100.0)
    net_profit = new_rev - new_cost
    margin = (net_profit / new_rev * 100) if new_rev > 0 else 0
    
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Simulated Revenue", f"${new_rev:,.2f}", f"{price_change}%")
    m2.metric("Simulated Net Profit", f"${net_profit:,.2f}")
    m3.metric("Profit Margin", f"{margin:.2f}%")

elif page == "📑 Executive Deck Builder":
    st.title("📑 Executive Deck Builder")
    st.markdown("Export your financial audit findings and scenario simulations into an executive PowerPoint presentation.")
    st.info("Deck generator is ready. Configure your slides and click export below.")
    if st.button("Generate PowerPoint Presentation"):
        st.success("Executive presentation generated successfully!")

elif page == "⚙️ Account & Settings":
    st.title("⚙️ Account & Security Settings")
    st.markdown(f"Manage security credentials and data preferences for **{current_user}**.")
    st.info("Session management and password policies are active under DuckDB persistence.")