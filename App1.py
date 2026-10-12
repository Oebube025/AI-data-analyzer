"""
Executive Data Intelligence Suite - Streamlit Frontend (App1.py)
Frictionless SME Login, automated CFO briefs, bank-ready decks, 
in-app feedback, and password-protected Founder Admin panel.
"""

import hashlib
import hmac
import io
import os
import re
import time
import duckdb

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from analysis import (analyze_dataset, build_ai_payload, prepare_dataframe, suggest_columns,
                      valid_numeric_columns)
from database import (init_db, load_scenarios_db,
                      save_scenario_db, log_tenant_activity, save_feedback_db)
from deck_builder import create_executive_deck
from simulator import calculate_scenario, generate_sensitivity_matrix

APP_VERSION = "1.0"

st.set_page_config(page_title="AI CFO Suite for Small Business", page_icon="💼",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #0f172a; color: #e2e8f0; }
    section[data-testid="stSidebar"] { background-color: #090d16; border-right: 1px solid #1e293b; }
    .saas-card { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1px solid #334155; padding: 28px; border-radius: 12px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.4); margin-bottom: 20px; }
    .sme-badge { background-color: #10b981; color: #ffffff; font-size: 0.75rem; font-weight: 700; padding: 3px 10px; border-radius: 6px; vertical-align: middle; margin-left: 8px; }
    h1, h2, h3 { color: #f8fafc; letter-spacing: -0.02em; }
    .stButton>button { background-color: #2563eb; color: white; border: none; border-radius: 8px; font-weight: 600; padding: 0.6rem 1.2rem; width: 100%; transition: all 0.2s ease; }
    .stButton>button:hover { background-color: #1d4ed8; box-shadow: 0 4px 12px rgba(37,99,235,0.4); }
</style>
""", unsafe_allow_html=True)


def secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, os.getenv(name, default)))
    except Exception:
        return os.getenv(name, default)


BACKEND_URL = secret("BACKEND_URL", "http://127.0.0.1:8000")
BACKEND_SECRET_KEY = secret("BACKEND_SECRET_KEY")
DB_FILE = secret("DB_PATH", "executive_intelligence.duckdb")


@st.cache_resource
def _init():
    init_db()
    return True


_init()


@st.cache_data(ttl=60)
def check_backend_status(url: str, token: str) -> bool:
    try:
        return requests.get(f"{url}/health", headers={"X-API-Key": token}, timeout=3).status_code == 200
    except Exception:
        return False


@st.cache_data(show_spinner=False)
def get_facts(df: pd.DataFrame, rev, cost, cat, date, notes: tuple):
    return analyze_dataset(df, revenue_col=rev, cost_col=cost, category_col=cat,
                           date_col=date, prep_notes=list(notes))


def read_upload(name: str, data: bytes, sheet=None) -> pd.DataFrame:
    if name.lower().endswith(".xlsx"):
        return pd.read_excel(io.BytesIO(data), sheet_name=sheet if sheet is not None else 0)
    last_err = None
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(data), encoding=enc, sep=None, engine="python")
        except Exception as e:
            last_err = e
    raise last_err


def money(v, cur):
    return f"{cur}{v:,.2f}"


def pct(v):
    return "n/a" if v is None or pd.isna(v) else f"{v:.1f}%"


def idx(options, value):
    return options.index(value) if value in options else 0


# ----------------------------------------------------------------- FRICTIONLESS SME AUTH GATE
if not st.session_state.get("authenticated"):
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(f"<br><br><h1 style='text-align:center;'>AI CFO Suite "
                    f"<span class='sme-badge'>FOR SMALL BUSINESS</span></h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#94a3b8;margin-bottom:30px;'>"
                    "Automated Financial Audits • Bank-Ready Decks • On-Demand CFO Advice</p>", unsafe_allow_html=True)
        
        with st.form("sme_auth_form"):
            st.markdown("### 🔐 Enter Business Workspace")
            client_email = st.text_input("Business Email", placeholder="owner@company.com")
            company_name = st.text_input("Company Name", placeholder="Acme Services")
            access_key = st.text_input("Access Passcode", type="password", placeholder="Enter beta passcode")
            
            submitted = st.form_submit_button("🚀 Launch Business Dashboard")
            if submitted:
                # Accept backend secret key or the default demo passkey
                if access_key == BACKEND_SECRET_KEY or access_key == "demo-beta-2026" or not BACKEND_SECRET_KEY:
                    user_email = client_email.strip().lower() if client_email else "guest@sme.com"
                    comp_name = company_name.strip() if company_name else "Independent SME"
                    
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = user_email
                    st.session_state["company_name"] = comp_name
                    
                    log_tenant_activity(user_email, comp_name, "Workspace Sign-In")
                    st.rerun()
                else:
                    st.error("❌ Invalid access passcode. (Tip: Use demo-beta-2026)")
    st.stop()

USER = st.session_state["user"]
COMPANY = st.session_state.get("company_name", "Independent SME")

# ------------------------------------------------------------- WORKSPACE
if not BACKEND_SECRET_KEY:
    st.warning("⚠️ BACKEND_SECRET_KEY is not configured, so AI advisory is disabled.")
elif not check_backend_status(BACKEND_URL, BACKEND_SECRET_KEY):
    st.warning("⚠️ Backend API is waking up or offline. AI advisory may not work yet.")

uploaded = st.file_uploader("📁 Upload Monthly Business File (.csv or .xlsx - QuickBooks, Shopify, Excel)", type=["csv", "xlsx"])
if uploaded is None:
    st.info("👋 Upload your monthly business spreadsheet above to get started.")
    st.stop()

data = uploaded.getvalue()
if len(data) / (1024 * 1024) > 10:
    st.error("❌ File size exceeds the strict 10MB limit.")
    st.stop()

sheet = None
if uploaded.name.lower().endswith(".xlsx"):
    try:
        sheets = pd.ExcelFile(io.BytesIO(data)).sheet_names
    except Exception as e:
        st.error(f"Could not open the Excel file: {e}")
        st.stop()
    sheet = st.selectbox("Sheet", sheets) if len(sheets) > 1 else sheets[0]

data_key = f"{hashlib.md5(data).hexdigest()}:{sheet}"
if st.session_state.get("data_key") != data_key:
    try:
        raw = read_upload(uploaded.name, data, sheet)
    except Exception as e:
        st.error(f"Error parsing file: {e}")
        st.stop()
    if raw.empty:
        st.error("The file has no rows.")
        st.stop()
    clean, notes = prepare_dataframe(raw)
    st.session_state.update(data_key=data_key, active_df=clean, prep_notes=notes,
                            suggested=suggest_columns(clean))
    st.session_state.pop("deck_bytes", None)
    log_tenant_activity(USER, COMPANY, f"Uploaded File: {uploaded.name}")

df = st.session_state["active_df"]
notes = st.session_state["prep_notes"]
sug = st.session_state["suggested"]

st.sidebar.markdown("### ⚙️ Business Settings")
currency = st.sidebar.selectbox("Currency", ["₦", "$", "€", "£"])

nums = valid_numeric_columns(df)
if not nums:
    st.error("No numeric columns were found. Please check that your file has a revenue or amount column.")
    st.stop()
cats = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c])]
cats = [c for c in cats if not pd.api.types.is_datetime64_any_dtype(df[c])]

sel_rev = st.sidebar.selectbox("Sales / Revenue Column", nums, index=idx(nums, sug["revenue"]))
cost_opts = ["None"] + [c for c in nums if c != sel_rev]
sel_cost = st.sidebar.selectbox("Expenses / Costs Column", cost_opts, index=idx(cost_opts, sug["cost"]))
cat_opts = ["None"] + cats
sel_cat = st.sidebar.selectbox("Product / Client / Group Column", cat_opts, index=idx(cat_opts, sug["category"]))
date_opts = ["None"] + list(df.columns)
sel_date = st.sidebar.selectbox("Date / Time Column (Optional)", date_opts, index=idx(date_opts, sug["date"]))

facts = get_facts(df, sel_rev, sel_cost, sel_cat, sel_date, tuple(notes))
totals, meta, trend = facts["totals"], facts["metadata"], facts["trend"]
cost_known = totals["cost_known"]

st.sidebar.markdown("---")
st.sidebar.markdown(f"### 👤 Company: `{COMPANY}`")
if st.sidebar.button("🔒 Exit Workspace"):
    st.session_state["authenticated"] = False
    st.rerun()

# --- FOUNDER ADMIN PANEL (PASSWORD: Caleb@2020) ---
st.sidebar.markdown("---")
with st.sidebar.expander("🛠️ Founder Admin Panel"):
    admin_pass = st.text_input("Master Password", type="password", key="admin_password_input")
    if admin_pass == "Caleb@2020":
        st.success("🔓 Admin Unlocked")
        if os.path.exists(DB_FILE):
            conn = duckdb.connect(DB_FILE)
            st.markdown("#### 👥 Registered Tenants")
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
            st.info("Database file not found.")
    elif admin_pass:
        st.error("❌ Incorrect password")

tabs = st.tabs(["💰 Cash & Profit", "🏆 Top Products", "🚨 Red Flags",
                "🧮 Pricing Calculator", "🧠 AI CFO Brief", "📊 Pitch Deck", "💬 Feedback"])

with tabs[0]:
    st.subheader("Monthly Cash & Profit Summary")
    for w in facts["warnings"]:
        st.warning(f"⚠️ {w}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Money In (Sales)", money(totals["total_revenue"], currency))
    c2.metric("Total Money Out (Costs)", money(totals["total_costs"], currency) if cost_known else "Not provided")
    c3.metric("Take-Home Net Profit", money(totals["net_profit"], currency) if cost_known else "n/a")
    c4.metric("Profit Margin", pct(totals["profit_margin"]))
    st.markdown("---")

    g1, g2 = st.columns(2)
    with g1:
        if cost_known:
            fig = px.bar(x=["Sales", "Costs", "Net Profit"],
                         y=[totals["total_revenue"], totals["total_costs"], totals["net_profit"]],
                         title="Sales vs. Expenses Breakdown", labels={"x": "Metric", "y": f"Amount ({currency})"},
                         color=["Sales", "Costs", "Net Profit"], template="plotly_dark")
        else:
            fig = px.histogram(df, x=sel_rev, title=f"Distribution of {sel_rev}", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        rbc = facts["revenue_by_category"]
        if rbc:
            pie_df = pd.DataFrame(list(rbc.items())[:6], columns=["Category", "Revenue"])
            pie_df = pie_df[pie_df["Revenue"] > 0]
            st.plotly_chart(px.pie(pie_df, names="Category", values="Revenue",
                                   title=f"Top {meta['category_column']} Revenue Share",
                                   template="plotly_dark", hole=0.4), use_container_width=True)
        else:
            st.info("Select a category column to see revenue share.")
    st.markdown("### Uploaded Data Preview")
    st.dataframe(df.head(10), use_container_width=True)

with tabs[1]:
    st.subheader("Sales Trends & Leaderboards")
    if len(trend["points"]) >= 2:
        tdf = pd.DataFrame(trend["points"])
        st.plotly_chart(px.line(tdf, x="period", y="revenue", markers=True, template="plotly_dark",
                                title=f"Revenue by {trend['granularity']} (chronological)"),
                        use_container_width=True)
        if trend["change_pct"] is not None:
            st.metric(f"Latest {trend['granularity']} vs previous", f"{trend['change_pct']:+.1f}%")
    elif sel_date == "None":
        st.info("Select a date column in the sidebar to see trends.")
    else:
        st.info("Not enough dated data to draw a trend.")

    if facts["revenue_by_category"]:
        gdf = pd.DataFrame(list(facts["revenue_by_category"].items()), columns=["Category", "Revenue"])
        a, b = st.columns(2)
        with a:
            st.markdown("#### Top Revenue Contributors")
            st.dataframe(gdf.head(10), use_container_width=True)
        with b:
            st.plotly_chart(px.bar(gdf.head(10), x="Category", y="Revenue", template="plotly_dark",
                                   title="Top 10 by Revenue"), use_container_width=True)

with tabs[2]:
    st.subheader("Data Health Check & Red Flag Audit")
    d1, d2, d3 = st.columns(3)
    d1.metric("Data Quality Score", f"{meta['data_health_index']}%")
    d2.metric("Missing Cells", f"{meta['missing_cells']:,}")
    d3.metric("Duplicate Rows", f"{meta['duplicate_rows']:,}")
    if facts["anomalies"]:
        st.markdown(f"##### 🚨 Unusual Transactions / Potential Outliers")
        st.dataframe(pd.DataFrame(facts["anomalies"]).head(5), use_container_width=True)
    else:
        st.success("✅ No suspicious transaction outliers detected.")

with tabs[3]:
    st.subheader("Business Growth & Price Hike Calculator")
    st.caption("Use preset buttons or manual sliders to see how price increases or cost cuts affect your profit.")

    sim_totals = dict(totals)
    cost_assumed = False
    if not cost_known:
        st.info("No cost column selected. Enter an assumption to model scenarios (clearly labelled as assumed).")
        ratio = st.slider("Assumed total costs as % of revenue", 0, 100, 70)
        sim_totals["total_costs"] = totals["total_revenue"] * ratio / 100
        cost_assumed = True

    w1, w2 = st.columns(2)
    with w1:
        scenario_name = st.text_input("Scenario Label", value="Growth Plan 1")
        price_adj = st.slider("Price Adjustment (%)", -50, 50, 5)
        volume_adj = st.slider("Sales Volume Shift (%)", -50, 50, 0)
    with w2:
        fixed_share = st.slider("Share of current costs that are fixed (%)", 0, 100, 30) / 100
        fixed_change = st.number_input("Fixed Expense Adjustment (e.g., +Rent)", value=0.0, step=1000.0)
        var_pct = st.slider("Variable Expense Shift (%)", -50, 50, 0)

    res = calculate_scenario(sim_totals, price_adj, volume_adj, fixed_change, var_pct, fixed_share)
    res["cost_assumed"] = cost_assumed
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Projected Sales", money(res["revenue"], currency),
              f"{((1 + price_adj / 100) * (1 + volume_adj / 100) - 1) * 100:+.1f}%")
    s2.metric("Projected Expenses", money(res["costs"], currency))
    s3.metric("Projected Net Profit", money(res["net_profit"], currency), f"{res['profit_delta']:+,.2f}")
    s4.metric("Projected Margin", pct(res["profit_margin"]))

    if st.button("💾 Save Plan to Workspace Database", type="primary"):
        save_scenario_db(USER, scenario_name, res)
        log_tenant_activity(USER, COMPANY, f"Saved Scenario: {scenario_name}")
        st.success(f"Saved '{scenario_name}' to database!")

    saved = load_scenarios_db(USER)
    if saved:
        st.markdown("### 📊 Stored Growth Models")
        st.dataframe(pd.DataFrame(saved)[["scenario_name", "revenue", "costs", "net_profit", "margin"]],
                     use_container_width=True)

    st.markdown("---")
    st.markdown("### 📈 Estimated Take-Home Profit Matrix (Price vs. Sales Volume)")
    st.dataframe(pd.DataFrame(generate_sensitivity_matrix(sim_totals, fixed_share)), use_container_width=True)

with tabs[4]:
    st.subheader("On-Demand AI Fractional CFO Advisor")
    st.caption("Generate a plain-English, 6-section CFO brief evaluating your financial health and saved scenarios.")
    consent = st.checkbox("I understand that aggregated figures (totals, category names and revenue, outlier "
                          "values) are sent to our AI provider. Raw rows are never sent.")
    if st.button("Generate AI CFO Advice Brief", type="primary", disabled=not consent):
        with st.spinner("🤖 Analyzing business data & scenarios..."):
            try:
                res_ai = requests.post(
                    f"{BACKEND_URL}/api/ai-advisory",
                    json={"verified_stats": build_ai_payload(facts), "saved_scenarios": load_scenarios_db(USER)},
                    headers={"X-API-Key": BACKEND_SECRET_KEY, "X-User-Id": USER},
                    timeout=120,
                )
                try:
                    body = res_ai.json()
                except Exception:
                    body = {"detail": res_ai.text or "Server error."}
                if res_ai.status_code == 200:
                    st.markdown("### 📋 Monthly Business Intelligence Brief")
                    st.markdown('<div class="saas-card">', unsafe_allow_html=True)
                    st.markdown(body.get("advisory", ""))
                    st.markdown("</div>", unsafe_allow_html=True)
                    log_tenant_activity(USER, COMPANY, "Generated AI CFO Brief")
                else:
                    st.error(body.get("detail", "AI advisory request failed."))
            except Exception as e:
                st.error(f"Connection error: {e}")

with tabs[5]:
    st.subheader("Automated Presentation Deck (.pptx)")
    st.caption("Generate a professional 12-slide presentation deck ready for bank loan applications, partners, or local investors.")
    if st.button("Generate Pitch Deck (.pptx)", type="primary"):
        with st.spinner("📊 Building professional presentation deck..."):
            try:
                st.session_state["deck_bytes"] = create_executive_deck(
                    facts, currency=currency, filename=uploaded.name, scenarios=load_scenarios_db(USER))
                st.success("✅ Presentation deck generated successfully!")
                log_tenant_activity(USER, COMPANY, "Generated Pitch Deck (.pptx)")
            except Exception as e:
                st.error(f"Error generating presentation: {e}")
    if "deck_bytes" in st.session_state:
        st.download_button("📥 Download Bank-Ready Deck (.pptx)", data=st.session_state["deck_bytes"],
                           file_name="Business_Financial_Overview.pptx",
                           mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                           type="primary")

with tabs[6]:
    st.subheader("💬 Direct Founder Feedback & Support")
    st.caption("Encountered an issue or have a feature request? Send a direct message to the app founder.")
    
    with st.form("in_app_feedback_form"):
        fb_category = st.selectbox("Topic", ["Feature Request", "Bug Report / Error", "General Question", "Praise 🎉"])
        fb_message = st.text_area("Your Message / Feedback")
        fb_submit = st.form_submit_button("📨 Submit Feedback")
        
        if fb_submit:
            if fb_message.strip():
                save_feedback_db(USER, fb_category, fb_message)
                st.success("✅ Thank you! Your feedback has been sent directly to the founder.")
            else:
                st.warning("Please enter a message before submitting.")