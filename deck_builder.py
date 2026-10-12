"""
Professional Boardroom Deck Generator (deck_builder.py)
Multi-slide PowerPoint generation with native charts and category breakdowns.
Contains ZERO Streamlit imports.
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.chart import XL_CHART_TYPE
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
import io

THEME_BG = RGBColor(15, 23, 42)
THEME_CARD = RGBColor(30, 41, 59)
THEME_TEXT = RGBColor(248, 250, 252)
THEME_MUTED = RGBColor(148, 163, 184)
THEME_ACCENT = RGBColor(37, 99, 235)

def create_executive_deck(facts: dict, currency: str = "₦") -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # --- Slide 1: Title Slide ---
    slide1 = prs.slides.add_slide(blank_layout)
    title_box = slide1.shapes.add_textbox(Inches(1), Inches(2.2), Inches(11.333), Inches(3))
    tf1 = title_box.text_frame
    tf1.word_wrap = True
    p1 = tf1.paragraphs[0]
    p1.text = "Executive Financial Intelligence Report"
    p1.font.size = Pt(40)
    p1.font.bold = True
    p1.font.color.rgb = THEME_TEXT

    p2 = tf1.add_paragraph()
    totals = facts["totals"]
    meta = facts["metadata"]
    p2.text = f"Analyzed Records: {meta['total_records']:,}  |  Data Health Index: {meta['data_health_index']}%"
    p2.font.size = Pt(18)
    p2.font.color.rgb = THEME_MUTED

    # --- Slide 2: KPI Summary Cards ---
    slide2 = prs.slides.add_slide(blank_layout)
    tb2 = slide2.shapes.add_textbox(Inches(1), Inches(0.8), Inches(11.333), Inches(1))
    tf2 = tb2.text_frame
    tp2 = tf2.paragraphs[0]
    tp2.text = "Key Financial Performance Indicators"
    tp2.font.size = Pt(28)
    tp2.font.bold = True
    tp2.font.color.rgb = THEME_TEXT

    kpi_data = [
        ("Total Revenue", f"{currency}{totals['total_revenue']:,.2f}"),
        ("Total Costs", f"{currency}{totals['total_costs']:,.2f}"),
        ("Net Profit", f"{currency}{totals['net_profit']:,.2f}"),
        ("Profit Margin", f"{totals['profit_margin']:.1f}%")
    ]

    card_width = Inches(2.5)
    card_gap = Inches(0.4)
    start_left = Inches(1)
    for i, (label, val) in enumerate(kpi_data):
        left = start_left + i * (card_width + card_gap)
        box = slide2.shapes.add_textbox(left, Inches(2.5), card_width, Inches(3))
        tf = box.text_frame
        tf.word_wrap = True
        
        p_lbl = tf.paragraphs[0]
        p_lbl.text = label.upper()
        p_lbl.font.size = Pt(12)
        p_lbl.font.bold = True
        p_lbl.font.color.rgb = THEME_MUTED

        p_val = tf.add_paragraph()
        p_val.text = val
        p_val.font.size = Pt(24)
        p_val.font.bold = True
        p_val.font.color.rgb = THEME_TEXT

    # --- Slide 3: Financial Overview Chart ---
    slide3 = prs.slides.add_slide(blank_layout)
    tb3 = slide3.shapes.add_textbox(Inches(1), Inches(0.6), Inches(11.333), Inches(0.8))
    tf3 = tb3.text_frame
    tp3 = tf3.paragraphs[0]
    tp3.text = "Financial Overview & Distribution"
    tp3.font.size = Pt(26)
    tp3.font.bold = True
    tp3.font.color.rgb = THEME_TEXT

    chart_data = CategoryChartData()
    chart_data.categories = ["Revenue", "Costs", "Net Profit"]
    chart_data.add_series("Financials", (totals["total_revenue"], totals["total_costs"], totals["net_profit"]))
    slide3.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1), Inches(1.8), Inches(11.333), Inches(5), chart_data)

    # --- Slide 4: Category Breakdown Chart (If available) ---
    rev_cat = facts.get("revenue_by_category", {})
    if rev_cat:
        slide4 = prs.slides.add_slide(blank_layout)
        tb4 = slide4.shapes.add_textbox(Inches(1), Inches(0.6), Inches(11.333), Inches(0.8))
        tf4 = tb4.text_frame
        tp4 = tf4.paragraphs[0]
        tp4.text = f"Top {meta.get('category_column', 'Category')} Breakdown by Revenue"
        tp4.font.size = Pt(26)
        tp4.font.bold = True
        tp4.font.color.rgb = THEME_TEXT

        cat_chart_data = CategoryChartData()
        top_cats = list(rev_cat.items())[:8] # Take top 8
        cat_chart_data.categories = [str(k) for k, v in top_cats]
        cat_chart_data.add_series("Revenue", [float(v) for k, v in top_cats])
        slide4.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(1), Inches(1.8), Inches(11.333), Inches(5), cat_chart_data)

    # --- Slide 5: Data Quality & Warnings Appendix ---
    slide5 = prs.slides.add_slide(blank_layout)
    tb5 = slide5.shapes.add_textbox(Inches(1), Inches(0.8), Inches(11.333), Inches(1))
    tf5 = tb5.text_frame
    tp5 = tf5.paragraphs[0]
    tp5.text = "Data Quality Audit & Notes"
    tp5.font.size = Pt(26)
    tp5.font.bold = True
    tp5.font.color.rgb = THEME_TEXT

    notes_box = slide5.shapes.add_textbox(Inches(1), Inches(2.0), Inches(11.333), Inches(4.5))
    ntf = notes_box.text_frame
    ntf.word_wrap = True
    
    warnings = facts["warnings"]
    audit_text = f"• Data Health Index: {meta['data_health_index']}%\n• Missing Cells: {meta['missing_cells']:,}\n• Duplicate Rows: {meta['duplicate_rows']:,}\n"
    if warnings:
        audit_text += "\nWarnings Detected:\n" + "\n".join([f"• {w}" for w in warnings])
    else:
        audit_text += "\nNo structural warnings detected in the dataset."
    
    ntf.text = audit_text

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.getvalue()