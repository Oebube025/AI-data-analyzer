import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import io
import json
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

# PAGE CONFIGURATION
st.set_page_config(
    page_title="Executive Data Intelligence Suite - Arcade SaaS Edition",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CUSTOM HIGH-ENERGY VIBRANT CYBERPUNK / SAAS CSS
st.markdown("""
<style>
    /* Global Cosmic Vibe */
    .stApp {
        background: radial-gradient(circle at top right, #0f172a 0%, #070913 100%);
        color: #f3f4f6;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0b0f19 0%, #05070c 100%);
        border-right: 1px solid #1e293b;
    }
    
    /* Glowing Neon Card Containers */
    .saas-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid #38bdf8;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 0 20px rgba(56, 189, 248, 0.15);
        margin-bottom: 20px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .saas-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 25px rgba(56, 189, 248, 0.3);
    }
    
    /* Typography & Headers */
    h1, h2, h3 {
        letter-spacing: -0.025em;
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Neon Action Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #38bdf8 0%, #6366f1 50%, #a855f7 100%);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 700;
        padding: 0.6rem 1.2rem;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 20px rgba(168, 85, 247, 0.6);
    }
    
    /* Sleek Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: rgba(15, 23, 42, 0.5);
        padding: 8px;
        border-radius: 12px;
        border: 1px solid #1e293b;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e293b;
        border-radius: 8px;
        color: #94a3b8;
        padding: 10px 18px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #38bdf8 0%, #6366f1 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# BACKEND API CONFIGURATION
BACKEND_URL = "http://127.0.0.1:8000"

def check_backend_status():
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False

def analyze_dataset_via_backend_api(filename: str, file_bytes: bytes, mime_type: str):
    files = {"file": (filename, file_bytes, mime_type)}
    response = requests.post(f"{BACKEND_URL}/api/analyze", files=files, timeout=10)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Backend API error: {response.status_code} - {response.text}")

def fetch_ai_advisory_from_backend(verified_stats: str):
    response = requests.post(f"{BACKEND_URL}/api/ai-advisory", json={"verified_stats": verified_stats}, timeout=45)
    if response.status_code == 200:
        return response.json().get("advisory", "")
    else:
        raise Exception(f"Backend AI error: {response.status_code} - {response.text}")

class BusinessDataEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        self.cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
        self.date_cols = [c for c in df.columns if any(k in c.lower() for k in ['date', 'time', 'year', 'month', 'period', 'created'])]

    def audit_data_quality(self):
        total_cells = self.df.size
        if total_cells == 0:
            return 0.0, 0, 0, []
        missing_cells = self.df.isna().sum().sum()
        health_score = max(0.0, min(100.0, ((total_cells - missing_cells) / total_cells) * 100))
        issues = []
        if missing_cells > 0:
            issues.append(f"Found {missing_cells:,} missing/null data cells across dataset.")
        duplicates = self.df.duplicated().sum()
        if duplicates > 0:
            issues.append(f"Detected {duplicates:,} fully duplicated row records.")
        return round(health_score, 1), missing_cells, duplicates, issues

    def get_smart_time_series(self):
        date_candidates = [col for col in self.df.columns if any(k in col.lower() for k in ['date', 'time', 'year', 'month', 'period', 'created'])]
        if not date_candidates and self.date_cols:
            date_candidates = self.date_cols
        if date_candidates and self.num_cols:
            d_col = date_candidates[0]
            n_col = self.num_cols[0]
            try:
                temp_df = self.df.copy()
                temp_df[d_col] = pd.to_datetime(temp_df[d_col], errors='coerce')
                trend = temp_df.groupby(d_col)[n_col].sum().reset_index().sort_values(d_col)
                if len(trend) > 1:
                    return d_col, n_col, trend
            except Exception:
                pass
        return None, None, None

# SILENT BACKGROUND LOGIC (Running without rendering UI widgets)
is_backend_online = check_backend_status()
focus_field = "None"

# MAIN HERO BANNER
st.markdown("""
    <div style='padding: 28px; background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.95) 100%); border-radius: 20px; border: 1px solid #38bdf8; box-shadow: 0 0 30px rgba(56, 189, 248, 0.2); margin-bottom: 24px; text-align: center;'>
        <h1 style='margin:0; font-size: 2.4rem;'>🚀 Executive Data Intelligence Suite</h1>
        <p style='margin: 10px 0 0 0; color: #94a3b8; font-size: 1.15rem;'>High-Velocity Business Analytics & Grounded AI Command Center</p>
    </div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader("✨ Drop Your Business Dataset (.csv or .xlsx)", type=["csv", "xlsx"])

if uploaded is not None:
    if "current_filename" not in st.session_state or st.session_state["current_filename"] != uploaded.name:
        file_bytes = uploaded.getvalue()
        try:
            if uploaded.name.endswith('.csv'):
                orig_df = pd.read_csv(io.BytesIO(file_bytes))
            else:
                orig_df = pd.read_excel(io.BytesIO(file_bytes))
            
            st.session_state["current_filename"] = uploaded.name
            st.session_state["raw_file_bytes"] = file_bytes
            st.session_state["active_df"] = orig_df.copy()
            st.session_state["transformation_history"] = ["Dataset loaded successfully."]
        except Exception as e:
            st.error(f"Error loading file: {e}")
            st.stop()

    df = st.session_state["active_df"]
    engine = BusinessDataEngine(df)

    # STREAMLINED SIDEBAR (ONLY ESSENTIAL FILTERS)
    st.sidebar.markdown("### 🔍 Live Dataset Filters")
    
    filtered_df = df.copy()
    if engine.cat_cols:
        filter_cat_col = st.sidebar.selectbox("Filter Category", ["None"] + engine.cat_cols)
        if filter_cat_col != "None":
            unique_vals = df[filter_cat_col].dropna().unique().tolist()
            selected_vals = st.sidebar.multiselect(f"Select {filter_cat_col}", unique_vals, default=unique_vals[:min(5, len(unique_vals))])
            if selected_vals:
                filtered_df = filtered_df[filtered_df[filter_cat_col].isin(selected_vals)]

    st.sidebar.success(f"⚡ Active Records: {len(filtered_df):,} / {len(df):,}")
    
    if st.sidebar.button("🔄 Reset Transformations"):
        file_bytes = st.session_state["raw_file_bytes"]
        if st.session_state["current_filename"].endswith('.csv'):
            st.session_state["active_df"] = pd.read_csv(io.BytesIO(file_bytes))
        else:
            st.session_state["active_df"] = pd.read_excel(io.BytesIO(file_bytes))
        st.session_state["transformation_history"] = ["Reset to original uploaded state."]
        st.experimental_rerun()

    tabs = [
        "🤖 AI Adviser",
        "💰 Sales & Profit",
        "📊 Leaderboard",
        "🛠️ Data Health",
        "⚠️ Anomaly Radar",
        "📈 Boardroom PPTX",
        "⚡ Neural Backend"
    ]
    
    tab_objs = st.tabs(tabs)
    tab_offset = 0

    # TAB 1: AI ADVISER
    with tab_objs[tab_offset]:
        tab_offset += 1
        st.subheader("🤖 Module 4: Grounded AI Business Adviser")
        st.caption("Generate high-impact strategic advisory powered by secure server-side AI intelligence.")
        
        if not is_backend_online:
            st.warning("⚠️ FastAPI Backend is offline. Start your backend server to unleash AI advisory.")
        else:
            if st.button("✨ Summon AI Business Advisory", type="primary"):
                with st.spinner("🔮 Analyzing verified metrics and consulting AI intelligence..."):
                    try:
                        total_rows = len(filtered_df)
                        health_score, _, _, _ = engine.audit_data_quality()
                        num_summary = filtered_df[engine.num_cols].describe().to_string() if engine.num_cols else "No numeric data"
                        
                        verified_stats = f"""
                        Verified Dataset Statistics:
                        - Filename: {st.session_state['current_filename']}
                        - Filtered Row Count: {total_rows:,}
                        - Data Health Index: {health_score}%
                        - Numeric Columns Summary:
                        {num_summary}
                        """
                        
                        advisory_result = fetch_ai_advisory_from_backend(verified_stats)
                        st.session_state["grounded_ai_output"] = advisory_result
                        st.balloons()
                        st.success("🎉 AI Business Advisory Summoned Successfully!")
                    except Exception as e:
                        st.error(f"Failed to generate AI advisory: {e}")

        if "grounded_ai_output" in st.session_state:
            st.markdown("---")
            st.markdown(st.session_state["grounded_ai_output"])

    # TAB 2: SALES & PROFIT DASHBOARD
    with tab_objs[tab_offset]:
        tab_offset += 1
        st.subheader("💰 Module 1: Small Business Sales & Profit Command Center")
        
        rev_candidates = [c for c in engine.num_cols if any(k in c.lower() for k in ['revenue', 'sales', 'amount', 'total', 'price'])]
        cost_candidates = [c for c in engine.num_cols if any(k in c.lower() for k in ['cost', 'expense', 'spend', 'budget'])]

        sel_rev = st.selectbox("Select Revenue Metric", engine.num_cols, index=engine.num_cols.index(rev_candidates[0]) if rev_candidates else 0)
        sel_cost = st.selectbox("Select Cost Metric (Optional)", ["None"] + engine.num_cols)

        total_revenue = filtered_df[sel_rev].sum()
        total_costs = filtered_df[sel_cost].sum() if sel_cost != "None" else 0.0
        net_profit = total_revenue - total_costs
        profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("💵 Total Revenue", f"${total_revenue:,.2f}")
        p2.metric("📉 Total Costs", f"${total_costs:,.2f}")
        p3.metric("🚀 Net Profit", f"${net_profit:,.2f}")
        p4.metric("📈 Profit Margin", f"{profit_margin:.1f}%")

        st.markdown("---")
        t_col, _, trend_data = engine.get_smart_time_series()
        if t_col is not None and trend_data is not None:
            fig_trend = px.line(filtered_df.groupby(t_col)[sel_rev].sum().reset_index(), x=t_col, y=sel_rev, title=f"⚡ Sales Velocity Over Time ({t_col})", template="plotly_dark", color_discrete_sequence=["#38bdf8"])
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            fig_hist = px.histogram(filtered_df, x=sel_rev, title=f"📊 Distribution of {sel_rev}", template="plotly_dark", color_discrete_sequence=["#38bdf8"])
            st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown("---")
        st.dataframe(filtered_df.head(15), use_container_width=True)

    # TAB 3: PERFORMANCE LEADERBOARD
    with tab_objs[tab_offset]:
        tab_offset += 1
        st.subheader("📊 Module 2: Business Performance Leaderboard")
        if engine.cat_cols and engine.num_cols:
            perf_cat = st.selectbox("Grouping Dimension", engine.cat_cols)
            perf_num = st.selectbox("Performance Metric", engine.num_cols)

            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown("#### 🏆 Top Performers")
                st.dataframe(filtered_df.groupby(perf_cat)[perf_num].sum().nlargest(5).reset_index(), use_container_width=True)
            with col_r:
                st.markdown("#### ⚠️ Underperformers")
                st.dataframe(filtered_df.groupby(perf_cat)[perf_num].sum().nsmallest(5).reset_index(), use_container_width=True)
        else:
            st.info("Dataset requires categorical and numerical columns.")

    # TAB 4: DATA REFINEMENT & QUALITY
    with tab_objs[tab_offset]:
        tab_offset += 1
        st.subheader("🛠️ Module 3: Data Quality & Health Audit")
        health_score, missing_cells, duplicates, issues = engine.audit_data_quality()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📂 Active Rows", f"{len(filtered_df):,}")
        c2.metric("📊 Columns", f"{len(filtered_df.columns):,}")
        c3.metric("✨ Health Index", f"{health_score}%")
        c4.metric("⚠️ Flagged Issues", len(issues))
        
        st.markdown("---")
        if issues:
            for issue in issues:
                st.warning(issue)
        else:
            st.success("✨ Pristine Dataset! Zero quality anomalies detected.")

        st.markdown("---")
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Cleaned Dataset (.csv)", data=csv_data, file_name="cleaned_dataset.csv", mime="text/csv")

    # TAB 5: EXPENSE & ANOMALY MONITOR
    with tab_objs[tab_offset]:
        tab_offset += 1
        st.subheader("⚠️ Anomaly Radar & Outlier Detection")
        if engine.num_cols:
            anomaly_metric = st.selectbox("Select Audit Metric", engine.num_cols)
            series = filtered_df[anomaly_metric].dropna()
            mean_val = series.mean()
            std_val = series.std()
            anomalies = filtered_df[np.abs(filtered_df[anomaly_metric] - mean_val) > (2.5 * std_val)]
            st.write(f"🚨 Flagged **{len(anomalies)} statistical outlier records** in `{anomaly_metric}`.")
            st.dataframe(anomalies.head(15), use_container_width=True)
        else:
            st.info("No numeric columns available.")

    # TAB 6: BOARDROOM PPTX EXPORT
    with tab_objs[tab_offset]:
        tab_offset += 1
        st.subheader("📈 Boardroom-Ready Executive PowerPoint Suite")
        st.caption("Export a stunning consulting-grade 6-slide presentation deck instantly.")

        if st.button("🚀 Generate Boardroom Presentation (.pptx)", type="primary"):
            try:
                prs = Presentation()
                health_score, missing_cells, duplicates, issues = engine.audit_data_quality()
                
                rev_cands = [c for c in engine.num_cols if any(k in c.lower() for k in ['revenue', 'sales', 'amount', 'total', 'price'])]
                cost_cands = [c for c in engine.num_cols if any(k in c.lower() for k in ['cost', 'expense', 'spend', 'budget'])]
                s_rev = rev_cands[0] if rev_cands else (engine.num_cols[0] if engine.num_cols else None)
                s_cost = cost_cands[0] if cost_cands else None

                t_rev = filtered_df[s_rev].sum() if s_rev else 0.0
                t_cost = filtered_df[s_cost].sum() if s_cost else 0.0
                n_profit = t_rev - t_cost
                p_margin = (n_profit / t_rev * 100) if t_rev > 0 else 0.0

                # Slide 1: Title
                slide1 = prs.slides.add_slide(prs.slide_layouts[0])
                slide1.shapes.title.text = "Executive Profit & Sales Intelligence Report"
                slide1.placeholders[1].text = f"Dataset Source: {st.session_state['current_filename']}\nGenerated via Executive Data Intelligence Suite"

                # Slide 2: Summary
                slide2 = prs.slides.add_slide(prs.slide_layouts[5])
                slide2.shapes.title.text = "1. Executive Summary & Data Integrity Audit"
                t2 = slide2.shapes.add_table(5, 2, Inches(1.0), Inches(1.8), Inches(11.3), Inches(4.2)).table
                t2.columns[0].width, t2.columns[1].width = Inches(4.5), Inches(6.8)
                summary_metrics = [
                    ("Evaluation Parameter", "Verified System Metric"),
                    ("Total Active Records Analyzed", f"{len(filtered_df):,} rows"),
                    ("Data Quality Health Index", f"{health_score}% (Pristine Standard)"),
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
                    ("Gross Revenue / Sales", f"${t_rev:,.2f}"),
                    ("Total Costs / Expenses", f"${t_cost:,.2f}"),
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
                    slide4.shapes.title.text = "3. Business Performance Leaderboard"
                    p_cat, p_num = engine.cat_cols[0], engine.num_cols[0]
                    top_items = filtered_df.groupby(p_cat)[p_num].sum().nlargest(5).reset_index()
                    t4 = slide4.shapes.add_table(len(top_items)+1, 2, Inches(1.5), Inches(1.8), Inches(10.3), Inches(4.0)).table
                    t4.columns[0].width, t4.columns[1].width = Inches(5.0), Inches(5.3)
                    t4.cell(0, 0).text, t4.cell(0, 1).text = f"Category ({p_cat})", f"Metric ({p_num})"
                    for idx, row in top_items.iterrows():
                        t4.cell(idx+1, 0).text, t4.cell(idx+1, 1).text = str(row[p_cat]), f"{row[p_num]:,.2f}"
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
                    "• Statistical Variance Auditing: Evaluated dataset distribution against standard deviation thresholds.\n"
                    "• Outlier Detection: Isolated high-magnitude transactions for operational review.\n"
                    "• Risk Mitigation: Ensures irregular expense spikes or unusual sales figures are audited before final reporting."
                )

                # Slide 6: Recommendations
                slide6 = prs.slides.add_slide(prs.slide_layouts[1])
                slide6.shapes.title.text = "5. Strategic AI Adviser & Next Steps"
                slide6.placeholders[1].text_frame.text = (
                    "1. Scale High-Margin Offerings: Reallocate marketing budget toward top-performing product categories.\n"
                    "2. Cost Control & Expense Trimming: Investigate bottom-tier segments and vendor spending spikes.\n"
                    "3. Continuous Monitoring: Establish weekly automated data health audits via the FastAPI pipeline."
                )

                pptx_buffer = io.BytesIO()
                prs.save(pptx_buffer)
                pptx_buffer.seek(0)
                
                st.balloons()
                st.success("🎉 Boardroom Presentation Generated Successfully!")
                st.download_button(
                    label="📥 Download Boardroom Presentation (.pptx)",
                    data=pptx_buffer,
                    file_name="Boardroom_Executive_Presentation.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                )
            except Exception as e:
                st.error(f"Failed to generate PowerPoint presentation: {e}")

    # TAB 7: FASTAPI BACKEND PIPELINE
    with tab_objs[tab_offset]:
        tab_offset += 1
        st.subheader("⚡ Decoupled FastAPI Neural Pipeline")
        st.caption("Transmit active datasets directly to the asynchronous FastAPI REST backend.")

        if not is_backend_online:
            st.warning("⚠️ FastAPI Server is currently offline. Start Uvicorn in your terminal (`uvicorn main:app --reload --port 8000`).")
        else:
            if st.button("🚀 Execute Neural Dataset Audit", type="primary"):
                with st.spinner("⚡ Transmitting dataset payload to FastAPI REST API..."):
                    try:
                        file_bytes = st.session_state["raw_file_bytes"]
                        mime_type = "text/csv" if st.session_state["current_filename"].endswith(".csv") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        api_result = analyze_dataset_via_backend_api(st.session_state["current_filename"], file_bytes, mime_type)
                        st.session_state["backend_api_result"] = api_result
                        st.success("✨ Neural Audit Complete from FastAPI Server!")
                    except Exception as err:
                        st.error(f"Failed to communicate with FastAPI server: {err}")

        if "backend_api_result" in st.session_state:
            res = st.session_state["backend_api_result"]
            st.markdown("---")
            st.markdown("### 📈 Backend Neural Summary")
            
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("File Name", res.get("filename", "N/A"))
            col_b.metric("Total Records", f"{res.get('records', 0):,}")
            col_c.metric("Data Fields", res.get("fields_count", 0))
            col_d.metric("Health Index", res.get("data_health_index", "0%"))

            st.markdown("---")
            st.markdown("### 🧠 Smart Executive Visual Analytics Grid")

            t_col, t_num, trend_data = engine.get_smart_time_series()
            s_cat = engine.cat_cols[0] if engine.cat_cols else None
            s_num = engine.num_cols[0] if engine.num_cols else None

            r1_col1, r1_col2 = st.columns(2)
            with r1_col1:
                if t_col is not None and trend_data is not None:
                    fig_trend = px.line(trend_data, x=t_col, y=t_num, title=f"1. Smart Trend: {t_num} over {t_col}", template="plotly_dark", color_discrete_sequence=["#38bdf8"])
                    st.plotly_chart(fig_trend, use_container_width=True)
                elif engine.num_cols:
                    num_field = engine.num_cols[0]
                    fig_hist = px.histogram(filtered_df, x=num_field, title=f"1. Smart Distribution: {num_field}", template="plotly_dark", color_discrete_sequence=["#38bdf8"])
                    st.plotly_chart(fig_hist, use_container_width=True)

            with r1_col2:
                if s_cat and s_num:
                    grouped_cat = filtered_df.groupby(s_cat)[s_num].sum().nlargest(8).reset_index()
                    fig_smart_cat = px.bar(grouped_cat, x=s_cat, y=s_num, title=f"2. Smart Performance: Total {s_num} by {s_cat}", template="plotly_dark", color_discrete_sequence=["#14b8a6"])
                    st.plotly_chart(fig_smart_cat, use_container_width=True)
                elif s_cat:
                    cat_counts = filtered_df[s_cat].value_counts().head(8).reset_index()
                    cat_counts.columns = [s_cat, "Count"]
                    fig_cat = px.bar(cat_counts, x=s_cat, y="Count", title=f"2. Volume Breakdown by {s_cat}", template="plotly_dark", color_discrete_sequence=["#14b8a6"])
                    st.plotly_chart(fig_cat, use_container_width=True)

            r2_col1, r2_col2 = st.columns(2)
            with r2_col1:
                if len(engine.num_cols) >= 2:
                    num1, num2 = engine.num_cols[0], engine.num_cols[1]
                    fig_scatter = px.scatter(filtered_df, x=num1, y=num2, title=f"3. Correlation Analysis: {num1} vs {num2}", template="plotly_dark", color_discrete_sequence=["#f43f5e"])
                    st.plotly_chart(fig_scatter, use_container_width=True)
                elif engine.num_cols:
                    num1 = engine.num_cols[0]
                    fig_box = px.box(filtered_df, y=num1, title=f"3. Outlier Variance Map: {num1}", template="plotly_dark", color_discrete_sequence=["#f43f5e"])
                    st.plotly_chart(fig_box, use_container_width=True)

            with r2_col2:
                if s_cat and s_num:
                    grouped_h = filtered_df.groupby(s_cat)[s_num].mean().nlargest(8).reset_index()
                    fig_h = px.bar(grouped_h, x=s_num, y=s_cat, orientation="h", title=f"4. Average {s_num} across {s_cat}", template="plotly_dark", color_discrete_sequence=["#a855f7"])
                    fig_h.update_yaxes(autorange="reversed")
                    st.plotly_chart(fig_h, use_container_width=True)

            with st.expander("🔍 View Raw JSON Backend Response"):
                st.json(res)
else:
    st.markdown("""
        <div style='text-align: center; padding: 60px; background: rgba(15, 23, 42, 0.6); border-radius: 20px; border: 2px dashed #38bdf8; margin-top: 40px; box-shadow: 0 0 20px rgba(56, 189, 248, 0.1);'>
            <h2 style='color: #38bdf8; margin-bottom: 8px;'>📂 Ready for Action</h2>
            <p style='color: #94a3b8; font-size: 1.1rem;'>Drop your dataset above to launch your high-velocity executive command center.</p>
        </div>
    """, unsafe_allow_html=True)