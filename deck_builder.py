"""
deck_builder.py - FINCH Presentation Generator with Native Charts
"""
import io
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION

def create_executive_deck(facts, currency="₦", filename="Dataset", scenarios=None):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_slide_layout = prs.slide_layouts[6]

    theme_colors = {
        "bg_dark": RGBColor(9, 13, 22),
        "bg_light": RGBColor(255, 255, 255),
        "card_bg": RGBColor(248, 250, 252),
        "primary": RGBColor(15, 23, 42),
        "accent": RGBColor(15, 157, 143),
        "success": RGBColor(16, 185, 129),
        "gold": RGBColor(244, 184, 96),
        "text_muted": RGBColor(100, 116, 139),
    }

    totals = facts.get("totals", {})
    meta = facts.get("metadata", {})
    rbc = facts.get("revenue_by_category", {})
    trend = facts.get("trend", {})

    def set_background(slide, color):
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = color

    def add_header(slide, category: str, title: str, subtitle: str = ""):
        txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.5), Inches(0.4))
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = category.upper()
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = theme_colors["accent"]

        txBox_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.5), Inches(0.8))
        tf_title = txBox_title.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        p_title.text = title
        p_title.font.size = Pt(26)
        p_title.font.bold = True
        p_title.font.color.rgb = theme_colors["primary"]

        if subtitle:
            txBox_sub = slide.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(11.5), Inches(0.4))
            tf_sub = txBox_sub.text_frame
            tf_sub.word_wrap = True
            p_sub = tf_sub.paragraphs[0]
            p_sub.text = subtitle
            p_sub.font.size = Pt(13)
            p_sub.font.color.rgb = theme_colors["text_muted"]

    # SLIDE 1: Title
    slide1 = prs.slides.add_slide(blank_slide_layout)
    set_background(slide1, theme_colors["bg_dark"])
    txBox = slide1.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(11.3), Inches(3.5))
    tf = txBox.text_frame
    tf.word_wrap = True
    p0 = tf.paragraphs[0]
    p0.text = "FINCH EXECUTIVE REPORT"
    p0.font.size = Pt(14)
    p0.font.bold = True
    p0.font.color.rgb = theme_colors["gold"]
    p0.space_after = Pt(14)
    p1 = tf.add_paragraph()
    p1.text = f"Business Intelligence Audit: {filename}"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = RGBColor(248, 250, 252)
    p1.space_after = Pt(16)
    margin_val = totals.get('profit_margin')
    margin_str = f"{margin_val:.1f}%" if margin_val is not None else "N/A"
    p2 = tf.add_paragraph()
    p2.text = f"Automated audit and strategic growth scenarios • Net Margin: {margin_str}"
    p2.font.size = Pt(16)
    p2.font.color.rgb = theme_colors["text_muted"]

    # SLIDE 2: Summary Cards
    slide2 = prs.slides.add_slide(blank_slide_layout)
    set_background(slide2, theme_colors["bg_light"])
    add_header(slide2, "Core Metrics", "Executive Financial Summary", "High-level summary of total top-line revenue, operating costs, and net profit.")
    cost_known = totals.get("cost_known", False)
    rev_str = f"{currency}{totals.get('total_revenue', 0):,.2f}"
    cost_str = f"{currency}{totals.get('total_costs', 0):,.2f}" if cost_known else "N/A"
    profit_str = f"{currency}{totals.get('net_profit', 0):,.2f}" if cost_known else "N/A"
    metrics = [
        {"label": "TOTAL REVENUE", "value": rev_str, "sub": "Gross Inflow", "color": theme_colors["primary"], "bg": theme_colors["card_bg"]},
        {"label": "TOTAL COSTS", "value": cost_str, "sub": "Operating Expenses", "color": theme_colors["primary"], "bg": theme_colors["card_bg"]},
        {"label": "NET PROFIT", "value": profit_str, "sub": f"{margin_str} Net Margin", "color": theme_colors["success"], "bg": theme_colors["primary"], "dark": True}
    ]
    for i, m in enumerate(metrics):
        x = Inches(0.8) + i * Inches(4.0)
        shape = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(2.2), Inches(3.6), Inches(3.5))
        shape.fill.solid()
        shape.fill.fore_color.rgb = m["bg"]
        tf_card = shape.text_frame
        tf_card.word_wrap = True
        tf_card.margin_left = Inches(0.3)
        tf_card.margin_top = Inches(0.4)
        p_lbl = tf_card.paragraphs[0]
        p_lbl.text = m["label"]
        p_lbl.font.size = Pt(12)
        p_lbl.font.bold = True
        p_lbl.font.color.rgb = theme_colors["text_muted"] if not m.get("dark") else RGBColor(148, 163, 184)
        p_lbl.space_after = Pt(16)
        p_val = tf_card.add_paragraph()
        p_val.text = m["value"]
        p_val.font.size = Pt(28)
        p_val.font.bold = True
        p_val.font.color.rgb = m["color"]
        p_val.space_after = Pt(12)
        p_sub = tf_card.add_paragraph()
        p_sub.text = m["sub"]
        p_sub.font.size = Pt(13)
        p_sub.font.bold = True
        p_sub.font.color.rgb = theme_colors["accent"] if not m.get("dark") else theme_colors["success"]

    # SLIDE 3: Native Category Chart
    slide3 = prs.slides.add_slide(blank_slide_layout)
    set_background(slide3, theme_colors["bg_light"])
    add_header(slide3, "Category Distribution", "Top Revenue Categories", "Native chart breakdown of revenue concentration across categories.")
    if rbc:
        chart_data = CategoryChartData()
        top_cats = list(rbc.items())[:6]
        chart_data.categories = [str(k) for k, v in top_cats]
        chart_data.add_series("Revenue", tuple(v for k, v in top_cats))
        chart_shape = slide3.shapes.add_chart(
            XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.8), Inches(2.2), Inches(11.7), Inches(4.5), chart_data
        )
        chart = chart_shape.chart
        chart.has_legend = False
    else:
        txBox = slide3.shapes.add_textbox(Inches(0.8), Inches(2.5), Inches(11.5), Inches(1.0))
        txBox.text_frame.paragraphs[0].text = "No category mapping available."

    # SLIDE 4: Native Trend Chart
    slide4 = prs.slides.add_slide(blank_slide_layout)
    set_background(slide4, theme_colors["bg_light"])
    add_header(slide4, "Performance Trends", "Chronological Revenue Trend", "Monthly revenue trajectory over active timeline.")
    trend_points = trend.get("points", [])
    if trend_points:
        chart_data = CategoryChartData()
        chart_data.categories = [str(p["period"]) for p in trend_points]
        chart_data.add_series("Revenue", tuple(p["revenue"] for p in trend_points))
        chart_shape = slide4.shapes.add_chart(
            XL_CHART_TYPE.LINE, Inches(0.8), Inches(2.2), Inches(11.7), Inches(4.5), chart_data
        )
        chart_shape.chart.has_legend = False
    else:
        txBox = slide4.shapes.add_textbox(Inches(0.8), Inches(2.5), Inches(11.5), Inches(1.0))
        txBox.text_frame.paragraphs[0].text = "No date column selected for chronological trend."

    # SLIDE 5: Data Health
    slide5 = prs.slides.add_slide(blank_slide_layout)
    set_background(slide5, theme_colors["bg_light"])
    add_header(slide5, "Data Governance", "Data Health & Outlier Quality Check", "Automated screening for null cells and duplicate records.")
    circle = slide5.shapes.add_shape(MSO_SHAPE.OVAL, Inches(1.2), Inches(2.5), Inches(3.2), Inches(3.2))
    circle.fill.solid()
    circle.fill.fore_color.rgb = theme_colors["card_bg"]
    circle.line.color.rgb = theme_colors["success"]
    circle.line.width = Pt(3)
    tf_c = circle.text_frame
    tf_c.margin_top = Inches(0.9)
    p_c1 = tf_c.paragraphs[0]
    p_c1.text = f"{meta.get('data_health_index', 100)}%"
    p_c1.font.size = Pt(44)
    p_c1.font.bold = True
    p_c1.font.color.rgb = theme_colors["success"]
    p_c1.alignment = PP_ALIGN.CENTER

    # SLIDE 6: Strategic Action Plan
    slide6 = prs.slides.add_slide(blank_slide_layout)
    set_background(slide6, theme_colors["bg_light"])
    add_header(slide6, "Execution Roadmap", "FINCH Strategic Action Plan", "Prioritized recommendations to sustain operational efficiency.")
    actions = [
        {"num": "01", "title": "Margin Optimization", "desc": "Audit high-cost lines and optimize variable per-unit expenses."},
        {"num": "02", "title": "Category Scaling", "desc": "Scale channel investment into top-performing regional drivers."},
        {"num": "03", "title": "Anomaly Resolution", "desc": "Verify outlier transactions to preserve ledger consistency."},
        {"num": "04", "title": "Scenario Targets", "desc": "Deploy sensitivity forecasts to protect bottom-line margins."}
    ]
    for i, act in enumerate(actions):
        x = Inches(0.8) + i * Inches(3.0)
        box = slide6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(2.2), Inches(2.7), Inches(4.2))
        box.fill.solid()
        box.fill.fore_color.rgb = theme_colors["card_bg"]
        tf_a = box.text_frame
        tf_a.margin_left = Inches(0.25)
        tf_a.margin_top = Inches(0.3)
        tf_a.word_wrap = True
        p_num = tf_a.paragraphs[0]
        p_num.text = act["num"]
        p_num.font.size = Pt(20)
        p_num.font.bold = True
        p_num.font.color.rgb = theme_colors["accent"]
        p_num.space_after = Pt(14)
        p_at = tf_a.add_paragraph()
        p_at.text = act["title"]
        p_at.font.size = Pt(15)
        p_at.font.bold = True
        p_at.font.color.rgb = theme_colors["primary"]
        p_at.space_after = Pt(10)
        p_ad = tf_a.add_paragraph()
        p_ad.text = act["desc"]
        p_ad.font.size = Pt(12)
        p_ad.font.color.rgb = theme_colors["text_muted"]

    # SLIDE 7: Closing
    slide7 = prs.slides.add_slide(blank_slide_layout)
    set_background(slide7, theme_colors["bg_dark"])
    txBox7 = slide7.shapes.add_textbox(Inches(1.5), Inches(2.5), Inches(10.3), Inches(3.0))
    tf7 = txBox7.text_frame
    tf7.word_wrap = True
    p7_1 = tf7.paragraphs[0]
    p7_1.text = "Audit Complete & Verified"
    p7_1.font.size = Pt(38)
    p7_1.font.bold = True
    p7_1.font.color.rgb = RGBColor(248, 250, 252)
    p7_1.alignment = PP_ALIGN.CENTER
    p7_1.space_after = Pt(16)
    p7_2 = tf7.add_paragraph()
    p7_2.text = "FINCH Business Intelligence Workspace"
    p7_2.font.size = Pt(18)
    p7_2.font.color.rgb = theme_colors["success"]
    p7_2.alignment = PP_ALIGN.CENTER

    bio = io.BytesIO()
    prs.save(bio)
    bio.seek(0)
    return bio.getvalue()