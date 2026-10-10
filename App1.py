"""
Executive Data Intelligence Suite (Cohere AI Engine & FastAPI Backend Integration)
Phase 3 Decoupled Client — Includes Autonomous AI Dashboard Orchestrator.
To run locally: streamlit run App1.py
"""

import io
import os
import time
import json
import hashlib
import requests
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import cohere
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

# ----------------------------------------------------------------------
# FastAPI Backend Configuration
# ----------------------------------------------------------------------
BACKEND_URL = "http://127.0.0.1:8000"

def check_backend_health() -> bool:
    """Verifies connection with the FastAPI server."""
    try:
        res = requests.get(f"{BACKEND_URL}/", timeout=2)
        return res.status_code == 200
    except Exception:
        return False

def analyze_dataset_via_backend_api(file_name: str, file_bytes: bytes, file_type: str) -> dict:
    """Sends uploaded dataset payload to FastAPI backend for analysis."""
    files = {"file": (file_name, file_bytes, file_type)}
    response = requests.post(f"{BACKEND_URL}/api/v1/analyze-file", files=files, timeout=10)
    if response.status_code == 200:
        return response.json()
    else:
        raise ValueError(f"Backend API error: {response.status_code}")

# ----------------------------------------------------------------------
# Page Configuration & Executive Styling
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Executive Data Intelligence Suite",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_cohere_api_key() -> str:
    """Retrieves Cohere API key safely from environment or Streamlit secrets."""
    if os.getenv("COHERE_API_KEY"):
        return os.getenv("COHERE_API_KEY")
    try:
        if "COHERE_API_KEY" in st.secrets:
            return st.secrets["COHERE_API_KEY"]
    except Exception:
        pass
    return ""

def compute_dataset_hash(file_bytes: bytes, sheet_name: str = None) -> str:
    """Creates a cryptographic hash of dataset content to prevent stale state."""
    hasher = hashlib.sha256(file_bytes)
    if sheet_name:
        hasher.update(sheet_name.encode("utf-8"))
    return hasher.hexdigest()

st.markdown("""
    <style>
    .stApp { background-color: #0f172a !important; color: #f8fafc !important; }
    section[data-testid="stSidebar"] { background-color: #1e293b !important; border-right: 1px solid #334155 !important; }
    div[data-testid="stMetric"] { background-color: #1e293b !important; border: 1px solid #334155 !important; padding: 18px 22px !important; border-radius: 10px !important; }
    div[data-testid="stMetric"] label { color: #94a3b8 !important; font-weight: 600 !important; font-size: 0.85rem !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #38bdf8 !important; font-weight: 700 !important; }
    button[data-baseweb="tab"] { color: #94a3b8 !important; font-weight: 600 !important; }
    button[aria-selected="true"] { color: #38bdf8 !important; border-bottom-color: #38bdf8 !important; }
    .stButton>button[kind="primary"] { background-color: #0284c7 !important; color: #ffffff !important; border-radius: 8px !important; }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Data Processing Engine
# ----------------------------------------------------------------------
@st.cache_data(show_spinner="Processing business records...")
def load_data(file_bytes: bytes, file_name: str, sheet_name=None) -> pd.DataFrame:
    ext = os.path.splitext(file_name)[-1].lower()
    buffer = io.BytesIO(file_bytes)

    if ext == ".csv":
        try:
            df = pd.read_csv(buffer)
        except UnicodeDecodeError:
            buffer.seek(0)
            df = pd.read_csv(buffer, encoding="latin-1")
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(buffer, sheet_name=sheet_name or 0)
    elif ext == ".parquet":
        df = pd.read_parquet(buffer)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    if df.columns.has_duplicates:
        df.columns = pd.io.parsers.ParserBase({'names': df.columns})._maybe_dedup_names(df.columns)
    return df

def list_sheets(file_bytes: bytes):
    return pd.ExcelFile(io.BytesIO(file_bytes)).sheet_names

# ----------------------------------------------------------------------
# PowerPoint Presentation Export Generator
# ----------------------------------------------------------------------
def generate_pptx_deck(metrics: dict, field_inventory: pd.DataFrame, briefing_text: str = "") -> bytes:
    prs = Presentation()
    
    # Slide 1: Title Slide
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = "Executive Data Intelligence Briefing"
    subtitle.text = "Automated Business Performance Report & AI Audit"

    # Slide 2: Data Profile Summary
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    shapes = slide.shapes
    shapes.title.text = "Dataset Health & Operational Summary"

    tf = slide.placeholders[1].text_frame
    tf.text = "Core Performance Indicators:"
    for label, val in metrics.items():
        p = tf.add_paragraph()
        p.text = f"• {label}: {val}"
        p.level = 0

    # Slide 3: Executive Briefing Content
    if briefing_text:
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = "AI Executive Strategic Briefing"
        tf = slide.placeholders[1].text_frame
        clean_lines = [line for line in briefing_text.split("\n") if line.strip()][:12]
        tf.text = "\n".join(clean_lines)

    buffer = io.BytesIO()
    prs.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

# ----------------------------------------------------------------------
# Business Data Engine
# ----------------------------------------------------------------------
class BusinessDataEngine:
    def __init__(self, df: pd.DataFrame, focus_field=None):
        self.df = df
        self.focus_field = focus_field
        self.num_cols = list(df.select_dtypes(include=[np.number]).columns)
        self.cat_cols = list(df.select_dtypes(include=["object", "category", "bool"]).columns)
        self.date_cols = list(df.select_dtypes(include=["datetime", "datetimetz"]).columns)

    def executive_metrics(self):
        df = self.df
        total_cells = df.shape[0] * df.shape[1]
        missing_cells = df.isnull().sum().sum()
        health_score = round(((total_cells - missing_cells) / total_cells) * 100, 1) if total_cells > 0 else 100
        
        return {
            "Total Records": f"{df.shape[0]:,}",
            "Data Fields": f"{df.shape[1]:,}",
            "Data Health Index": f"{health_score}%",
            "Duplicate Entries": f"{int(df.duplicated().sum()):,}"
        }

    def field_inventory(self):
        return pd.DataFrame({
            "Field Name": self.df.columns,
            "Field Type": [str(t).capitalize() for t in self.df.dtypes.values],
            "Recorded Entries": self.df.notnull().sum().values,
            "Unique Values": self.df.nunique().values,
        })

    def missing_summary(self):
        counts = self.df.isnull().sum()
        pct = (counts / len(self.df)) * 100
        out = pd.DataFrame({"Missing Entries": counts, "Missing Share (%)": pct.round(2)})
        return out[out["Missing Entries"] > 0].sort_values("Missing Entries", ascending=False)

    def numeric_summary(self):
        if not self.num_cols:
            return None
        summary = self.df[self.num_cols].describe().T
        summary.rename(columns={
            "count": "Record Count", "mean": "Average", "std": "Std Dev",
            "min": "Minimum", "25%": "25th Pct", "50%": "Median", "75%": "75th Pct", "max": "Maximum"
        }, inplace=True)
        return summary.round(2)

    def detect_anomalies(self):
        rows = []
        for col in self.num_cols:
            series = self.df[col].dropna()
            if len(series) < 4:
                continue
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            count = int(((series < lower) | (series > upper)).sum())
            if count > 0:
                rows.append({
                    "Business Field": col,
                    "Potential Outliers": count,
                    "Observed Outlier Share (%)": round(100 * count / len(series), 2),
                    "Expected Min": round(lower, 2),
                    "Expected Max": round(upper, 2),
                })
        return pd.DataFrame(rows)

    def compute_grounded_context(self) -> str:
        facts = []
        df = self.df

        for col in self.cat_cols[:3]:
            top_vals = df[col].value_counts().head(3).to_dict()
            facts.append(f"Top categories for '{col}': {top_vals}")

        if self.num_cols:
            sums = df[self.num_cols].sum().round(2).to_dict()
            means = df[self.num_cols].mean().round(2).to_dict()
            facts.append(f"Column Totals: {sums}")
            facts.append(f"Column Averages: {means}")

        if self.focus_field and self.num_cols and self.focus_field in self.cat_cols:
            top_num = self.num_cols[0]
            grouped = df.groupby(self.focus_field)[top_num].sum().nlargest(5).to_dict()
            facts.append(f"Top 5 '{self.focus_field}' by sum of '{top_num}': {grouped}")

        return "\n".join(facts)

    def generate_cohere_briefing(self, api_key: str, selected_model: str) -> str:
        co = cohere.ClientV2(api_key=api_key)

        metrics = self.executive_metrics()
        missing = self.missing_summary().to_dict(orient="index") if not self.missing_summary().empty else "None"
        anomalies = self.detect_anomalies().to_dict(orient="records") if not self.detect_anomalies().empty else "None"
        grounded_facts = self.compute_grounded_context()

        prompt = f"""
You are an elite C-suite Strategy Consultant & Data Architect. Review the verified dataset calculations below and write a concise, executive-level business briefing in clean Markdown.

### Verified Executive KPI Summary
{metrics}

### Operational Health & Missing Data
{missing}

### Risk & Statistical Outliers
{anomalies}

### Deterministic Data Facts & Calculations
{grounded_facts}

Focus Field: {self.focus_field if self.focus_field else "General Performance Audit"}

---
### Deliverable Requirements:
1. **Executive Briefing**: Summary of scale, health index, and utility.
2. **Operational Risks & Data Gaps**: Critical missing fields or outliers.
3. **Core Performance Insights**: Highlight exact values provided in the data facts above.
4. **Actionable Recommendations**: 3 to 4 prioritized strategic steps.
"""
        try:
            response = co.chat(
                model=selected_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            return response.message.content[0].text
        except Exception as e:
            return f"⚠️ Unable to generate briefing. Details: {str(e)}"

    def generate_orchestrator_blueprint(self, api_key: str, selected_model: str) -> dict:
        """Asks Cohere to analyze schema profile and return a clean JSON dashboard blueprint."""
        co = cohere.ClientV2(api_key=api_key)
        
        profile = {
            "columns": list(self.df.columns),
            "dtypes": {col: str(t) for col, t in self.df.dtypes.items()},
            "categorical_columns": self.cat_cols,
            "numeric_columns": self.num_cols,
            "total_rows": len(self.df)
        }

        prompt = f"""
You are an autonomous Master BI Orchestrator Agent. Analyze this dataset profile and return a dashboard blueprint strictly in valid JSON format (no markdown code blocks, just raw JSON).

Dataset Profile:
{profile}

JSON Structure Required:
{{
  "dashboard_title": "Suggested Executive Dashboard Title",
  "recommended_focus_metric": "Name of the most important numeric column",
  "recommended_category_dimension": "Name of the best categorical column",
  "key_insight": "A 2-sentence summary of what this dataset appears to track.",
  "suggested_charts": [
    {{"type": "bar", "x": "column_name", "y": "column_name", "title": "Chart Title"}},
    {{"type": "histogram", "x": "column_name", "title": "Distribution Title"}}
  ]
}}
"""
        try:
            response = co.chat(
                model=selected_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            raw_text = response.message.content[0].text.strip()
            # Clean potential markdown wrapping
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
            return json.loads(raw_text.strip())
        except Exception as e:
            return {
                "dashboard_title": "Autonomous Executive Dashboard",
                "recommended_focus_metric": self.num_cols[0] if self.num_cols else "N/A",
                "recommended_category_dimension": self.cat_cols[0] if self.cat_cols else "N/A",
                "key_insight": f"Fallback blueprint generated due to parsing error: {str(e)}",
                "suggested_charts": []
            }

    def execute_nl_pandas_query(self, api_key: str, selected_model: str, user_query: str) -> tuple[str, str, dict]:
        co = cohere.ClientV2(api_key=api_key)
        schema_info = {col: str(dtype) for col, dtype in zip(self.df.columns, self.df.dtypes)}
        
        prompt = f"""
You are a Python Data Analysis Assistant. Write ONLY executable Python code using pandas to answer the user's question.
The dataframe is already loaded as `df`. Store the final answer in a variable named `result`.

Dataframe Columns & Types:
{schema_info}

User Question: {user_query}

Rules:
- Do NOT include markdown formatting or backticks like ```python.
- Write raw Python code only.
- Set `result` to a string, DataFrame, Series, or number that answers the query.
"""
        start_time = time.time()
        try:
            response = co.chat(
                model=selected_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            code = response.message.content[0].text.strip().replace("```python", "").replace("```", "").strip()

            local_vars = {"df": self.df.copy(), "pd": pd, "np": np}
            exec(code, {}, local_vars)
            
            result = local_vars.get("result", "Query executed, but no `result` variable was assigned.")
            exec_time = round((time.time() - start_time) * 1000, 2)

            provenance = {
                "Execution Time": f"{exec_time} ms",
                "Rows Analyzed": f"{len(self.df):,}",
                "Columns Utilized": ", ".join([col for col in self.df.columns if col in code]),
                "Execution Code": code
            }
            return str(result), code, provenance

        except Exception as e:
            provenance = {"Execution Mode": "Error Handled", "Error": str(e)}
            return "Unable to execute query.", "# Execution error", provenance

# ----------------------------------------------------------------------
# Streamlit Application
# ----------------------------------------------------------------------
def main():
    st.title("💼 Executive Data Intelligence Suite")
    st.caption("Phase 3 Decoupled Client — Integrated with Autonomous BI Orchestrator & FastAPI")
    st.markdown("---")

    # Sidebar: System Status & Settings
    with st.sidebar:
        st.markdown("### 🔌 System Connectivity")
        is_backend_online = check_backend_health()
        if is_backend_online:
            st.success("🟢 FastAPI Backend: Online")
            st.caption(f"Connected to `{BACKEND_URL}`")
        else:
            st.warning("🟡 Local Mode (FastAPI Offline)")

        st.markdown("---")

    uploaded = st.file_uploader("📂 Upload Business Files (.csv or .xlsx)", type=["csv", "xlsx", "xls", "parquet"])
    
    if uploaded is None:
        st.info("👋 Welcome! Please upload your business dataset above to launch the analysis environment.")
        return

    file_bytes = uploaded.getvalue()
    sheet = None
    if uploaded.name.lower().endswith((".xlsx", ".xls")):
        sheets = list_sheets(file_bytes)
        if len(sheets) > 1:
            sheet = st.selectbox("Select Business Worksheet", sheets)

    current_hash = compute_dataset_hash(file_bytes, sheet)

    if "dataset_hash" not in st.session_state or st.session_state["dataset_hash"] != current_hash:
        try:
            loaded_df = load_data(file_bytes, uploaded.name, sheet)
            st.session_state["original_df"] = loaded_df.copy()
            st.session_state["current_df"] = loaded_df.copy()
            st.session_state["transformation_stack"] = []
            st.session_state["dataset_hash"] = current_hash
            st.session_state.pop("ai_briefing", None)
            st.session_state.pop("orchestrator_blueprint", None)
            st.session_state.pop("last_answer", None)
            st.session_state.pop("backend_api_result", None)
        except Exception as e:
            st.error(f"Error loading business file: {e}")
            return

    raw_df = st.session_state["current_df"]

    if raw_df.empty:
        st.warning("The uploaded file contains no active data records.")
        return

    # Interactive Global Filter Bar
    with st.expander("🔍 Interactive Global Filters (Applies Across All Tabs)", expanded=False):
        f_cols = st.columns(3)
        filtered_df = raw_df.copy()
        
        cat_cols = list(raw_df.select_dtypes(include=["object", "category"]).columns)
        num_cols = list(raw_df.select_dtypes(include=[np.number]).columns)

        if cat_cols:
            with f_cols[0]:
                filter_cat_col = st.selectbox("Filter Category Field", ["None"] + cat_cols)
                if filter_cat_col != "None":
                    selected_cats = st.multiselect("Select Categories", raw_df[filter_cat_col].dropna().unique().tolist())
                    if selected_cats:
                        filtered_df = filtered_df[filtered_df[filter_cat_col].isin(selected_cats)]

        if num_cols:
            with f_cols[1]:
                filter_num_col = st.selectbox("Filter Numeric Field", ["None"] + num_cols)
                if filter_num_col != "None":
                    min_v, max_v = float(raw_df[filter_num_col].min()), float(raw_df[filter_num_col].max())
                    if min_v < max_v:
                        val_range = st.slider(f"Range for {filter_num_col}", min_v, max_v, (min_v, max_v))
                        filtered_df = filtered_df[(filtered_df[filter_num_col] >= val_range[0]) & (filtered_df[filter_num_col] <= val_range[1])]

        with f_cols[2]:
            st.markdown("<br>", unsafe_allow_html=True)
            st.caption(f"**Filtered Output:** {len(filtered_df):,} of {len(raw_df):,} rows")

    df = filtered_df

    with st.sidebar:
        st.markdown("### ⚙️ Analysis Settings")
        target_selection = st.selectbox("Focus Field / KPI Domain", ["None"] + list(df.columns))
        focus_field = None if target_selection == "None" else target_selection

        st.markdown("---")
        st.markdown("### 📜 Transformation Stack")
        stack = st.session_state.get("transformation_stack", [])
        if stack:
            st.caption(f"Active Transformations: **{len(stack)}**")
            for idx, action in enumerate(stack, 1):
                st.text(f"{idx}. {action}")
            
            if st.button("⏪ Undo Last Transformation", use_container_width=True):
                st.session_state["transformation_stack"].pop()
                temp_df = st.session_state["original_df"].copy()
                st.session_state["current_df"] = temp_df
                st.rerun()
        else:
            st.caption("No transformations applied yet.")

        if st.button("🔄 Reset All Transformations", use_container_width=True):
            st.session_state["current_df"] = st.session_state["original_df"].copy()
            st.session_state["transformation_stack"] = []
            st.session_state.pop("ai_briefing", None)
            st.session_state.pop("orchestrator_blueprint", None)
            st.success("Dataset restored!")
            st.rerun()

    engine = BusinessDataEngine(df, focus_field)

    tabs = ["🤖 Autonomous AI Agent", "📈 Executive Dashboard", "🧹 Data Refinement", "📊 Metric Visualizations", "⚠️ Anomaly Audit"]
    if focus_field:
        tabs.append("🎯 Focus Field Drilldown")
    tabs.append("🤖 AI Executive Briefing & Export")
    tabs.append("⚡ FastAPI Backend Pipeline")

    tab_objs = st.tabs(tabs)

    # TAB 1: AUTONOMOUS AI AGENT ORCHESTRATOR
    with tab_objs[0]:
        st.subheader("🤖 Autonomous BI Orchestrator Agent")
        st.caption("Drop your data and let Cohere automatically inspect schema profiles, discover key metrics, and build your custom dashboard blueprint.")

        cohere_api_key = get_cohere_api_key()
        if not cohere_api_key:
            cohere_api_key = st.text_input("Enter Cohere API Key:", type="password", key="agent_key")

        if cohere_api_key:
            selected_model = st.selectbox("Select Orchestrator Model", ["command-a-03-2025", "command-r-plus-08-2024", "command-r-08-2024"], key="agent_model")
            
            if st.button("🚀 Run Autonomous Dashboard Orchestrator", type="primary"):
                with st.spinner("Agent is analyzing schema profile and building dashboard layout..."):
                    blueprint = engine.generate_orchestrator_blueprint(api_key=cohere_api_key, selected_model=selected_model)
                    st.session_state["orchestrator_blueprint"] = blueprint

        if "orchestrator_blueprint" in st.session_state:
            bp = st.session_state["orchestrator_blueprint"]
            st.markdown("---")
            st.markdown(f"### ✨ {bp.get('dashboard_title', 'Executive Dashboard')}")
            st.info(f"💡 **AI Orchestrator Insight:** {bp.get('key_insight', '')}")

            # Render Recommended KPIs
            metrics = engine.executive_metrics()
            cols = st.columns(len(metrics))
            for col, (label, val) in zip(cols, metrics.items()):
                col.metric(label, val)

            st.markdown("---")
            st.markdown("### 📊 Agent-Recommended Visualizations")
            
            rec_cat = bp.get("recommended_category_dimension")
            rec_num = bp.get("recommended_focus_metric")

            c_cols = st.columns(2)
            with c_cols[0]:
                if rec_cat and rec_cat in df.columns and rec_num and rec_num in df.columns:
                    grouped_df = df.groupby(rec_cat)[rec_num].sum().reset_index().nlargest(10, rec_num)
                    fig = px.bar(grouped_df, x=rec_cat, y=rec_num, title=f"Top {rec_cat} by {rec_num}", template="plotly_dark", color_discrete_sequence=["#38bdf8"])
                    st.plotly_chart(fig, use_container_width=True)
                elif engine.cat_cols and engine.num_cols:
                    fallback_cat = engine.cat_cols[0]
                    fallback_num = engine.num_cols[0]
                    grouped_df = df.groupby(fallback_cat)[fallback_num].sum().reset_index().nlargest(10, fallback_num)
                    fig = px.bar(grouped_df, x=fallback_cat, y=fallback_num, title=f"Top {fallback_cat} by {fallback_num}", template="plotly_dark", color_discrete_sequence=["#38bdf8"])
                    st.plotly_chart(fig, use_container_width=True)

            with c_cols[1]:
                if rec_num and rec_num in df.columns:
                    fig_hist = px.histogram(df, x=rec_num, title=f"Distribution of {rec_num}", template="plotly_dark", color_discrete_sequence=["#14b8a6"])
                    st.plotly_chart(fig_hist, use_container_width=True)
                elif engine.num_cols:
                    fallback_num = engine.num_cols[0]
                    fig_hist = px.histogram(df, x=fallback_num, title=f"Distribution of {fallback_num}", template="plotly_dark", color_discrete_sequence=["#14b8a6"])
                    st.plotly_chart(fig_hist, use_container_width=True)

    # TAB 2: DASHBOARD
    with tab_objs[1]:
        st.subheader("Key Data Health Metrics")
        metrics = engine.executive_metrics()
        cols = st.columns(len(metrics))
        for col, (label, val) in zip(cols, metrics.items()):
            col.metric(label, val)

        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns([3, 2])
        with col1:
            st.subheader("Records Preview")
            n_rows = st.slider("Display Rows", 5, min(100, len(df)), 10)
            st.dataframe(df.head(n_rows), use_container_width=True)
        with col2:
            st.subheader("Field Inventory")
            st.dataframe(engine.field_inventory(), use_container_width=True, hide_index=True)

    # TAB 3: DATA REFINEMENT
    with tab_objs[2]:
        st.subheader("🧹 Interactive Data Refinement & Cleanup")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 1. Clean Missing Values")
            missing_cols = list(df.columns[df.isnull().any()])
            if missing_cols:
                col_to_fix = st.selectbox("Select Field to Repair", missing_cols)
                is_num = pd.api.types.is_numeric_dtype(df[col_to_fix])

                strategies = ["Remove empty rows"]
                if is_num:
                    strategies.extend(["Fill with Field Average", "Fill with Median", "Set to Zero"])
                else:
                    strategies.extend(["Fill with Most Frequent (Mode)", "Set to 'N/A'"])

                strategy = st.selectbox("Correction Method", strategies)

                if st.button("Apply Correction", type="primary"):
                    working_df = st.session_state["current_df"].copy()
                    
                    if strategy == "Remove empty rows":
                        working_df = working_df.dropna(subset=[col_to_fix])
                    elif strategy == "Fill with Field Average" and is_num:
                        working_df[col_to_fix] = working_df[col_to_fix].fillna(working_df[col_to_fix].mean())
                    elif strategy == "Fill with Median" and is_num:
                        working_df[col_to_fix] = working_df[col_to_fix].fillna(working_df[col_to_fix].median())
                    elif strategy == "Set to Zero" and is_num:
                        working_df[col_to_fix] = working_df[col_to_fix].fillna(0)
                    elif strategy == "Fill with Most Frequent (Mode)" and not is_num:
                        mode_vals = working_df[col_to_fix].mode()
                        if not mode_vals.empty:
                            working_df[col_to_fix] = working_df[col_to_fix].fillna(mode_vals[0])
                    elif strategy == "Set to 'N/A'" and not is_num:
                        working_df[col_to_fix] = working_df[col_to_fix].fillna("N/A")

                    st.session_state["current_df"] = working_df
                    st.session_state["transformation_stack"].append(f"Fixed '{col_to_fix}' using {strategy}")
                    st.success(f"Updated field: {col_to_fix}")
                    st.rerun()
            else:
                st.success("✅ All data fields are 100% complete!")

        with c2:
            st.markdown("##### 2. Deduplication & Column Removal")
            dup_count = df.duplicated().sum()
            st.write(f"Duplicate Entries Identified: **{dup_count}**")
            if dup_count > 0 and st.button("Remove Duplicate Entries"):
                st.session_state["current_df"] = df.drop_duplicates()
                st.session_state["transformation_stack"].append(f"Purged {dup_count} duplicate rows")
                st.success("Duplicates purged!")
                st.rerun()

            remove_cols = st.multiselect("Select Fields to Exclude", list(df.columns))
            if remove_cols and st.button("Remove Selected Fields"):
                st.session_state["current_df"] = df.drop(columns=remove_cols)
                st.session_state["transformation_stack"].append(f"Dropped columns: {', '.join(remove_cols)}")
                st.success("Fields excluded!")
                st.rerun()

        st.markdown("---")
        st.subheader("💾 Export Refined Records")
        e_col1, e_col2 = st.columns(2)
        with e_col1:
            csv_data = st.session_state["current_df"].to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Refined CSV", data=csv_data, file_name="refined_data.csv", mime="text/csv", use_container_width=True)
        with e_col2:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                st.session_state["current_df"].to_excel(writer, index=False, sheet_name="Clean Data")
            excel_buffer.seek(0)
            st.download_button("📥 Download Refined Excel", data=excel_buffer.getvalue(), file_name="refined_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    # TAB 4: VISUALIZATIONS
    with tab_objs[3]:
        st.subheader("📊 Business Data Explorers")
        v1, v2 = st.columns(2)
        with v1:
            if engine.num_cols:
                num_field = st.selectbox("Select Metric Field", engine.num_cols)
                st.plotly_chart(px.histogram(df, x=num_field, title=f"Distribution: {num_field}", color_discrete_sequence=["#38bdf8"], template="plotly_dark"))
        with v2:
            if engine.cat_cols:
                cat_field = st.selectbox("Select Category Field", engine.cat_cols)
                counts = df[cat_field].astype(str).value_counts().head(10).reset_index()
                counts.columns = [cat_field, "Volume"]
                fig_cat = px.bar(counts, x="Volume", y=cat_field, orientation="h", title=f"Top Categories: {cat_field}", template="plotly_dark")
                fig_cat.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_cat)

    # TAB 5: ANOMALIES
    with tab_objs[4]:
        st.subheader("⚠️ Anomaly & Risk Audit")
        if engine.num_cols:
            anomalies = engine.detect_anomalies()
            if anomalies.empty:
                st.success("✅ No statistical outliers detected using 1.5x IQR rule.")
            else:
                st.dataframe(anomalies, use_container_width=True, hide_index=True)
                inspect_field = st.selectbox("Select Field for Outlier Inspection", anomalies["Business Field"].tolist())
                st.plotly_chart(px.box(df, y=inspect_field, title=f"Outlier Map: {inspect_field}", color_discrete_sequence=["#f43f5e"], template="plotly_dark"))
        else:
            st.info("No numerical metric fields available for anomaly detection.")

    tab_offset = 5
    if focus_field:
        with tab_objs[tab_offset]:
            st.subheader(f"🎯 KPI Drilldown: {focus_field}")
            if pd.api.types.is_numeric_dtype(df[focus_field]):
                st.plotly_chart(px.histogram(df, x=focus_field, title=f"Distribution of {focus_field}", color_discrete_sequence=["#14b8a6"], template="plotly_dark"))
            else:
                counts = df[focus_field].value_counts().reset_index()
                counts.columns = [focus_field, "Count"]
                st.plotly_chart(px.bar(counts, x=focus_field, y="Count", title=f"Volume: {focus_field}", template="plotly_dark"))
        tab_offset += 1

    # TAB 6: COHERE AI EXECUTIVE BRIEFING & EXPORT
    with tab_objs[tab_offset]:
        st.subheader("🤖 Grounded AI Briefing & Executive Presentation Deck Export")
        cohere_api_key = get_cohere_api_key()

        if not cohere_api_key:
            st.error("🔑 Cohere API Key Missing: Configure `COHERE_API_KEY` in Secrets or Environment.")
            cohere_api_key = st.text_input("Enter key manually:", type="password", key="briefing_key")

        if cohere_api_key:
            cohere_models = [
                "command-a-03-2025",
                "command-r-plus-08-2024",
                "command-r-08-2024",
                "command-r7b-12-2024"
            ]
            selected_model = st.selectbox("Select Cohere Model", cohere_models, key="briefing_model")

            if st.button("🚀 Generate Executive Briefing", type="primary"):
                with st.spinner("Calculating facts & querying Cohere AI..."):
                    briefing_md = engine.generate_cohere_briefing(api_key=cohere_api_key, selected_model=selected_model)
                    st.session_state["ai_briefing"] = briefing_md

        if "ai_briefing" in st.session_state:
            st.markdown("---")
            st.markdown(st.session_state["ai_briefing"])
            
            st.markdown("### 📊 Export Executive Presentation Deck")
            pptx_bytes = generate_pptx_deck(
                metrics=engine.executive_metrics(),
                field_inventory=engine.field_inventory(),
                briefing_text=st.session_state["ai_briefing"]
            )
            st.download_button(
                label="💻 Download Executive PowerPoint Presentation (.pptx)",
                data=pptx_bytes,
                file_name="Executive_Data_Briefing.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True
            )

        if cohere_api_key:
            st.markdown("---")
            st.subheader("⚡ Execute Dynamic Data Queries (Natural Language to Pandas)")
            user_query = st.text_input("Enter query (e.g., 'Show top 5 categories by average value')")
            if st.button("⚡ Execute Query Sandbox"):
                if user_query.strip():
                    with st.spinner("Generating Pandas code and running in execution sandbox..."):
                        res_val, code_executed, provenance = engine.execute_nl_pandas_query(
                            api_key=cohere_api_key,
                            selected_model=selected_model,
                            user_query=user_query
                        )
                        st.session_state["sandbox_result"] = res_val
                        st.session_state["sandbox_code"] = code_executed
                        st.session_state["sandbox_provenance"] = provenance

            if "sandbox_result" in st.session_state:
                st.markdown("### 📊 Query Result")
                st.code(st.session_state["sandbox_result"])
                
                with st.expander("🔍 View Execution Code & Analytical Provenance"):
                    st.markdown("**Executed Pandas Code:**")
                    st.code(st.session_state["sandbox_code"], language="python")
                    st.markdown("**Execution Audit & Provenance:**")
                    st.json(st.session_state["sandbox_provenance"])

    tab_offset += 1

    # TAB 7: FASTAPI BACKEND SERVICE INTEGRATION (PHASE 3)
    with tab_objs[tab_offset]:
        st.subheader("⚡ Decoupled FastAPI Enterprise Backend Execution")
        st.caption("Transmit active datasets directly to the async FastAPI REST endpoint.")

        if not is_backend_online:
            st.warning("⚠️ FastAPI Server is currently offline. Start the Uvicorn server in your terminal (`uvicorn backend.app.main:app --reload --port 8000`) to enable remote API processing.")
        else:
            if st.button("🚀 Process & Audit Dataset via FastAPI Server", type="primary"):
                with st.spinner("Transmitting dataset payload to FastAPI REST API..."):
                    try:
                        mime_type = "text/csv" if uploaded.name.endswith(".csv") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        api_result = analyze_dataset_via_backend_api(uploaded.name, file_bytes, mime_type)
                        st.session_state["backend_api_result"] = api_result
                        st.success("Analysis complete from FastAPI server!")
                    except Exception as err:
                        st.error(f"Failed to communicate with FastAPI server: {err}")

        if "backend_api_result" in st.session_state:
            res = st.session_state["backend_api_result"]
            st.markdown("---")
            st.markdown("### 📈 Backend API Response Payload")
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("File Name", res.get("filename", "N/A"))
            col_b.metric("Total Records", f"{res.get('records', 0):,}")
            col_c.metric("Data Fields", res.get("fields_count", 0))
            col_d.metreic("Health Index", res.get("data_health_index", "0%")) if hasattr(col_d, 'metreic') else col_d.metric("Health Index", res.get("data_health_index", "0%"))

            with st.expander("🔍 View Full JSON Payload"):
                st.json(res)

if __name__ == "__main__":
    main()