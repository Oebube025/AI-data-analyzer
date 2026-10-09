"""
Executive Data Intelligence Suite (Cohere AI Engine)
Production-grade dashboard with deterministic AI grounding, state hashing, and type-safe data cleaning.
To run locally: streamlit run App1.py
"""

import io
import os
import hashlib
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import cohere

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
    """Creates a cryptographic hash of dataset content to prevent stale state (F-02)."""
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

    # Prevent duplicate column conflicts (F-10)
    if df.columns.has_duplicates:
        df.columns = pd.io.parsers.ParserBase({'names': df.columns})._maybe_dedup_names(df.columns)
    return df

def list_sheets(file_bytes: bytes):
    return pd.ExcelFile(io.BytesIO(file_bytes)).sheet_names

# ----------------------------------------------------------------------
# Business Data Engine with Grounded AI Analytics
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
        """Corrected outlier detection using observed-value denominators (F-06, F-07)."""
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
        """Calculates deterministic Pandas aggregations to ground AI responses in facts (F-01)."""
        facts = []
        df = self.df

        # Top Category Summaries
        for col in self.cat_cols[:3]:
            top_vals = df[col].value_counts().head(3).to_dict()
            facts.append(f"Top categories for '{col}': {top_vals}")

        # Primary Numerical Highlights
        if self.num_cols:
            sums = df[self.num_cols].sum().round(2).to_dict()
            means = df[self.num_cols].mean().round(2).to_dict()
            facts.append(f"Column Totals: {sums}")
            facts.append(f"Column Averages: {means}")

        # Focus Field Groupbys
        if self.focus_field and self.num_cols and self.focus_field in self.cat_cols:
            top_num = self.num_cols[0]
            grouped = df.groupby(self.focus_field)[top_num].sum().nlargest(5).to_dict()
            facts.append(f"Top 5 '{self.focus_field}' by sum of '{top_num}': {grouped}")

        return "\n".join(facts)

    def generate_cohere_briefing(self, api_key: str, selected_model: str) -> str:
        """Generates executive briefing using calculated facts (F-01)."""
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

    def ask_cohere_assistant(self, api_key: str, selected_model: str, user_query: str) -> str:
        """Grounded Q&A assistant to eliminate arithmetic halluncinations (F-01, F-04)."""
        co = cohere.ClientV2(api_key=api_key)

        metrics = self.executive_metrics()
        grounded_facts = self.compute_grounded_context()

        context_prompt = f"""
Calculated Dataset Context:
- Summary Metrics: {metrics}
- Deterministic Aggregations & Facts:
{grounded_facts}

User Question: {user_query}

Instructions: Answer strictly using the computed facts provided above. If the exact answer cannot be derived from these facts, explicitly state that the calculation is not available.
"""
        try:
            response = co.chat(
                model=selected_model,
                messages=[{"role": "user", "content": context_prompt}],
                temperature=0.2
            )
            return response.message.content[0].text
        except Exception as e:
            return f"⚠️ Request failed. Provider error recorded."

# ----------------------------------------------------------------------
# Streamlit Interface
# ----------------------------------------------------------------------
def main():
    st.title("💼 Executive Data Intelligence Suite")
    st.caption("Powered by Cohere Enterprise AI Models with Deterministic Grounding")
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

    # Cryptographic Hash Dataset Key (F-02)
    current_hash = compute_dataset_hash(file_bytes, sheet)

    if "dataset_hash" not in st.session_state or st.session_state["dataset_hash"] != current_hash:
        try:
            loaded_df = load_data(file_bytes, uploaded.name, sheet)
            st.session_state["original_df"] = loaded_df.copy()  # Immutable original (F-09)
            st.session_state["current_df"] = loaded_df.copy()
            st.session_state["dataset_hash"] = current_hash
            st.session_state.pop("ai_briefing", None)
            st.session_state.pop("last_answer", None)
        except Exception as e:
            st.error(f"Error loading business file: {e}")
            return

    df = st.session_state["current_df"]

    if df.empty:
        st.warning("The uploaded file contains no active data records.")
        return

    with st.sidebar:
        st.markdown("### ⚙️ Analysis Settings")
        target_selection = st.selectbox("Focus Field / KPI Domain", ["None"] + list(df.columns))
        focus_field = None if target_selection == "None" else target_selection

        st.markdown("---")
        st.markdown("### 📁 Dataset File Details")
        st.caption(f"**Filename:** {uploaded.name}")
        st.caption(f"**Active Records:** {len(df):,} rows")
        
        # 1-Click Reset restores original_df (F-09)
        if st.button("🔄 Reset Transformations", use_container_width=True):
            st.session_state["current_df"] = st.session_state["original_df"].copy()
            st.session_state.pop("ai_briefing", None)
            st.session_state.pop("last_answer", None)
            st.success("Dataset restored to original state!")
            st.rerun()

    engine = BusinessDataEngine(df, focus_field)

    tabs = ["📈 Executive Dashboard", "🧹 Data Refinement", "📊 Metric Visualizations", "⚠️ Anomaly Audit"]
    if focus_field:
        tabs.append("🎯 Focus Field Drilldown")
    tabs.append("🤖 AI Executive Briefing")

    tab_objs = st.tabs(tabs)

    # TAB 1: DASHBOARD
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

    # TAB 2: TYPE-SAFE DATA REFINEMENT (F-03)
    with tab_objs[1]:
        st.subheader("🧹 Interactive Data Refinement & Cleanup")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 1. Clean Missing Values")
            missing_cols = list(df.columns[df.isnull().any()])
            if missing_cols:
                col_to_fix = st.selectbox("Select Field to Repair", missing_cols)
                is_num = pd.api.types.is_numeric_dtype(df[col_to_fix])

                # Dtype-aware choices (F-03)
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
                st.success("Duplicates purged!")
                st.rerun()

            remove_cols = st.multiselect("Select Fields to Exclude", list(df.columns))
            if remove_cols and st.button("Remove Selected Fields"):
                st.session_state["current_df"] = df.drop(columns=remove_cols)
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

    # TAB 3: VISUALIZATIONS
    with tab_objs[2]:
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

    # TAB 4: ANOMALIES
    with tab_objs[3]:
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

    tab_offset = 4
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

    # TAB 5: COHERE GROUNDED AI BRIEFING
    with tab_objs[tab_offset]:
        st.subheader("🤖 Grounded AI Executive Briefing (Cohere)")
        cohere_api_key = get_cohere_api_key()

        if not cohere_api_key:
            st.error("🔑 Cohere API Key Missing: Configure `COHERE_API_KEY` in Secrets or Environment.")
            cohere_api_key = st.text_input("Enter key manually:", type="password")

        if cohere_api_key:
            cohere_models = [
                "command-a-03-2025",
                "command-r-plus-08-2024",
                "command-r-08-2024",
                "command-r7b-12-2024"
            ]
            selected_model = st.selectbox("Select Cohere Model", cohere_models)

            if st.button("🚀 Generate Grounded Executive Briefing", type="primary"):
                with st.spinner("Calculating facts & querying Cohere AI..."):
                    briefing_md = engine.generate_cohere_briefing(api_key=cohere_api_key, selected_model=selected_model)
                    st.session_state["ai_briefing"] = briefing_md

        if "ai_briefing" in st.session_state:
            st.markdown("---")
            st.markdown(st.session_state["ai_briefing"])
            st.download_button("📄 Download Briefing (.md)", data=st.session_state["ai_briefing"], file_name="Executive_Briefing.md", mime="text/markdown")

        if cohere_api_key:
            st.markdown("---")
            st.subheader("💬 Ask Grounded Questions About Your Data")
            user_query = st.text_input("Enter your question (e.g., 'What are the top categories by total volume?')")
            if st.button("💬 Ask Data Assistant"):
                if user_query.strip():
                    with st.spinner("Consulting Cohere Data Assistant..."):
                        answer = engine.ask_cohere_assistant(api_key=cohere_api_key, selected_model=selected_model, user_query=user_query)
                        st.session_state["last_answer"] = answer

            if "last_answer" in st.session_state:
                st.info(f"**Cohere AI Response:**\n\n{st.session_state['last_answer']}")

if __name__ == "__main__":
    main()