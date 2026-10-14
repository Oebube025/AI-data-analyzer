"""
FINCH - AI Business Intelligence Frontend (App1.py)
Integrated with cinematic splash, banner bird intro, and custom Space Grotesk shimmering header.
"""

import hashlib
import hmac
import io
import os
import re
import duckdb

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from analysis import (analyze_dataset, build_ai_payload, prepare_dataframe, suggest_columns,
                      valid_numeric_columns)
from database import (init_db, load_scenarios_db, save_scenario_db, delete_scenarios_db,
                      log_tenant_activity, save_feedback_db, 
                      create_user, verify_user, get_user_email,
                      save_audit_history_db, load_user_history_db)
from deck_builder import create_executive_deck
from simulator import calculate_scenario, generate_sensitivity_matrix
from finch_intro import show_finch_intro

APP_VERSION = "2.11"

st.set_page_config(page_title="FINCH | AI Business Intelligence", page_icon="🐦",
                   layout="wide", initial_sidebar_state="expanded")

# --- CINEMATIC INTRO SPLASH SCREEN (MATCHING #0b0f19) ---
show_finch_intro(mode="splash", bg="#0b0f19")

# --- SIGNATURE DARK GLASSMORPHISM STYLING ---
st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #f1f5f9; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    section[data-testid="stSidebar"] { background-color: #050811; border-right: 1px solid rgba(30, 41, 59, 0.6); }
    .saas-card { 
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.65) 0%, rgba(15, 23, 42, 0.85) 100%); 
        border: 1px solid rgba(51, 65, 85, 0.5); backdrop-filter: blur(16px);
        padding: 28px; border-radius: 18px; box-shadow: 0 12px 32px -4px rgba(0, 0, 0, 0.6); margin-bottom: 24px; 
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #162032, #101726);
        border: 1px solid rgba(71, 85, 105, 0.4); padding: 20px; border-radius: 16px;
        box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.05), 0 12px 28px rgba(0, 0, 0, 0.5);
    }
    div[data-testid="stMetric"] label { color: #94a3b8 !important; font-weight: 500; font-size: 0.85rem !important; text-transform: uppercase; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #f8fafc !important; font-weight: 700; }
    h1, h2, h3 { color: #f8fafc; letter-spacing: -0.03em; font-weight: 700; }
    .stButton>button { 
        background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border: none; border-radius: 12px; 
        font-weight: 600; padding: 0.6rem 1.2rem; width: 100%; box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.2), 0 6px 16px rgba(16, 185, 129, 0.4);
    }
    .stButton>button:hover { background: linear-gradient(135deg, #059669 0%, #047857 100%); transform: translateY(-1px); }
</style>
""", unsafe_allow_html=True)


def get_required_secret(name: str) -> str:
    val = st.secrets.get(name, os.getenv(name))
    if not val:
        st.error(f"❌ Critical Configuration Error: Required secret '{name}' is missing in Streamlit secrets.")
        st.stop()
    return str(val)


BACKEND_URL = get_required_secret("BACKEND_URL")
BACKEND_SECRET_KEY = get_required_secret("BACKEND_SECRET_KEY")
INVITE_CODE = get_required_secret("INVITE_CODE")
ADMIN_EMAILS = [e.strip().lower() for e in get_required_secret("ADMIN_EMAILS").split(",") if e.strip()]
DB_FILE = st.secrets.get("DB_PATH", os.getenv("DB_PATH", "executive_intelligence.duckdb"))


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
        return pd.read_excel(io.BytesIO(data), sheet_name=sheet if sheet is not None else 0, engine="openpyxl")
    last_err = None
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(data), encoding=enc, sep=None, engine="python")
        except Exception as e:
            last_err = e
    raise last_err


def format_compact(v, cur):
    if v is None or pd.isna(v):
        return "n/a"
    if abs(v) >= 1_000_000:
        return f"{cur}{v/1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"{cur}{v/1_000:.1f}K"
    return f"{cur}{v:,.2f}"


def pct(v):
    return "n/a" if v is None or pd.isna(v) else f"{v:.1f}%"


def idx(options, value):
    return options.index(value) if value in options else 0


# ----------------------------------------------------------------- AUTH STATE MACHINE
if not st.session_state.get("user"):
    if "nav_state" not in st.session_state:
        st.session_state["nav_state"] = "portal"

    if st.session_state["nav_state"] == "portal":
        _, col, _ = st.columns([1, 2.2, 1])
        with col:
            # --- ANIMATED BIRD LANDING ---
            show_finch_intro(mode="banner", height=200, bg="#0b0f19")
            
            # --- CUSTOM SHIMMERING TYPOGRAPHY HEADER ---
            st.markdown("""
            <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@700&family=Inter:wght@400;500&display=swap" rel="stylesheet">
            <style>
            .finch-wrap{text-align:center;padding:0.2rem 0 1.5rem;}
            .finch-title{
              display:inline-block;
              font-family:'Space Grotesk',sans-serif;
              font-weight:700;
              font-size:4rem;
              line-height:1;
              letter-spacing:.32em;
              margin-right:-.32em;
              background:linear-gradient(110deg,#0f9d8f 0%,#5eead4 28%,#f4b860 50%,#5eead4 72%,#0f9d8f 100%);
              background-size:250% auto;
              -webkit-background-clip:text;
              background-clip:text;
              -webkit-text-fill-color:transparent;
              animation:finch-shine 7s linear infinite;
              filter:drop-shadow(0 0 20px rgba(20,184,166,.40));
            }
            @keyframes finch-shine{to{background-position:250% center;}}
            .finch-badge{
              display:inline-block;
              vertical-align:top;
              margin-left:1.2rem;
              padding:.2rem .6rem;
              font-family:'Inter',sans-serif;
              font-size:.75rem;
              font-weight:700;
              color:#fff;
              background:linear-gradient(135deg,#10b981,#0f9d8f);
              border-radius:999px;
              box-shadow:0 0 14px rgba(16,185,129,.5);
            }
            .finch-line{
              width:70px;height:3px;margin:.9rem auto .7rem;
              background:linear-gradient(90deg,transparent,#f4b860,transparent);
              border-radius:2px;
            }
            .finch-sub{
              font-family:'Inter',sans-serif;
              font-size:.8rem;
              font-weight:500;
              letter-spacing:.3em;
              text-transform:uppercase;
              color:#7fa6c9;
            }
            </style>
            <div class="finch-wrap">
            <span class="finch-title">FINCH</span><span class="finch-badge">V2.11</span>
            <div class="finch-line"></div>
            <div class="finch-sub">Secure Business Intelligence Workspace</div>
            </div>
            """, unsafe_allow_html=True)
            
            tab_login, tab_signup = st.tabs(["Log in", "Create account"])

            with tab_login:
                with st.form("login_form"):
                    u = st.text_input("Username or Email")
                    p = st.text_input("Password", type="password")
                    if st.form_submit_button("🚀 Log in"):
                        verified_user = verify_user(u, p)
                        if verified_user:
                            st.session_state["user"] = verified_user
                            user_email = get_user_email(verified_user)
                            log_tenant_activity(user_email, "User Login")
                            st.rerun()
                        else:
                            st.error("Invalid username/email or password.")

            with tab_signup:
                with st.form("signup_form"):
                    nu = st.text_input("Choose username (3-32 letters, numbers, . _ -)")
                    ne = st.text_input("Business Email address", placeholder="owner@company.com")
                    np1 = st.text_input("Password (min 8 characters)", type="password")
                    np2 = st.text_input("Confirm password", type="password")
                    inv = st.text_input("Invite code", type="password")
                    if st.form_submit_button("Create account"):
                        if not hmac.compare_digest(inv.encode(), INVITE_CODE.encode()):
                            st.error("Invalid invite code.")
                        elif not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", nu.strip()):
                            st.error("Username must be 3-32 characters: letters, numbers, . _ -")
                        elif "@" not in ne or "." not in ne:
                            st.error("Please provide a valid business email address.")
                        elif len(np1) < 8 or np1 != np2:
                            st.error("Passwords must match and be at least 8 characters.")
                        elif create_user(nu, ne, np1):
                            st.session_state["user"] = nu.strip().lower()
                            log_tenant_activity(ne.strip().lower(), "Account Created")
                            st.rerun()
                        else:
                            st.error("That username or email is already taken.")
        st.stop()

USER = st.session_state["user"]
USER_EMAIL = get_user_email(USER)

# ------------------------------------------------------------- WORKSPACE UPLOAD
if not check_backend_status(BACKEND_URL, BACKEND_SECRET_KEY):
    st.warning("⚠️ Backend API is waking up or offline. AI advisory may not work yet.")

uploaded = st.file_uploader("📁 Upload your sales or business records (.csv or .xlsx, max 10MB)", type=["csv", "xlsx"])

if uploaded is None:
    st.info("👋 Please upload your sales or business records above to begin audit.")
    st.markdown("---")
    st.subheader("📂 Your Past Saved Audits & History")
    history_records = load_user_history_db(USER_EMAIL)
    if history_records:
        st.dataframe(pd.DataFrame(history_records)[["file_name", "total_revenue", "net_profit", "profit_margin", "timestamp"]], use_container_width=True)
    else:
        st.info("No past audit records found for this account yet.")
    st.stop()

uploaded_data = uploaded.getvalue()
uploaded_name = uploaded.name

if len(uploaded_data) / (1024 * 1024) > 10:
    st.error("❌ File size exceeds the strict 10MB limit.")
    st.stop()

sheet = None
if uploaded_name.lower().endswith(".xlsx"):
    try:
        sheets = pd.ExcelFile(io.BytesIO(uploaded_data), engine="openpyxl").sheet_names
    except Exception as e:
        st.error(f"Could not open the Excel file: {e}")
        st.stop()
    sheet = st.selectbox("Sheet", sheets) if len(sheets) > 1 else sheets[0]

data_key = f"{hashlib.md5(uploaded_data).hexdigest()}:{sheet}"
if st.session_state.get("data_key") != data_key:
    try:
        raw = read_upload(uploaded_name, uploaded_data, sheet)
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
    log_tenant_activity(USER_EMAIL, f"Uploaded File: {uploaded_name}", increment_upload=True)

df = st.session_state["active_df"]
notes = st.session_state["prep_notes"]
sug = st.session_state["suggested"]

st.sidebar.markdown("### 🐦 FINCH Workspace")
currency = st.sidebar.selectbox("Currency", ["₦", "$", "€", "£"])

nums = valid_numeric_columns(df)
if not nums:
    st.error("No numeric columns were found. Please check that your file has a revenue or amount column.")
    st.stop()
cats = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c])]
cats = [c for c in cats if not pd.api.types.is_datetime64_any_dtype(df[c])]

with st.sidebar.expander("🔍 How we read your file (Column Mapping)"):
    sel_rev = st.selectbox("Revenue Column", nums, index=idx(nums, sug["revenue"]))
    cost_opts = ["None"] + [c for c in nums if c != sel_rev]
    sel_cost = st.selectbox("Cost Column", cost_opts, index=idx(cost_opts, sug["cost"]))
    cat_opts = ["None"] + cats
    sel_cat = st.selectbox("Category / Group Column", cat_opts, index=idx(cat_opts, sug["category"]))
    date_opts = ["None"] + list(df.columns)
    sel_date = st.selectbox("Date / Time Column (Optional)", date_opts, index=idx(date_opts, sug["date"]))

facts = get_facts(df, sel_rev, sel_cost, sel_cat, sel_date, tuple(notes))
totals, meta, trend = facts["totals"], facts["metadata"], facts["trend"]
cost_known = totals["cost_known"]

st.sidebar.markdown("---")
st.sidebar.markdown(f"### 👤 Signed in: `{USER}`<br><small>{USER_EMAIL}</small>", unsafe_allow_html=True)
if st.sidebar.button("🔒 Log out"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# --- FAIL-CLOSED ADMIN PANEL CHECK ---
is_admin = (ADMIN_EMAILS and USER_EMAIL in ADMIN_EMAILS)
if is_admin:
    st.sidebar.markdown("---")
    with st.sidebar.expander("🛠️ Founder Admin Panel"):
        st.success("🔓 Authorized Admin View")
        if os.path.exists(DB_FILE):
            conn = duckdb.connect(DB_FILE)
            st.markdown("#### 👥 Registered Tenants")
            try:
                tenants_df = conn.execute("SELECT email, created_at, last_active, total_uploads FROM tenants ORDER BY last_active DESC").fetchdf()
                st.dataframe(tenants_df, use_container_width=True)
            except Exception:
                st.info("No tenant data recorded yet.")
            conn.close()

# --- STREAMLINED NAVIGATION ---
tabs = st.tabs(["📊 Summary", "📈 Trends", "🔍 Data Check", "🎛️ What-If", "📁 Reports & History"])

with tabs[0]:
    st.subheader("FINCH Executive Summary")
    
    profit_val = totals["net_profit"] if cost_known and totals["net_profit"] is not None else 0.0
    margin_val = totals["profit_margin"]
    if cost_known:
        if profit_val > 0:
            verdict_msg = f"You generated **{format_compact(totals['total_revenue'], currency)}** in revenue with **{format_compact(profit_val, currency)}** net profit ({pct(margin_val)} margin). Financial health is stable and profitable."
        elif profit_val < 0:
            verdict_msg = f"Warning: You generated **{format_compact(totals['total_revenue'], currency)}** in revenue but incurred a net loss of **{format_compact(abs(profit_val), currency)}**. Immediate cost rationalization is advised."
        else:
            verdict_msg = f"You generated **{format_compact(totals['total_revenue'], currency)}** in revenue and broke even. Review cost structures to improve margins."
    else:
        verdict_msg = f"You generated **{format_compact(totals['total_revenue'], currency)}** in revenue. Select a cost column to evaluate net profitability."
    
    st.markdown(f"✨ **Verdict:** {verdict_msg}")

    if notes or facts["warnings"]:
        with st.expander("ℹ️ What we did to your file (Data Prep & Warnings)"):
            for n in notes:
                st.markdown(f"- {n}")
            for w in facts["warnings"]:
                st.markdown(f"⚠️ {w}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Net Profit", format_compact(totals["net_profit"], currency) if cost_known else "n/a")
    c2.metric("Total Revenue", format_compact(totals["total_revenue"], currency))
    c3.metric("Total Costs", format_compact(totals["total_costs"], currency) if cost_known else "Not provided")
    c4.metric("Profit Margin", pct(totals["profit_margin"]))
    st.markdown("---")

    g1, g2 = st.columns(2)
    with g1:
        if cost_known:
            fig = px.bar(x=["Revenue", "Costs", "Net Profit"],
                         y=[totals["total_revenue"], totals["total_costs"], totals["net_profit"]],
                         title="Financial Overview", labels={"x": "Metric", "y": f"Amount ({currency})"},
                         color=["Revenue", "Costs", "Net Profit"],
                         color_discrete_map={"Revenue": "#10b981", "Costs": "#64748b", "Net Profit": "#059669"},
                         template="plotly_dark")
        else:
            fig = px.histogram(df, x=sel_rev, title=f"Distribution of {sel_rev}", template="plotly_dark")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        rbc = facts["revenue_by_category"]
        if rbc:
            bar_df = pd.DataFrame(list(rbc.items())[:8], columns=["Category", "Revenue"]).sort_values("Revenue", ascending=True)
            fig_bar = px.bar(bar_df, x="Revenue", y="Category", orientation="h",
                             title=f"Top Categories by Revenue",
                             template="plotly_dark", color_discrete_sequence=["#10b981"])
            fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Select a category column to see category distribution.")

with tabs[1]:
    st.subheader("Performance Trends & Leaderboards")
    if len(trend["points"]) >= 1:
        tdf = pd.DataFrame(trend["points"])
        fig_trend = px.line(tdf, x="period", y="revenue", markers=True, template="plotly_dark",
                            title=f"Revenue by {trend['granularity']} (chronological)")
        fig_trend.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_trend, use_container_width=True)
        if trend["change_pct"] is not None:
            st.metric(f"Latest {trend['granularity']} vs previous", f"{trend['change_pct']:+.1f}%")
    elif sel_date == "None":
        st.info("Select a date column in the sidebar to see trends.")
    else:
        st.info("Not enough dated data to draw a chronological trend.")

    if facts["revenue_by_category"]:
        gdf = pd.DataFrame(list(facts["revenue_by_category"].items()), columns=["Category", "Revenue"])
        st.markdown("#### Category Leaderboard")
        st.dataframe(gdf, use_container_width=True)

with tabs[2]:
    st.subheader("Data Check: Is Your Data Reliable?")
    d1, d2, d3 = st.columns(3)
    d1.metric("Data Quality Score", f"{meta['data_health_index']}%")
    d2.metric("Missing Cells", f"{meta['missing_cells']:,}")
    d3.metric("Duplicate Rows", f"{meta['duplicate_rows']:,}")
    if facts["anomalies"]:
        st.markdown(f"##### Unusually large sales ({meta['anomaly_count']} total, top 5 shown)")
        st.dataframe(pd.DataFrame(facts["anomalies"]).head(5), use_container_width=True)
    else:
        st.success("No significant outliers detected.")
    st.markdown("### Dataset Preview")
    st.dataframe(df.head(10), use_container_width=True)

with tabs[3]:
    st.subheader("What-If Scenario & Heatmap Sensitivity Modelling")
    st.caption("Volume changes scale variable costs; fixed costs stay flat; price changes affect revenue only.")

    sim_totals = dict(totals)
    cost_assumed = False
    if not cost_known:
        st.warning("⚠️ **Cost column not selected:** Profit and margin calculations below are modelled on assumed cost ratios.")
        ratio = st.slider("Assumed total costs as % of revenue", 0, 100, 70)
        sim_totals["total_costs"] = totals["total_revenue"] * ratio / 100
        cost_assumed = True

    w1, w2 = st.columns(2)
    with w1:
        scenario_name = st.text_input("Scenario Name", value="Scenario 1")
        price_adj = st.slider("Price Adjustment (%)", -50, 50, 5)
        volume_adj = st.slider("Volume Adjustment (%)", -50, 50, 0)
    with w2:
        fixed_share = st.slider("Share of current costs that are fixed (%)", 0, 100, 30) / 100
        fixed_change = st.number_input("Fixed Cost Adjustment (absolute)", value=0.0, step=1000.0)
        var_pct = st.slider("Variable Cost per-unit Adjustment (%)", -50, 50, 0)

    res = calculate_scenario(sim_totals, price_adj, volume_adj, fixed_change, var_pct, fixed_share)
    res["cost_assumed"] = cost_assumed
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Simulated Revenue", format_compact(res["revenue"], currency),
              f"{((1 + price_adj / 100) * (1 + volume_adj / 100) - 1) * 100:+.1f}%")
    s2.metric("Simulated Costs", format_compact(res["costs"], currency))
    s3.metric("Simulated Net Profit", format_compact(res["net_profit"], currency), f"{res['profit_delta']:+,.2f}")
    s4.metric("Simulated Margin", pct(res["profit_margin"]))

    if st.button("💾 Save Scenario", type="primary"):
        save_scenario_db(USER, scenario_name, res)
        st.success(f"Saved '{scenario_name}'.")

    saved = load_scenarios_db(USER)
    if saved:
        st.markdown("### 📊 Your Saved Scenarios")
        st.dataframe(pd.DataFrame(saved)[["scenario_name", "revenue", "costs", "net_profit", "margin"]],
                     use_container_width=True)
        if st.button("🗑️ Delete all my saved scenarios", help="Clear saved scenarios"):
            delete_scenarios_db(USER)
            st.rerun()

    st.markdown("---")
    st.markdown("### 📈 Profit Sensitivity Heatmap")
    sens_matrix = generate_sensitivity_matrix(sim_totals, fixed_share)
    sens_df = pd.DataFrame(sens_matrix)
    if not sens_df.empty:
        fig_heat = px.imshow(sens_df.set_index(sens_df.columns[0]),
                             color_continuous_midpoint=0, text_auto=",.0f",
                             color_continuous_scale="RdYlGn", template="plotly_dark",
                             labels=dict(color="Profit"))
        fig_heat.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_heat, use_container_width=True)

with tabs[4]:
    st.subheader("Reports, FINCH AI Advisor & History")
    
    col_rep1, col_rep2 = st.columns(2)
    with col_rep1:
        st.markdown("### 🧠 FINCH AI Advisor")
        consent = st.checkbox("I understand aggregated figures are sent to AI. Raw rows are never sent.")
        if st.button("Get AI Brief", type="primary", disabled=not consent):
            with st.spinner("🐦 FINCH is analyzing verified facts and scenarios..."):
                try:
                    res_ai = requests.post(
                        f"{BACKEND_URL}/api/ai-advisory",
                        json={
                            "verified_stats": build_ai_payload(facts),
                            "saved_scenarios": load_scenarios_db(USER),
                            "currency": currency
                        },
                        headers={"X-API-Key": BACKEND_SECRET_KEY, "X-User-Id": USER},
                        timeout=120,
                    )
                    if res_ai.status_code == 200:
                        body = res_ai.json()
                        advice_text = body.get("advisory", "")
                        st.markdown(advice_text)
                        save_audit_history_db(USER_EMAIL, "Independent SME", uploaded_name, totals, advice_text)
                    else:
                        try:
                            err_detail = res_ai.json().get("detail", "The server encountered an error.")
                        except Exception:
                            err_detail = res_ai.text or "The server encountered an error."
                        st.error(f"⚠️ AI Advisory Error: {err_detail}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

    with col_rep2:
        st.markdown("### 📈 Presentation Deck")
        st.caption("Generate a professional 8-slide FINCH executive PowerPoint presentation.")
        if st.button("Create PowerPoint Report (.pptx)", type="primary"):
            with st.spinner("📊 Building presentation..."):
                try:
                    deck_bytes = create_executive_deck(
                        facts, currency=currency, filename=uploaded_name, scenarios=load_scenarios_db(USER))
                    st.session_state["deck_bytes"] = deck_bytes
                    st.success("✅ Deck generated.")
                    save_audit_history_db(USER_EMAIL, "Independent SME", uploaded_name, totals, "Generated PowerPoint Deck (.pptx)")
                except Exception as e:
                    st.error(f"Error generating presentation: {e}")
        if "deck_bytes" in st.session_state:
            st.download_button("📥 Download Business Report (.pptx)", data=st.session_state["deck_bytes"],
                               file_name="FINCH_Business_Report.pptx",
                               mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                               type="primary")

    st.markdown("---")
    st.subheader("📂 Dedicated User History & Audit Trail")
    history_records = load_user_history_db(USER_EMAIL)
    if history_records:
        st.dataframe(pd.DataFrame(history_records)[["file_name", "total_revenue", "net_profit", "profit_margin", "timestamp"]], use_container_width=True)
        with st.expander("🔍 View Saved AI Briefs"):
            for rec in history_records:
                if rec.get("ai_brief"):
                    st.markdown(f"**File:** `{rec['file_name']}` | **Date:** {rec['timestamp']}")
                    st.markdown(rec["ai_brief"])
                    st.markdown("---")
    else:
        st.info("No audit history saved yet.")

    st.markdown("---")
    st.subheader("Feedback & Support")
    with st.form("feedback_form"):
        cat = st.selectbox("Category", ["Bug Report", "Feature Request", "General Feedback"])
        msg = st.text_area("Your Message")
        if st.form_submit_button("Submit Feedback"):
            if msg.strip():
                save_feedback_db(USER_EMAIL, cat, msg)
                st.success("Thank you! Feedback received.")
            else:
                st.warning("Please enter a message.")