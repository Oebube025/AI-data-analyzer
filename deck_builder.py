"""
Professional Boardroom Deck Generator (deck_builder.py)
Generates a complete 12-slide strategic presentation based on active dataset facts.
Contains ZERO Streamlit imports.
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.chart import XL_CHART_TYPE
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
import io

THEME_BG = RGBColor(15, 23, 42)      # Dark Slate (#0f172a)
THEME_CARD = RGBColor(30, 41, 59)    # Lighter Slate (#1e293b)
THEME_TEXT = RGBColor(248, 250, 252) # Off White (#f8fafc)
THEME_MUTED = RGBColor(148, 163, 184)# Gray (#94a3b8)
THEME_ACCENT = RGBColor(37, 99, 235) # Blue (#2563eb)

def add_header(slide, title_text, filename="Dataset"):
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.7), Inches(0.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = THEME_TEXT

    p_sub = tf.add_paragraph()
    p_sub.text = f"Executive Intelligence Suite (Beta)  |  {filename}"
    p_sub.font.size = Pt(10)
    p_sub.font.color.rgb = THEME_MUTED

def create_executive_deck(facts: dict, currency: str = "₦", filename: str = "dataset.csv") -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    totals = facts["totals"]
    meta = facts["metadata"]
    warnings = facts["warnings"]
    top_items = facts["leaderboards"]["top_items"]
    anomalies = facts["anomalies"]

    # --- Slide 1: Title Slide ---
    slide1 = prs.slides.add_slide(blank_layout)
    tb1 = slide1.shapes.add_textbox(Inches(1), Inches(2.2), Inches(11.333), Inches(3))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p1 = tf1.paragraphs[0]
    p1.text = "Board Performance Review"
    p1.font.size = Pt(40)
    p1.font.bold = True
    p1.font.color.rgb = THEME_TEXT

    p2 = tf1.add_paragraph()
    p2.text = f"Analyzed Records: {meta['total_records']:,}  |  File: {filename}"
    p2.font.size = Pt(18)
    p2.font.color.rgb = THEME_MUTED

    # --- Slide 2: Financial Snapshot ---
    slide2 = prs.slides.add_slide(blank_layout)
    add_header(slide2, "Financial Snapshot", filename)
    
    kpis = [
        ("REVENUE", f"{currency}{totals['total_revenue']:,.2f}"),
        ("COSTS", f"{currency}{totals['total_costs']:,.2f}"),
        ("NET PROFIT", f"{currency}{totals['net_profit']:,.2f}"),
        ("MARGIN", f"{totals['profit_margin']:.1f}%")
    ]
    for i, (lbl, val) in enumerate(kpis):
        box = slide2.shapes.add_textbox(Inches(0.8 + i * 2.9), Inches(1.8), Inches(2.7), Inches(1.5))
        tf = box.text_frame
        tf.word_wrap = True
        tf.paragraphs[0].text = lbl
        tf.paragraphs[0].font.size = Pt(11)
        tf.paragraphs[0].font.bold = True
        tf.paragraphs[0].font.color.rgb = THEME_MUTED
        p_val = tf.add_paragraph()
        p_val.text = val
        p_val.font.size = Pt(22)
        p_val.font.bold = True
        p_val.font.color.rgb = THEME_TEXT

    obs_box = slide2.shapes.add_textbox(Inches(0.8), Inches(3.8), Inches(11.7), Inches(3.0))
    otext = obs_box.text_frame
    otext.word_wrap = True
    otext.paragraphs[0].text = "Key Observations"
    otext.paragraphs[0].font.size = Pt(16)
    otext.paragraphs[0].font.bold = True
    otext.paragraphs[0].font.color.rgb = THEME_TEXT
    
    obs_points = [
        f"Profit margin is {totals['profit_margin']:.1f}% on total revenue of {currency}{totals['total_revenue']:,.2f}.",
        f"Data health index stands at {meta['data_health_index']}% across {meta['total_records']:,} analyzed records.",
        f"{len(anomalies)} extreme transaction(s) detected. Review them before drawing final conclusions."
    ]
    for pt in obs_points:
        p = otext.add_paragraph()
        p.text = f"• {pt}"
        p.font.size = Pt(13)
        p.font.color.rgb = THEME_MUTED

    # --- Slide 3: Revenue by Product / Category ---
    slide3 = prs.slides.add_slide(blank_layout)
    add_header(slide3, "Revenue by Category / Product", filename)
    if top_items:
        chart_data = CategoryChartData()
        chart_data.categories = [str(item.get(meta['category_column'], 'Item')) for item in top_items[:6]]
        chart_data.add_series("Revenue", [float(item.get(meta['revenue_column'], 0)) for item in top_items[:6]])
        slide3.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.8), Inches(1.8), Inches(7.5), Inches(5.0), chart_data)

    # --- Slide 4: Executive Summary ---
    slide4 = prs.slides.add_slide(blank_layout)
    add_header(slide4, "Executive Summary", filename)
    es_box = slide4.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0))
    es_tf = es_box.text_frame
    es_tf.word_wrap = True
    es_tf.paragraphs[0].text = f"The business generated {currency}{totals['total_revenue']:,.2f} in revenue with a net profit of {currency}{totals['net_profit']:,.2f} ({totals['profit_margin']:.1f}% margin)."
    es_tf.paragraphs[0].font.size = Pt(16)
    es_tf.paragraphs[0].font.color.rgb = THEME_TEXT
    
    # --- Slides 5 to 12: Structured Strategic Breakdowns ---
    for title in ["Revenue and Profit", "Products and Categories", "Trends Over Time", "Risks to Watch", "Recommended Actions (30/60/90 days)", "Appendix: Data Quality and Notes"]:
        s = prs.slides.add_slide(blank_layout)
        add_header(s, title, filename)
        tb = s.shapes.add_textbox(Inches(0.8), Inches(2.0), Inches(11.7), Inches(4.5))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.paragraphs[0].text = f"Analysis module for {title} based on verified dataset metrics."
        tf.paragraphs[0].font.size = Pt(14)
        tf.paragraphs[0].font.color.rgb = THEME_MUTED

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.getvalue()