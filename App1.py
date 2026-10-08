"""
Universal Data Analyzer & Business AI Assistant
Production-ready dashboard built for business owners & clients.
To run locally: streamlit run App1.py
"""

import io
import os
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from google import genai
from google.genai import types

# ----------------------------------------------------------------------
# Page Configuration & Matching Dark Executive Theme Styling
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Executive Data Intelligence Suite",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Secure API Key Retrieval (Streamlit Secrets -> Environment Variables)
def get_gemini_api_key() -> str:
    """Retrieves Gemini API key safely without crashing on secrets TOML errors."""
    if os.getenv("GEMINI_API_KEY"):
        return os.getenv("GEMINI_API_KEY")
    
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

    return ""

# Matching Dark Slate & Cyan Executive Styling
st.markdown("""
    <style>
    /* Main Background & Clean Typography */
    .stApp {
        background-color: #0f172a !important;
        color: #f8fafc !important;
    }
    
    /* Sidebar Background */
    section[data-testid="stSidebar"] {
        background-color: #1e293b !important;
        border-right: 1px solid #334155 !important;
    }

    /* Executive Metric Card Styling */
    div[data-testid="stMetric"] {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        padding: 18px 22px !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3) !important;
    }
    div[data-testid="stMetric"] label {
        color: #94a3b8 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }

    /* Tab Styling */
    button[data-baseweb="tab"] {
        color: #94a3b8 !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 12px 20px !important;
    }
    button[aria-selected="true"] {
        color: #38bdf8 !important;
        border-bottom-color: #38bdf8 !important;
    }
    
    /* Primary Button Polish */
    .stButton>button[kind="primary"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
    }
    
    .stButton>button[kind="primary"]:hover {
        background-color: #0369a1 !important;
    }

    /* Download Buttons & secondary buttons */
    .stDownloadButton>button {
        background-color: #334155 !important;
        color: #f8fafc !important;
        border: 1px solid #475569 !important;
        border-radius: 8px !important;
    }
    .stDownloadButton>button:hover {
        background-color: #475569 !important;
        border-color: #64748b !important;
    }
    </style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Data Loading Engine
# ----------------------------------------------------------------------
@st.cache_data(show_spinner="Processing business records...")
def load_data(file_bytes: bytes, file_name: str, sheet_name=None) -> pd.DataFrame:
    ext = os.path.splitext(file_name)[-1].lower()
    buffer = io.BytesIO(file_bytes)

    if ext == ".csv":
        try:
            return pd.read_csv(buffer)
        except UnicodeDecodeError:
            buffer.seek(0)
            return pd.read_csv(buffer, encoding="latin-1")
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(buffer, sheet_name=sheet_name or 0)
    if ext == ".parquet":
        return pd.read_parquet(buffer)
    raise ValueError(f"Unsupported file format: {ext}")


def list_sheets(file_bytes: bytes):
    return pd.ExcelFile(io.BytesIO(file_bytes)).sheet_names


# ----------------------------------------------------------------------
# Business Data Intelligence Engine
# ----------------------------------------------------------------------
class BusinessDataEngine:
    def __init__(self, df: pd.DataFrame, target_column=None):
        self.df = df
        self.target_column = target_column
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
            if series.empty:
                continue
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            count = int(((series < lower) | (series > upper)).sum())
            if count > 0:
                rows.append({
                    "Business Field": col,
                    "Anomalies Detected": count,
                    "Anomaly Share (%)": round(count / len(self.df) * 100, 2),
                    "Expected Min": round(lower, 2),
                    "Expected Max": round(upper, 2),
                })
        return pd.DataFrame(rows)

    def generate_ai_briefing(self, api_key: str, selected_model: str) -> str:
        client = genai.Client(api_key=api_key)

        metrics = self.executive_metrics()
        missing = self.missing_summary().to_dict(orient="index") if not self.missing_summary().empty else "None"
        num_sum = self.numeric_summary()
        num_summary_dict = num_sum.to_dict(orient="index") if num_sum is not None else "None"
        anomalies = self.detect_anomalies().to_dict(orient="records") if not self.detect_anomalies().empty else "None"

        prompt = f"""
You are an elite C-suite Strategy Consultant & Senior Data Architect. Review the business dataset profile below and write a concise, executive-level business briefing in clean Markdown.

### Business Dataset Profile
- High-Level KPI Summary: {metrics}
- Categorical Attributes: {self.cat_cols}
- Numerical Metrics: {self.num_cols}
- Target/KPI Focus: {self.target_column if self.target_column else "General Performance Audit"}

### Operational Health & Missing Data
{missing}

### Risk & Anomaly Summary
{anomalies}

### Statistical Metric Ranges
{num_summary_dict}

---
### Deliverable Requirements:
1. **Executive Briefing**: High-level summary of dataset quality, scale, and strategic utility.
2. **Operational Risks & Data Gaps**: Immediate risks regarding missing fields or extreme outliers.
3. **Core Performance Insights**: Key trends, averages, or distribution highlights business leaders must know.
4. **Actionable Recommendations**: 3 to 4 prioritized strategic steps for business execution.
"""
        response = client.models.generate_content(
            model=selected_model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3)
        )
        return response.text


# ----------------------------------------------------------------------
# Application User Interface
# ----------------------------------------------------------------------
def main():
    st.title("💼 Executive Data Intelligence Suite")
    st.caption("Upload company records, generate automated data audits, and unlock instant AI business insights.")
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

    if "current_df" not in st.session_state or st.session_state.get("file_name") != uploaded.name:
        try:
            st.session_state["current_df"] = load_data(file_bytes, uploaded.name, sheet)
            st.session_state["file_name"] = uploaded.name
        except Exception as e:
            st.error(f"Error loading business file: {e}")
            return

    df = st.session_state["current_df"]

    if df.empty:
        st.warning("The uploaded file contains no active data records.")
        return

    with st.sidebar:
        st.markdown("### ⚙️ Analysis Settings")
        target_selection = st.selectbox("Primary KPI / Focus Field", ["None"] + list(df.columns))
        target = None if target_selection == "None" else target_selection

        st.markdown("---")
        st.markdown("### 📁 Dataset File Details")
        st.caption(f"**Filename:** {uploaded.name}")
        st.caption(f"**Active Records:** {len(df):,} rows")
        
        if st.button("🔄 Reset Data Transformations", use_container_width=True):
            st.session_state["current_df"] = load_data(file_bytes, uploaded.name, sheet)
            st.rerun()

    engine = BusinessDataEngine(df, target)

    tabs = ["📈 Executive Dashboard", "🧹 Data Refinement", "📊 Metric Visualizations", "⚠️ Anomaly Audit"]
    if target:
        tabs.append("🎯 Key Metric Drilldown")
    tabs.append("🤖 AI Executive Briefing")

    tab_objs = st.tabs(tabs)

    # ---- TAB 1: EXECUTIVE DASHBOARD ----
    with tab_objs[0]:
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

    # ---- TAB 2: DATA REFINEMENT ----
    with tab_objs[1]:
        st.subheader("🧹 Interactive Data Refinement & Cleanup")
        st.caption("Clean missing records, drop irrelevant fields, and export refined files.")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 1. Clean Missing Values")
            missing_cols = list(df.columns[df.isnull().any()])
            if missing_cols:
                col_to_fix = st.selectbox("Select Field to Repair", missing_cols)
                strategy = st.selectbox("Correction Method", ["Remove empty rows", "Fill with Field Average", "Set to Zero", "Set to 'N/A'"])
                
                if st.button("Apply Correction", type="primary"):
                    if strategy == "Remove empty rows":
                        st.session_state["current_df"] = df.dropna(subset=[col_to_fix])
                    elif strategy == "Fill with Field Average":
                        if pd.api.types.is_numeric_dtype(df[col_to_fix]):
                            fill_val = df[col_to_fix].mean()
                        else:
                            fill_val = df[col_to_fix].mode()[0]
                        st.session_state["current_df"][col_to_fix] = st.session_state["current_df"][col_to_fix].fillna(fill_val)
                    elif strategy == "Set to Zero":
                        st.session_state["current_df"][col_to_fix] = st.session_state["current_df"][col_to_fix].fillna(0)
                    elif strategy == "Set to 'N/A'":
                        st.session_state["current_df"][col_to_fix] = st.session_state["current_df"][col_to_fix].fillna("N/A")
                    st.success(f"Updated field: {col_to_fix}")
                    st.rerun()
            else:
                st.success("✅ All data fields are 100% complete!")

        with c2:
            st.markdown("##### 2. Deduplication & Column Removal")
            dup_count = df.duplicated().sum()
            st.write(f"Duplicate Entries Identified: **{dup_count}**")
            if dup_count > 0:
                if st.button("Remove Duplicate Entries"):
                    st.session_state["current_df"] = df.drop_duplicates()
                    st.success("Duplicates purged!")
                    st.rerun()

            remove_cols = st.multiselect("Select Fields to Exclude", list(df.columns))
            if remove_cols and st.button("Remove Selected Fields"):
                st.session_state["current_df"] = df.drop(columns=remove_cols)
                st.success("Fields excluded!")
                st.rerun()

        st.markdown("---")
        st.subheader("💾 Export Refined Business Records")
        e_col1, e_col2 = st.columns(2)
        with e_col1:
            csv_data = st.session_state["current_df"].to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Refined CSV", data=csv_data, file_name="refined_business_data.csv", mime="text/csv", use_container_width=True)
        with e_col2:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                st.session_state["current_df"].to_excel(writer, index=False, sheet_name="Clean Data")
            excel_buffer.seek(0)
            st.download_button("📥 Download Refined Excel", data=excel_buffer.getvalue(), file_name="refined_business_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    # ---- TAB 3: VISUALIZATIONS ----
    with tab_objs[2]:
        st.subheader("📊 Business Data Explorers")
        v1, v2 = st.columns(2)
        
        with v1:
            if engine.num_cols:
                num_field = st.selectbox("Select Metric Field", engine.num_cols)
                fig_num = px.histogram(df, x=num_field, title=f"Distribution Analysis: {num_field}", color_discrete_sequence=["#38bdf8"], template="plotly_dark")
                st.plotly_chart(fig_num)
                
        with v2:
            if engine.cat_cols:
                cat_field = st.selectbox("Select Category Field", engine.cat_cols)
                counts = df[cat_field].astype(str).value_counts().head(10).reset_index()
                counts.columns = [cat_field, "Volume"]
                fig_cat = px.bar(counts, x="Volume", y=cat_field, orientation="h", title=f"Top Categories: {cat_field}", color_continuous_scale="Blues", template="plotly_dark")
                fig_cat.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_cat)

    # ---- TAB 4: ANOMALIES ----
    with tab_objs[3]:
        st.subheader("⚠️ Anomaly & Risk Audit")
        if engine.num_cols:
            anomalies = engine.detect_anomalies()
            if anomalies.empty:
                st.success("✅ No extreme anomalies or data outliers detected.")
            else:
                st.dataframe(anomalies, use_container_width=True, hide_index=True)
                inspect_field = st.selectbox("Select Field for Outlier Inspection", anomalies["Business Field"].tolist())
                st.plotly_chart(px.box(df, y=inspect_field, title=f"Outlier Range Map: {inspect_field}", color_discrete_sequence=["#f43f5e"], template="plotly_dark"))
        else:
            st.info("No numerical metric fields available for anomaly detection.")

    tab_offset = 4
    if target:
        with tab_objs[tab_offset]:
            st.subheader(f"🎯 KPI Deep-Dive: {target}")
            if pd.api.types.is_numeric_dtype(df[target]):
                st.plotly_chart(px.histogram(df, x=target, title=f"Distribution of {target}", color_discrete_sequence=["#14b8a6"], template="plotly_dark"))
            else:
                counts = df[target].value_counts().reset_index()
                counts.columns = [target, "Count"]
                st.plotly_chart(px.bar(counts, x=target, y="Count", title=f"Class Volume: {target}", template="plotly_dark"))
        tab_offset += 1

    # ---- FINAL TAB: AI EXECUTIVE BRIEFING ----
    with tab_objs[tab_offset]:
        st.subheader("🤖 AI Executive Business Briefing")
        st.caption("Generate an automated strategic briefing tailored for executive leadership.")

        api_key = get_gemini_api_key()

        if not api_key:
            st.error("🔑 API Key Missing: Please configure `GEMINI_API_KEY` in Streamlit Secrets or Environment Variables before running AI reports.")
        else:
            try:
                client = genai.Client(api_key=api_key)
                available_models = [m.name.replace("models/", "") for m in client.models.list() if "generateContent" in getattr(m, "supported_generation_methods", [])]
            except Exception:
                available_models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]

            selected_model = st.selectbox("Select Gemini Model", available_models)

            if st.button("🚀 Generate Executive AI Briefing", type="primary"):
                with st.spinner("Analyzing operational records with Gemini AI..."):
                    try:
                        briefing_md = engine.generate_ai_briefing(api_key=api_key, selected_model=selected_model)
                        st.session_state["ai_briefing"] = briefing_md
                        st.success("Executive Briefing generated successfully!")
                    except Exception as err:
                        st.error(f"Failed to generate briefing: {err}")

        if "ai_briefing" in st.session_state:
            st.markdown("---")
            st.markdown(st.session_state["ai_briefing"])
            st.download_button(
                label="📄 Download Executive Briefing (.md)",
                data=st.session_state["ai_briefing"],
                file_name="Executive_Data_Briefing.md",
                mime="text/markdown"
            )


if __name__ == "__main__":
    main()