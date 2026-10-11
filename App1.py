import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import io
import time
from pptx import Presentation
from pptx.util import Inches, Pt

# PAGE CONFIGURATION
st.set_page_config(
    page_title="Executive Data Intelligence Suite",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# GMAIL-STYLE SPLASH & EXECUTIVE CSS
st.markdown("""
<style>
    .stApp {
        background-color: #0f172a;
        color: #e2e8f0;
    }
    section[data-testid="stSidebar"] {
        background-color: #090d16;
        border-right: 1px solid #1e293b;
    }
    .saas-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        padding: 32px;
        border-radius: 12px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
        margin-bottom: 20px;
    }
    h1, h2, h3 {
        color: #f8fafc;
        letter-spacing: -0.02em;
    }
    .stButton>button {
        background-color: #2563eb;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.6rem 1.2rem;
        transition: background-color 0.2s ease;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #1d4ed8;
    }
    /* Gmail-style pulsing loader animation */
    @keyframes gmailPulse {
        0% { transform: scale(0.95); opacity: 0.8; }
        50% { transform: scale(1.05); opacity: 1; }
        100% { transform: scale(0.95); opacity: 0.8; }
    }
    .gmail-loader {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 60vh;
        text-align: center;
    }
    .gmail-logo {
        font-size: 4rem;
        animation: gmailPulse 1.5s infinite ease-in-out;
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #090d16;
        padding: 6px;
        border-radius: 10px;
        border: 1px solid #1e293b;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e293b;
        border-radius: 6px;
        color: #94a3b8;
        padding: 8px 16px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# BACKEND API CONFIGURATION (Update with your live Render URL when deployed)
BACKEND_URL = "https://ai-data-analyzer-1-n0an.onrender.com"
BACKEND_SECRET_KEY = "dev-secret-token"

@st.cache_data(ttl=60)
def check_backend_status():
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=3)
        return response.status_code == 200
    except Exception:
        return False

def api_send_otp(email: str):
    res = requests.post(f"{BACKEND_URL}/api/auth/send-otp", json={"email": email}, timeout=10)
    if res.status_code == 200:
        return True
    raise Exception(res.json().get("detail", "Failed to send OTP"))

def api_verify_otp(email: str, code: str):
    res = requests.post(f"{BACKEND_URL}/api/auth/verify-otp", json={"email": email, "code": code}, timeout=10)
    if res.status_code == 200:
        return True
    raise Exception(res.json().get("detail", "Invalid verification code"))

def analyze_dataset_via_backend_api(filename: str, file_bytes: bytes, mime_type: str):
    files = {"file": (filename, file_bytes, mime_type)}
    headers = {"X-API-Key": BACKEND_SECRET_KEY}
    response = requests.post(f"{BACKEND_URL}/api/analyze", files=files, headers=headers, timeout=15)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Backend error ({response.status_code}): {response.text}")

def fetch_ai_advisory_from_backend(verified_stats: str):
    headers = {"X-API-Key": BACKEND_SECRET_KEY}
    payload = {"verified_stats": verified_stats}
    response = requests.post(f"{BACKEND_URL}/api/ai-advisory", json=payload, headers=headers, timeout=45)
    if response.status_code == 200:
        return response.json().get("advisory", "")
    else:
        raise Exception(f"Backend AI error ({response.status_code}): {response.text}")

class BusinessDataEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        self.cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
        self.date_cols = [c for c in df.columns if any(k in c.lower() for k in ['date', 'time', 'year', 'month', 'period', 'created'])]

    def audit_data_quality(self, active_df: pd.DataFrame):
        total_cells = active_df.size
        if total_cells == 0:
            return 0.0, 0, 0, []
        missing_cells = active_df.isna().sum().sum()
        health_score = max(0.0, min(100.0, ((total_cells - missing_cells) / total_cells) * 100))
        issues = []
        if missing_cells > 0:
            issues.append(f"Found {missing_cells:,} missing/null data cells in the active dataset view.")
        duplicates = active_df.duplicated().sum()
        if duplicates > 0:
            issues.append(f"Detected {duplicates:,} fully duplicated row records.")
        return round(health_score, 1), missing_cells, duplicates, issues

    def get_smart_time_series(self, active_df: pd.DataFrame, metric_col: str):
        date_candidates = [col for col in active_df.columns if any(k in col.lower() for k in ['date', 'time', 'year', 'month', 'period', 'created'])]
        if not date_candidates and self.date_cols:
            date_candidates = self.date_cols
        if date_candidates and metric_col in active_df.columns:
            d_col = date_candidates[0]
            try:
                temp_df = active_df.copy()
                temp_df[d_col] = pd.to_datetime(temp_df[d_col], errors='coerce')
                temp_df = temp_df.dropna(subset=[d_col, metric_col])
                temp_df[metric_col] = pd.to_numeric(temp_df[metric_col], errors='coerce')
                trend = temp_df.groupby(d_col)[metric_col].sum().reset_index().sort_values(d_col)
                if len(trend) > 1:
                    return d_col, trend
            except Exception:
                pass
        return None, None


# --- STATE INITIALIZATION ---
if "app_state" not in st.session_state:
    st.session_state["app_state"] = "splash"  # splash -> welcome -> auth_input -> otp_verify -> main
    st.session_state["auth_email"] = ""

# --- 1. GMAIL-STYLE SPLASH SCREEN ---
if st.session_state["app_state"] == "splash":
    st.markdown("""
        <div class="gmail-loader">
            <div class="gmail-logo">📊</div>
            <h2 style="color: #f8fafc; font-weight: 500;">Executive Data Intelligence Suite</h2>
            <p style="color: #94a3b8; font-size: 0.95rem;">Loading secure workspace...</p>
        </div>
    """, unsafe_allow_html=True)
    time.sleep(1.5)
    st.session_state["app_state"] = "welcome"
    st.rerun()

# --- 2. WELCOME LANDING PAGE ---
if st.session_state["app_state"] == "welcome":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
            <div style='text-align: center; padding: 10px;'>
                <h1 style='font-size: 2.5rem; color: #f8fafc;'>Instant Financial Clarity for Small Businesses & Individuals</h1>
                <p style='color: #94a3b8; font-size: 1.1rem; margin-top: 10px; margin-bottom: 30px;'>
                    Transform raw CSV and Excel data into executive dashboards, anomaly alerts, and AI advisory reports in seconds.
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="saas-card">', unsafe_allow_html=True)
        c_a, c_b = st.columns(2)
        with c_a:
            if st.button("Sign In"):
                st.session_state["auth_mode"] = "signin"
                st.session_state["app_state"] = "auth_input"
                st.rerun()
        with c_b:
            if st.button("Create Account", type="primary"):
                st.session_state["auth_mode"] = "signup"
                st.session_state["app_state"] = "auth_input"
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 3. EMAIL INPUT & OTP TRIGGER ---
if st.session_state["app_state"] == "auth_input":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""
            <div style='text-align: center; margin-bottom: 20px;'>
                <h2>{'Welcome Back' if st.session_state.get('auth_mode') == 'signin' else 'Create Your Account'}</h2>
                <p style='color: #94a3b8;'>Enter your email (Gmail, Yahoo, Outlook, etc.) to receive your secure verification code.</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="saas-card">', unsafe_allow_html=True)
            with st.form("email_form"):
                user_email = st.text_input("Email Address", placeholder="you@gmail.com")
                submitted = st.form_submit_button("Send Verification Code", type="primary")
                if submitted:
                    if user_email and "@" in user_email:
                        try:
                            api_send_otp(user_email)
                            st.session_state["auth_email"] = user_email
                            st.session_state["app_state"] = "otp_verify"
                            st.success("Verification code sent! Check your inbox.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.error("Please enter a valid email address.")
            
            if st.button("← Back to Welcome Page"):
                st.session_state["app_state"] = "welcome"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 4. OTP VERIFICATION SCREEN ---
if st.session_state["app_state"] == "otp_verify":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""
            <div style='text-align: center; margin-bottom: 20px;'>
                <h2>Verify Your Email</h2>
                <p style='color: #94a3b8;'>We've sent a 6-digit code to <b>{st.session_state['auth_email']}</b>.<br><small>(Check server terminal if running locally)</small></p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="saas-card">', unsafe_allow_html=True)
            with st.form("otp_form"):
                otp_input = st.text_input("Enter 6-Digit Code", placeholder="123456", max_chars=6)
                verify_submitted = st.form_submit_button("Verify & Launch Suite", type="primary")
                if verify_submitted:
                    try:
                        api_verify_otp(st.session_state["auth_email"], otp_input)
                        st.session_state["authenticated"] = True
                        st.session_state["app_state"] = "main"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Verification failed: {e}")
            
            if st.button("← Resend Code / Change Email"):
                st.session_state["app_state"] = "auth_input"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


# --- 5. MAIN APPLICATION (Post-Authentication) ---
is_backend_online = check_backend_status()

st.markdown(f"""
    <div style='padding: 24px; background-color: #1e293b; border-radius: 12px; border: 1px solid #334155; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;'>
        <div>
            <h1 style='margin:0; font-size: 1.8rem; color: #f8fafc;'>Executive Data Intelligence Suite</h1>
            <p style='margin: 6px 0 0 0; color: #94a3b8; font-size: 0.95rem;'>Account: <b>{st.session_state.get('auth_email')}</b> | Mode: <b>Verified Access</b></p>
        </div>
    </div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader("Upload Business Dataset (.csv or .xlsx)", type=["csv", "xlsx"])

if uploaded is not None:
    if "current_filename" not in st.session_state or st.session_state["current_filename"] != uploaded.name:
        file_bytes = uploaded.getvalue()
        try:
            if uploaded.name.lower().endswith('.csv'):
                try:
                    orig_df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
                except UnicodeDecodeError:
                    orig_df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")
            else:
                orig_df = pd.read_excel(io.BytesIO(file_bytes))
            
            st.session_state["current_filename"] = uploaded.name
            st.session_state["raw_file_bytes"] = file_bytes
            st.session_state["active_df"] = orig_df.copy()
        except Exception as e:
            st.error(f"Error loading file: {e}")
            st.stop()

    df = st.session_state["active_df"]
    engine = BusinessDataEngine(df)

    # SIDEBAR CONTROLS
    st.sidebar.markdown("### 🔍 Dataset Filters")
    filtered_df = df.copy()
    if engine.cat_cols:
        filter_cat_col = st.sidebar.selectbox("Filter Category", ["None"] + engine.cat_cols)
        if filter_cat_col != "None":
            unique_vals = df[filter_cat_col].dropna().unique().tolist()
            selected_vals = st.sidebar.multiselect(f"Select {filter_cat_col}", unique_vals, default=unique_vals)
            if selected_vals:
                filtered_df = filtered_df[filtered_df[filter_cat_col].isin(selected_vals)]

    st.sidebar.caption(f"Active Records: {len(filtered_df):,} / {len(df):,}")
    
    if st.sidebar.button("Reset Dataset View"):
        file_bytes = st.session_state["raw_file_bytes"]
        if st.session_state["current_filename"].lower().endswith('.csv'):
            st.session_state["active_df"] = pd.read_csv(io.BytesIO(file_bytes))
        else:
            st.session_state["active_df"] = pd.read_excel(io.BytesIO(file_bytes))
        st.rerun()

    if st.sidebar.button("Sign Out"):
        st.session_state["app_state"] = "welcome"
        st.session_state["authenticated"] = False
        st.rerun()

    tabs = [
        "AI Advisory",
        "Sales & Profit",
        "Leaderboard",
        "Data Health",
        "Anomaly Radar",
        "Boardroom PPTX",
        "Backend Diagnostics"
    ]
    
    tab_objs = st.tabs(tabs)

    # TAB 1: AI ADVISER
    with tab_objs[0]:
        st.subheader("AI Business Strategic Adviser")
        st.caption("Generate executive analysis powered by secure server-side intelligence.")
        
        if not is_backend_online:
            st.warning("Backend API is waking up or offline. Please check your Render service status.")
        else:
            if st.button("Generate Strategic Advisory", type="primary"):
                with st.spinner("Analyzing verified metrics and compiling advisory..."):
                    try:
                        total_rows = len(filtered_df)
                        health_score, _, _, _ = engine.audit_data_quality(filtered_df)
                        num_summary = filtered_df[engine.num_cols].describe().to_string() if engine.num_cols else "No numeric data"
                        
                        verified_stats = f"""
                        Dataset Statistics:
                        - Filename: {st.session_state['current_filename']}
                        - Filtered Row Count: {total_rows:,}
                        - Data Health Index: {health_score}%
                        - Numeric Summary:
                        {num_summary}
                        """
                        
                        advisory_result = fetch_ai_advisory_from_backend(verified_stats)
                        st.session_state["ai_output"] = advisory_result
                        st.success("Advisory generated successfully.")
                    except Exception as e:
                        st.error(f"Failed to generate advisory: {e}")

        if "ai_output" in st.session_state:
            st.markdown("---")
            st.markdown(st.session_state["ai_output"])

    # TAB 2: SALES & PROFIT DASHBOARD
    with tab_objs[1]:
        st.subheader("Sales & Profitability Command Center")
        
        rev_candidates = [c for c in engine.num_cols if any(k in c.lower() for k in ['revenue', 'sales', 'amount', 'total', 'price'])]
        cost_candidates = [c for c in engine.num_cols if any(k in c.lower() for k in ['cost', 'expense', 'spend', 'budget'])]

        sel_rev = st.selectbox("Select Revenue Metric", engine.num_cols, index=engine.num_cols.index(rev_candidates[0]) if rev_candidates else 0)
        sel_cost = st.selectbox("Select Cost Metric (Optional)", ["None"] + engine.num_cols)

        total_revenue = filtered_df[sel_rev].sum()
        total_costs = filtered_df[sel_cost].sum() if sel_cost != "None" else 0.0
        net_profit = total_revenue - total_costs
        profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Total Revenue", f"${total_revenue:,.2f}")
        p2.metric("Total Costs", f"${total_costs:,.2f}")
        p3.metric("Net Profit", f"${net_profit:,.2f}")
        p4.metric("Profit Margin", f"{profit_margin:.1f}%")

        st.markdown("---")
        t_col, trend_data = engine.get_smart_time_series(filtered_df, sel_rev)
        if t_col is not None and trend_data is not None:
            fig_trend = px.line(trend_data, x=t_col, y=sel_rev, title=f"Trend of {sel_rev} over {t_col}", template="plotly_dark", color_discrete_sequence=["#2563eb"])
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            fig_hist = px.histogram(filtered_df, x=sel_rev, title=f"Distribution of {sel_rev}", template="plotly_dark", color_discrete_sequence=["#2563eb"])
            st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown("---")
        st.dataframe(filtered_df.head(15), use_container_width=True)

    # TAB 3: PERFORMANCE LEADERBOARD
    with tab_objs[2]:
        st.subheader("Business Performance Leaderboard")
        if engine.cat_cols and engine.num_cols:
            perf_cat = st.selectbox("Grouping Dimension", engine.cat_cols)
            perf_num = st.selectbox("Performance Metric", engine.num_cols)

            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown("#### Top Performers")
                st.dataframe(filtered_df.groupby(perf_cat)[perf_num].sum().nlargest(5).reset_index(), use_container_width=True)
            with col_r:
                st.markdown("#### Underperformers")
                st.dataframe(filtered_df.groupby(perf_cat)[perf_num].sum().nsmallest(5).reset_index(), use_container_width=True)
        else:
            st.info("Dataset requires categorical and numerical columns.")

    # TAB 4: DATA QUALITY & HEALTH AUDIT
    with tab_objs[3]:
        st.subheader("Data Quality & Integrity Audit")
        health_score, missing_cells, duplicates, issues = engine.audit_data_quality(filtered_df)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Active Rows", f"{len(filtered_df):,}")
        c2.metric("Columns", f"{len(filtered_df.columns):,}")
        c3.metric("Health Index", f"{health_score}%")
        c4.metric("Flagged Issues", len(issues))
        
        st.markdown("---")
        if issues:
            for issue in issues:
                st.warning(issue)
        else:
            st.success("Dataset integrity check passed with zero anomalies.")

        st.markdown("---")
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Filtered Dataset (.csv)", data=csv_data, file_name="filtered_dataset.csv", mime="text/csv")

    # TAB 5: ANOMALY RADAR
    with tab_objs[4]:
        st.subheader("Anomaly & Outlier Detection")
        if engine.num_cols:
            anomaly_metric = st.selectbox("Select Audit Metric", engine.num_cols)
            series = filtered_df[anomaly_metric].dropna()
            
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            anomalies = filtered_df[(filtered_df[anomaly_metric] < lower_bound) | (filtered_df[anomaly_metric] > upper_bound)]
            st.write(f"Flagged **{len(anomalies)} outlier records** in `{anomaly_metric}` based on robust IQR analysis.")
            st.dataframe(anomalies.head(15), use_container_width=True)
        else:
            st.info("No numeric columns available.")

    # TAB 6: BOARDROOM PPTX EXPORT
    with tab_objs[5]:
        st.subheader("Boardroom Presentation Export")
        st.caption("Generate a professional 6-slide executive presentation matching verified dataset metrics.")

        if st.button("Generate PowerPoint Presentation (.pptx)", type="primary"):
            try:
                prs = Presentation()
                prs.slide_width = Inches(13.333)
                prs.slide_height = Inches(7.5)
                
                health_score, missing_cells, duplicates, issues = engine.audit_data_quality(filtered_df)
                
                rev_cands = [c for c in engine.num_cols if any(k in c.lower() for k in ['revenue', 'sales', 'amount', 'total', 'price'])]
                cost_cands = [c for c in engine.num_cols if any(k in c.lower() for k in ['cost', 'expense', 'spend', 'budget'])]
                
                s_rev = sel_rev if 'sel_rev' in locals() and sel_rev in engine.num_cols else (rev_cands[0] if rev_cands else engine.num_cols[0])
                s_cost = sel_cost if 'sel_cost' in locals() and sel_cost != "None" else (cost_cands[0] if cost_cands else None)

                t_rev = filtered_df[s_rev].sum() if s_rev else 0.0
                t_cost = filtered_df[s_cost].sum() if s_cost else 0.0
                n_profit = t_rev - t_cost
                p_margin = (n_profit / t_rev * 100) if t_rev > 0 else 0.0

                # Slide 1: Title
                slide1 = prs.slides.add_slide(prs.slide_layouts[0])
                slide1.shapes.title.text = "Executive Financial Intelligence Report"
                slide1.placeholders[1].text = f"Source: {st.session_state['current_filename']}\nPrepared for: {st.session_state.get('auth_email')}"

                # Slide 2: Summary
                slide2 = prs.slides.add_slide(prs.slide_layouts[5])
                slide2.shapes.title.text = "1. Executive Summary & Data Integrity Audit"
                t2 = slide2.shapes.add_table(5, 2, Inches(1.0), Inches(1.8), Inches(11.3), Inches(4.2)).table
                t2.columns[0].width, t2.columns[1].width = Inches(4.5), Inches(6.8)
                summary_metrics = [
                    ("Evaluation Parameter", "Verified System Metric"),
                    ("Total Active Records Analyzed", f"{len(filtered_df):,} rows"),
                    ("Data Quality Health Index", f"{health_score}%"),
                    ("Total Missing Cells Detected", f"{missing_cells:,} cells"),
                    ("Duplicate Row Anomalies", f"{duplicates:,} duplicate records")
                ]
                for r_idx, r_content in enumerate(summary_metrics):
                    for c_idx, text in enumerate(r_content):
                        cell = t2.cell(r_idx, c_idx)
                        cell.text = text
                        for p in cell.text_frame.paragraphs:
                            p.font.size = Pt(13)
                            if r_idx == 0: p.font.bold = True

                # Slide 3: Financials
                slide3 = prs.slides.add_slide(prs.slide_layouts[5])
                slide3.shapes.title.text = "2. Financial & Profitability Overview"
                t3 = slide3.shapes.add_table(5, 2, Inches(1.0), Inches(1.8), Inches(11.3), Inches(4.2)).table
                t3.columns[0].width, t3.columns[1].width = Inches(4.5), Inches(6.8)
                fin_metrics = [
                    ("Financial KPI Domain", "Verified Calculation"),
                    (f"Revenue Metric ({s_rev})", f"${t_rev:,.2f}"),
                    (f"Cost Metric ({s_cost if s_cost else 'None'})", f"${t_cost:,.2f}"),
                    ("Net Business Profit", f"${n_profit:,.2f}"),
                    ("Net Profit Margin %", f"{p_margin:.1f}%")
                ]
                for r_idx, r_content in enumerate(fin_metrics):
                    for c_idx, text in enumerate(r_content):
                        cell = t3.cell(r_idx, c_idx)
                        cell.text = text
                        for p in cell.text_frame.paragraphs:
                            p.font.size = Pt(13)
                            if r_idx == 0: p.font.bold = True

                # Slide 4: Leaderboard
                if engine.cat_cols and engine.num_cols:
                    slide4 = prs.slides.add_slide(prs.slide_layouts[5])
                    slide4.shapes.title.text = "3. Performance Leaderboard"
                    top_items = filtered_df.groupby(engine.cat_cols[0])[engine.num_cols[0]].sum().nlargest(5).reset_index()
                    t4 = slide4.shapes.add_table(len(top_items)+1, 2, Inches(1.5), Inches(1.8), Inches(10.3), Inches(4.0)).table
                    t4.columns[0].width, t4.columns[1].width = Inches(5.0), Inches(5.3)
                    t4.cell(0, 0).text, t4.cell(0, 1).text = f"Category ({engine.cat_cols[0]})", f"Metric ({engine.num_cols[0]})"
                    for idx, row in top_items.iterrows():
                        t4.cell(idx+1, 0).text, t4.cell(idx+1, 1).text = str(row[engine.cat_cols[0]]), f"{row[engine.num_cols[0]]:,.2f}"
                    for r_idx in range(len(top_items)+1):
                        for c_idx in range(2):
                            cell = t4.cell(r_idx, c_idx)
                            for p in cell.text_frame.paragraphs:
                                p.font.size = Pt(13)
                                if r_idx == 0: p.font.bold = True

                # Slide 5: Risk Audit
                slide5 = prs.slides.add_slide(prs.slide_layouts[1])
                slide5.shapes.title.text = "4. Expense & Anomaly Risk Audit"
                slide5.placeholders[1].text_frame.text = (
                    "• Statistical Variance Auditing: Evaluated dataset distribution against robust interquartile thresholds.\n"
                    "• Outlier Detection: Isolated high-magnitude transactions for operational review.\n"
                    "• Risk Mitigation: Ensures irregular expense spikes or unusual figures are verified prior to reporting."
                )

                # Slide 6: Recommendations
                slide6 = prs.slides.add_slide(prs.slide_layouts[1])
                slide6.shapes.title.text = "5. Strategic Recommendations & Next Steps"
                slide6.placeholders[1].text_frame.text = (
                    "1. Scale High-Margin Offerings: Reallocate budget toward top-performing categories.\n"
                    "2. Cost Control & Expense Trimming: Investigate bottom-tier segments and vendor spending spikes.\n"
                    "3. Continuous Monitoring: Establish weekly automated data health reviews."
                )

                pptx_buffer = io.BytesIO()
                prs.save(pptx_buffer)
                pptx_buffer.seek(0)
                
                st.success("Boardroom Presentation Generated Successfully.")
                st.download_button(
                    label="Download Boardroom Presentation (.pptx)",
                    data=pptx_buffer,
                    file_name="Boardroom_Executive_Presentation.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                )
            except Exception as e:
                st.error(f"Failed to generate PowerPoint presentation: {e}")

    # TAB 7: BACKEND DIAGNOSTICS
    with tab_objs[6]:
        st.subheader("Backend Intelligence Pipeline")
        st.caption("Secure communication with the asynchronous FastAPI REST service.")

        if not is_backend_online:
            st.warning("Backend API is currently offline.")
        else:
            if st.button("Execute Server Dataset Audit", type="primary"):
                with st.spinner("Transmitting dataset to FastAPI server..."):
                    try:
                        file_bytes = st.session_state["raw_file_bytes"]
                        mime_type = "text/csv" if st.session_state["current_filename"].lower().endswith(".csv") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        api_result = analyze_dataset_via_backend_api(st.session_state["current_filename"], file_bytes, mime_type)
                        st.session_state["backend_api_result"] = api_result
                        st.success("Server audit complete.")
                    except Exception as err:
                        st.error(f"Backend communication failed: {err}")

        if "backend_api_result" in st.session_state:
            res = st.session_state["backend_api_result"]
            st.markdown("---")
            st.markdown("### Server Response Summary")
            
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("File Name", res.get("filename", "N/A"))
            col_b.metric("Total Records", f"{res.get('records', 0):,}")
            col_c.metric("Data Fields", res.get("fields_count", 0))
            col_d.metric("Health Index", res.get("data_health_index", "0%"))

            with st.expander("View Raw JSON Response"):
                st.json(res)
else:
    st.markdown("""
        <div style='text-align: center; padding: 60px; background-color: #1e293b; border-radius: 12px; border: 1px solid #334155; margin-top: 40px;'>
            <h2 style='color: #f8fafc; margin-bottom: 8px;'>Workspace Ready</h2>
            <p style='color: #94a3b8; font-size: 1.05rem;'>Upload a business dataset above to initialize the executive command center.</p>
        </div>
    """, unsafe_allow_html=True)