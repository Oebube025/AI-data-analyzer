import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import io
import time
import hashlib
from pptx import Presentation
from pptx.util import Inches, Pt

# PAGE CONFIGURATION
st.set_page_config(
    page_title="Executive Intelligence Suite (Pilot Beta)",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# EXECUTIVE CSS WITH BETA BADGING & SLATE-NAVY PALETTE
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
    .beta-badge {
        background-color: #d97706;
        color: #ffffff;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 4px;
        vertical-align: middle;
        margin-left: 8px;
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

# Secure configuration pulling from Streamlit Secrets
BACKEND_URL = st.secrets.get("https://ai-data-analyzer-1-n0an.onrender.com")
BACKEND_SECRET_KEY = st.secrets.get("BACKEND_SECRET_KEY", "")

@st.cache_data(ttl=60)
def check_backend_status(token: str):
    try:
        headers = {"X-API-Key": token}
        response = requests.get(f"{BACKEND_URL}/health", headers=headers, timeout=3)
        return response.status_code == 200
    except Exception:
        return False

def analyze_dataset_via_backend_api(filename: str, file_bytes: bytes, mime_type: str, token: str):
    files = {"file": (filename, file_bytes, mime_type)}
    headers = {"X-API-Key": token}
    response = requests.post(f"{BACKEND_URL}/api/analyze", files=files, headers=headers, timeout=15)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Backend error ({response.status_code}): {response.text}")

def fetch_ai_advisory_from_backend(verified_stats: str, token: str):
    headers = {"X-API-Key": token}
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

    def clean_text_numeric_columns(self):
        """Cleans text-formatted numbers containing currency symbols (₦, $, €), commas, and parentheses for negatives."""
        cleaned_df = self.df.copy()
        for col in cleaned_df.columns:
            if col not in self.num_cols:
                sample_vals = cleaned_df[col].dropna().head(20).astype(str)
                if sample_vals.str.contains(r'[₦$€£,\(\)]', regex=True).any():
                    try:
                        converted = (
                            sample_vals.str.replace(r'[₦$€£,]', '', regex=True)
                            .str.replace(r'\((.*?)\)', r'-\1', regex=True)
                        )
                        pd.to_numeric(converted, errors='raise')
                        # Apply transformation globally to column
                        cleaned_df[col] = (
                            cleaned_df[col].astype(str)
                            .str.replace(r'[₦$€£,]', '', regex=True)
                            .str.replace(r'\((.*?)\)', r'-\1', regex=True)
                        )
                        cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')
                    except Exception:
                        pass
        return cleaned_df

    def remove_totals_rows(self, active_df: pd.DataFrame):
        """Excludes summary or total rows based on row label patterns."""
        if len(active_df) == 0:
            return active_df
        first_col = active_df.columns[0]
        mask = active_df[first_col].astype(str).str.lower().str.contains(
            r'total|sum|average|overall|subtotal', regex=True, na=False
        )
        return active_df[~mask]

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


# --- STATE INITIALIZATION ---
if "app_state" not in st.session_state:
    st.session_state["app_state"] = "splash"
    st.session_state["authenticated"] = False
    st.session_state["ai_call_count"] = 0
    st.session_state["file_hash"] = None

# --- 1. GMAIL-STYLE SPLASH SCREEN ---
if st.session_state["app_state"] == "splash":
    st.markdown("""
        <div class="gmail-loader">
            <div class="gmail-logo">📊</div>
            <h2 style="color: #f8fafc; font-weight: 500;">Executive Data Intelligence Suite <span class="beta-badge">PILOT BETA</span></h2>
            <p style="color: #94a3b8; font-size: 0.95rem;">Loading secure workspace...</p>
        </div>
    """, unsafe_allow_html=True)
    time.sleep(1.2)
    st.session_state["app_state"] = "welcome"
    st.rerun()

# --- 2. WELCOME LANDING PAGE ---
if st.session_state["app_state"] == "welcome":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
            <div style='text-align: center; padding: 10px;'>
                <h1 style='font-size: 2.3rem; color: #f8fafc;'>Instant Financial Clarity for Small Businesses & Individuals</h1>
                <p style='color: #94a3b8; font-size: 1.05rem; margin-top: 10px; margin-bottom: 30px;'>
                    Transform raw CSV and Excel data into executive dashboards, anomaly alerts, and AI advisory reports in seconds.
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="saas-card">', unsafe_allow_html=True)
        if st.button("Join Pilot Beta / Sign Up", type="primary"):
            st.session_state["app_state"] = "signup"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 3. PROFESSIONAL SIGN-UP & TRUTHFUL BETA PRIVACY POLICY ---
if st.session_state["app_state"] == "signup":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
            <div style='text-align: center; margin-bottom: 20px;'>
                <h2>Join the Pilot Beta</h2>
                <p style='color: #94a3b8;'>Enter your details to test the executive analytics suite.</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="saas-card">', unsafe_allow_html=True)
            with st.form("signup_form"):
                full_name = st.text_input("Full Name", placeholder="e.g. Jane Doe")
                email = st.text_input("Email Address (for Beta updates)", placeholder="e.g. jane@gmail.com")
                company = st.text_input("Business / Organization Name", placeholder="e.g. Acme Consulting or Personal")
                job_role = st.selectbox("Job Role", [
                    "Business Owner / Founder", 
                    "Small Business Manager", 
                    "Freelancer / Independent", 
                    "Accountant / Bookkeeper", 
                    "Data Analyst", 
                    "Other"
                ])
                
                st.markdown("---")
                
                with st.expander("📄 Read our Beta Privacy Notice"):
                    st.markdown("""
                    **Beta Privacy Notice & Data Processing Disclosure**
                    
                    *Effective Date: October 2026*
                    
                    1. **Beta Software Nature**: This application is operating as a **Pilot Beta** release. While we enforce strict encryption in transit, software anomalies may occur. We strongly advise testing with sample or anonymized datasets.
                    2. **Third-Party AI Processing**: When you click "Generate Strategic Advisory", summary statistics and column headers are transmitted securely to **Cohere AI** to generate automated business recommendations.
                    3. **Data Storage & Opt-Out**: Uploaded files are processed in server memory for your session and are not permanently stored. By signing up, you consent to receive feedback updates. To opt out or request data removal, contact support at `support@executivesuite.beta`.
                    """)
                
                agree_policy = st.checkbox("I agree to the Beta Privacy Notice and Terms of Service")
                
                submitted = st.form_submit_button("Launch Beta Workspace", type="primary")
                if submitted:
                    if not full_name.strip():
                        st.error("Please enter your full name.")
                    elif not email.strip() or "@" not in email:
                        st.error("Please enter a valid email address.")
                    elif not company.strip():
                        st.error("Please enter your business or organization name.")
                    elif not agree_policy:
                        st.error("You must agree to the Beta Privacy Notice to continue.")
                    else:
                        st.session_state["user_name"] = full_name.strip()
                        st.session_state["user_email"] = email.strip()
                        st.session_state["user_org"] = company.strip()
                        st.session_state["user_role"] = job_role
                        st.session_state["authenticated"] = True
                        st.session_state["app_state"] = "main"
                        st.rerun()
            
            # Frictionless Google Form link for signup email capture
            st.markdown("""
                <div style='text-align: center; margin-top: 15px;'>
                    <a href="https://forms.gle/your-signup-google-form-link" target="_blank" style='color: #94a3b8; font-size: 0.85rem; text-decoration: underline;'>Prefer registering via Google Form? Click here</a>
                </div>
            """, unsafe_allow_html=True)

            if st.button("← Back to Welcome Page"):
                st.session_state["app_state"] = "welcome"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


# --- 4. MAIN APPLICATION (Post-Signup) ---
is_backend_online = check_backend_status(BACKEND_SECRET_KEY)

user_name = st.session_state.get('user_name', 'Tester')
user_org = st.session_state.get('user_org', 'Personal Workspace')
user_role = st.session_state.get('user_role', 'User')

st.markdown(f"""
    <div style='padding: 24px; background-color: #1e293b; border-radius: 12px; border: 1px solid #334155; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;'>
        <div>
            <h1 style='margin:0; font-size: 1.8rem; color: #f8fafc;'>Executive Data Intelligence Suite <span class="beta-badge">PILOT BETA</span></h1>
            <p style='margin: 6px 0 0 0; color: #94a3b8; font-size: 0.95rem;'>Tester: <b>{user_name}</b> ({user_role}) | Workspace: <b>{user_org}</b></p>
        </div>
    </div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader("Upload Business Dataset (.csv or .xlsx)", type=["csv", "xlsx"])

if uploaded is not None:
    file_bytes = uploaded.getvalue()
    file_hash = hashlib.md5(file_bytes).hexdigest()

    # Reset stale state instantly if a new file is uploaded
    if "file_hash" not in st.session_state or st.session_state["file_hash"] != file_hash:
        st.session_state["file_hash"] = file_hash
        st.session_state["current_filename"] = uploaded.name
        st.session_state["raw_file_bytes"] = file_bytes
        if "ai_output" in st.session_state:
            del st.session_state["ai_output"]
        if "backend_api_result" in st.session_state:
            del st.session_state["backend_api_result"]

        try:
            if uploaded.name.lower().endswith('.csv'):
                try:
                    orig_df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
                except UnicodeDecodeError:
                    orig_df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")
            else:
                orig_df = pd.read_excel(io.BytesIO(file_bytes))
            
            if len(orig_df) > 50000:
                st.warning(f"Large dataset detected ({len(orig_df):,} rows). Processing performance may vary in Beta.")

            st.session_state["active_df"] = orig_df.copy()
        except Exception as e:
            st.error(f"Error loading file: {e}")
            st.stop()

    df = st.session_state["active_df"]
    engine = BusinessDataEngine(df)
    df_cleaned = engine.clean_text_numeric_columns()
    df_cleaned = engine.remove_totals_rows(df_cleaned)

    # SIDEBAR: MAPPING & CONFIGURATION CONTROLS
    st.sidebar.markdown("### ⚙️ Column & Currency Mapping")
    currency_symbol = st.sidebar.selectbox("Select Currency", ["₦", "$", "€", "£"], index=0)
    
    # Smart Filtering: Exclude ID-like or year/index columns from auto-selection
    valid_num_cols = [
        c for c in engine.num_cols 
        if not any(k in c.lower() for k in ['id', 'code', 'year', 'index', 'number', 'zip'])
    ]
    if not valid_num_cols:
        valid_num_cols = engine.num_cols

    rev_cands = [c for c in valid_num_cols if any(k in c.lower() for k in ['revenue', 'sales', 'amount', 'total', 'price', 'income'])]
    cost_cands = [c for c in valid_num_cols if any(k in c.lower() for k in ['cost', 'expense', 'spend', 'budget'])]

    default_rev_idx = valid_num_cols.index(rev_cands[0]) if rev_cands else 0
    sel_rev = st.sidebar.selectbox("Revenue / Sales Column", valid_num_cols, index=default_rev_idx)
    
    default_cost_idx = valid_num_cols.index(cost_cands[0]) + 1 if cost_cands else 0
    sel_cost = st.sidebar.selectbox("Cost / Expense Column (Opt.)", ["None"] + valid_num_cols, index=default_cost_idx if cost_cands else 0)
    
    date_cands = [c for c in df_cleaned.columns if any(k in c.lower() for k in ['date', 'time', 'year', 'month', 'period', 'created'])]
    sel_date = st.sidebar.selectbox("Date / Period Column", ["None"] + df_cleaned.columns.tolist(), index=df_cleaned.columns.get_loc(date_cands[0])+1 if date_cands else 0)

    dayfirst_option = st.sidebar.checkbox("Day-first Date Format (DD/MM/YYYY)", value=True)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Dataset Filters")
    filtered_df = df_cleaned.copy()
    if engine.cat_cols:
        filter_cat_col = st.sidebar.selectbox("Filter Category", ["None"] + engine.cat_cols)
        if filter_cat_col != "None":
            unique_vals = df_cleaned[filter_cat_col].dropna().unique().tolist()
            selected_vals = st.sidebar.multiselect(f"Select {filter_cat_col}", unique_vals, default=unique_vals)
            if selected_vals:
                filtered_df = filtered_df[filtered_df[filter_cat_col].isin(selected_vals)]

    st.sidebar.caption(f"Active Records: {len(filtered_df):,} / {len(df):,}")
    
    if st.sidebar.button("Reset Dataset View"):
        st.session_state.pop("ai_output", None)
        st.session_state.pop("backend_api_result", None)
        st.rerun()

    if st.sidebar.button("Sign Out"):
        st.session_state.clear()
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
        "Beta Feedback",
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
            if st.session_state.get("ai_call_count", 0) >= 5:
                st.error("Session AI call limit reached (5/5). Please restart your session to continue generating AI advisories.")
            else:
                if st.button("Generate Strategic Advisory", type="primary"):
                    with st.spinner("Analyzing verified metrics and compiling advisory..."):
                        try:
                            st.session_state["ai_call_count"] = st.session_state.get("ai_call_count", 0) + 1
                            total_rows = len(filtered_df)
                            health_score, _, _, _ = engine.audit_data_quality(filtered_df)
                            num_summary = filtered_df[engine.num_cols].describe().to_string() if engine.num_cols else "No numeric data"
                            
                            verified_stats = f"""
                            Dataset Statistics:
                            - Filename: {st.session_state['current_filename']}
                            - Filtered Row Count: {total_rows:,}
                            - Data Health Index: {health_score}%
                            - Mapped Revenue Column: {sel_rev}
                            - Mapped Cost Column: {sel_cost}
                            - Numeric Summary:
                            {num_summary}
                            """
                            
                            advisory_result = fetch_ai_advisory_from_backend(verified_stats, BACKEND_SECRET_KEY)
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
        
        total_revenue = filtered_df[sel_rev].sum() if sel_rev in filtered_df else 0.0
        total_costs = filtered_df[sel_cost].sum() if sel_cost != "None" and sel_cost in filtered_df else 0.0
        net_profit = total_revenue - total_costs
        profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Total Revenue", f"{currency_symbol}{total_revenue:,.2f}")
        p2.metric("Total Costs", f"{currency_symbol}{total_costs:,.2f}")
        p3.metric("Net Profit", f"{currency_symbol}{net_profit:,.2f}")
        p4.metric("Profit Margin", f"{profit_margin:.1f}%")

        st.markdown("---")
        if sel_date != "None" and sel_date in filtered_df.columns:
            try:
                temp_df = filtered_df.copy()
                initial_date_count = len(temp_df)
                temp_df[sel_date] = pd.to_datetime(temp_df[sel_date], dayfirst=dayfirst_option, errors='coerce')
                dropped_dates = initial_date_count - len(temp_df.dropna(subset=[sel_date]))
                if dropped_dates > 0:
                    st.info(f"Date Parser: Successfully parsed dates ({initial_date_count - dropped_dates} valid, {dropped_dates} rows unparseable/dropped).")
                
                temp_df = temp_df.dropna(subset=[sel_date, sel_rev])
                trend = temp_df.groupby(sel_date)[sel_rev].sum().reset_index().sort_values(sel_date)
                if len(trend) > 1:
                    fig_trend = px.line(trend, x=sel_date, y=sel_rev, title=f"Trend of {sel_rev} over {sel_date}", template="plotly_dark", color_discrete_sequence=["#2563eb"])
                    st.plotly_chart(fig_trend, use_container_width=True)
                else:
                    fig_hist = px.histogram(filtered_df, x=sel_rev, title=f"Distribution of {sel_rev}", template="plotly_dark", color_discrete_sequence=["#2563eb"])
                    st.plotly_chart(fig_hist, use_container_width=True)
            except Exception:
                fig_hist = px.histogram(filtered_df, x=sel_rev, title=f"Distribution of {sel_rev}", template="plotly_dark", color_discrete_sequence=["#2563eb"])
                st.plotly_chart(fig_hist, use_container_width=True)
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
                t_rev = filtered_df[sel_rev].sum() if sel_rev in filtered_df else 0.0
                t_cost = filtered_df[sel_cost].sum() if sel_cost != "None" and sel_cost in filtered_df else 0.0
                n_profit = t_rev - t_cost
                p_margin = (n_profit / t_rev * 100) if t_rev > 0 else 0.0

                # Slide 1: Title
                slide1 = prs.slides.add_slide(prs.slide_layouts[0])
                slide1.shapes.title.text = "Executive Financial Intelligence Report (Pilot Beta)"
                slide1.placeholders[1].text = f"Source: {st.session_state['current_filename']}\nPrepared for: {user_name} ({user_org})"

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
                    ("Financial KPI Domain", "Mapped Calculation"),
                    (f"Revenue Metric ({sel_rev})", f"{currency_symbol}{t_rev:,.2f}"),
                    (f"Cost Metric ({sel_cost if sel_cost != 'None' else 'None'})", f"{currency_symbol}{t_cost:,.2f}"),
                    ("Net Business Profit", f"{currency_symbol}{n_profit:,.2f}"),
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
                    "• Risk Mitigation: Ensures irregular expense spikes or unusual figures are flagged prior to reporting."
                )

                # Slide 6: Recommendations
                slide6 = prs.slides.add_slide(prs.slide_layouts[1])
                slide6.shapes.title.text = "5. Strategic Recommendations & General Guidance (Beta)"
                slide6.placeholders[1].text_frame.text = (
                    "1. Scale High-Margin Offerings: Reallocate budget toward verified top-performing categories.\n"
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

    # TAB 7: BETA FEEDBACK (Frictionless Google Form embed)
    with tab_objs[6]:
        st.subheader("Beta Tester Feedback Form")
        st.caption("Help us improve! Please submit your feedback using our Google Form below.")
        
        st.markdown("""
            <div style='text-align: center; padding: 30px; background-color: #1e293b; border-radius: 12px; border: 1px solid #334155; margin-top: 20px;'>
                <h3>We value your pilot feedback</h3>
                <p style='color: #94a3b8; margin-bottom: 20px;'>Click the button below to open our quick 2-minute feedback form.</p>
                <a href="https://forms.gle/your-feedback-google-form-link" target="_blank">
                    <button style='background-color: #2563eb; color: white; border: none; border-radius: 8px; font-weight: 600; padding: 0.8rem 1.6rem; cursor: pointer;'>Open Feedback Form ↗</button>
                </a>
            </div>
        """, unsafe_allow_html=True)

    # TAB 8: BACKEND DIAGNOSTICS (Hidden / Restricted in production)
    with tab_objs[7]:
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
                        api_result = analyze_dataset_via_backend_api(st.session_state["current_filename"], file_bytes, mime_type, BACKEND_SECRET_KEY)
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