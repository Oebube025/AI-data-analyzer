"""
deck_builder.py - FINCH Executive Presentation Generator
Generates an 8-slide PowerPoint deck using native python-pptx structured diagrams, 
KPI cards, and financial breakdown tables without external image rendering dependencies.
"""

import io
import pandas as pd

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# --- FINCH COLOR PALETTE ---
COLOR_BG = RGBColor(11, 15, 25)          # Dark Aesthetic #0B0F19
COLOR_CARD = RGBColor(22, 32, 50)        # Dark Glass Container #162032
COLOR_TEAL = RGBColor(15, 157, 143)      # Teal Accent #0F9D8F
COLOR_EMERALD = RGBColor(16, 185, 129)   # Emerald Green #10B981
COLOR_GOLD = RGBColor(244, 184, 96)      # Accent Gold #F4B860
COLOR_TEXT_MAIN = RGBColor(248, 250, 252)# Bright Text #F8FAFC
COLOR_TEXT_MUTED = RGBColor(148, 163, 184)# Muted Text #94A3B8


def set_slide_background(slide):
    """Sets slide background to FINCH dark blue #0B0F19."""
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = COLOR_BG


def add_header(slide, title_text, category_text="FINCH EXECUTIVE REPORT"):
    """Adds a styled header with custom category eyebrow and title."""
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.5), Inches(1.0))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p_cat = tf.paragraphs[0]
    p_cat.text = category_text.upper()
    p_cat.font.size = Pt(10)
    p_cat.font.bold = True
    p_cat.font.color.rgb = COLOR_GOLD
    
    p_title = tf.add_paragraph()
    p_title.text = title_text
    p_title.font.size = Pt(26)
    p_title.font.bold = True
    p_title.font.color.rgb = COLOR_TEXT_MAIN


def add_kpi_card(slide, left, top, width, height, title, value, subtitle=""):
    """Creates a glassmorphic KPI container card with metric text."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = COLOR_CARD
    card.line.color.rgb = COLOR_TEAL
    card.line.width = Pt(1.5)
    
    tf = card.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.2)
    tf.margin_top = Inches(0.2)
    
    p_label = tf.paragraphs[0]
    p_label.text = title.upper()
    p_label.font.size = Pt(10)
    p_label.font.color.rgb = COLOR_TEXT_MUTED
    
    p_val = tf.add_paragraph()
    p_val.text = str(value)
    p_val.font.size = Pt(22)
    p_val.font.bold = True
    p_val.font.color.rgb = COLOR_EMERALD
    
    if subtitle:
        p_sub = tf.add_paragraph()
        p_sub.text = subtitle
        p_sub.font.size = Pt(9)
        p_sub.font.color.rgb = COLOR_TEXT_MUTED


def create_executive_deck(facts, currency="₦", filename="Dataset", scenarios=None):
    """Generates a styled 8-slide executive presentation byte stream using native PPTX elements."""
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]
    
    totals = facts["totals"]
    cost_known = totals.get("cost_known", False)

    # ------------------------------------------------------------- SLIDE 1: Title Slide
    slide1 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide1)
    
    tb = slide1.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(11.333), Inches(3.0))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p0 = tf.paragraphs[0]
    p0.text = "FINCH EXECUTIVE REPORT"
    p0.font.size = Pt(14)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_GOLD
    
    p1 = tf.add_paragraph()
    p1.text = f"Business Intelligence Audit: {filename}"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_TEXT_MAIN
    
    p2 = tf.add_paragraph()
    p2.text = "Automated financial health audit, growth scenarios, and executive recommendations."
    p2.font.size = Pt(16)
    p2.font.color.rgb = COLOR_TEXT_MUTED

    # ------------------------------------------------------------- SLIDE 2: Executive Summary & KPIs
    slide2 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide2)
    add_header(slide2, "Executive Financial Summary")
    
    rev_str = f"{currency}{totals.get('total_revenue', 0):,.2f}"
    cost_str = f"{currency}{totals.get('total_costs', 0):,.2f}" if cost_known else "N/A"
    profit_str = f"{currency}{totals.get('net_profit', 0):,.2f}" if cost_known else "N/A"
    margin_str = f"{totals.get('profit_margin', 0):.1f}%" if cost_known and totals.get("profit_margin") is not None else "N/A"

    add_kpi_card(slide2, Inches(0.8), Inches(1.8), Inches(2.7), Inches(1.5), "Total Revenue", rev_str)
    add_kpi_card(slide2, Inches(3.8), Inches(1.8), Inches(2.7), Inches(1.5), "Total Costs", cost_str)
    add_kpi_card(slide2, Inches(6.8), Inches(1.8), Inches(2.7), Inches(1.5), "Net Profit", profit_str)
    add_kpi_card(slide2, Inches(9.8), Inches(1.8), Inches(2.7), Inches(1.5), "Profit Margin", margin_str)

    verdict_card = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(3.7), Inches(11.7), Inches(2.8))
    verdict_card.fill.solid()
    verdict_card.fill.fore_color.rgb = COLOR_CARD
    verdict_card.line.color.rgb = COLOR_TEAL
    
    v_tf = verdict_card.text_frame
    v_tf.margin_left = Inches(0.3)
    v_tf.margin_top = Inches(0.3)
    
    vp0 = v_tf.paragraphs[0]
    vp0.text = "FINCH AUDIT VERDICT & KEY OBSERVATIONS"
    vp0.font.size = Pt(12)
    vp0.font.bold = True
    vp0.font.color.rgb = COLOR_GOLD

    obs = facts.get("metadata", {})
    p_text = f"• Total dataset rows analyzed: {obs.get('total_rows', 0):,}\n"
    p_text += f"• Data health index score: {obs.get('data_health_index', 100)}%\n"
    if cost_known:
        p_text += f"• Overall business operation is running with a net margin of {margin_str}.\n"
    else:
        p_text += "• Revenue tracked accurately. Cost analysis currently pending cost column assignment."

    vp1 = v_tf.add_paragraph()
    vp1.text = p_text
    vp1.font.size = Pt(14)
    vp1.font.color.rgb = COLOR_TEXT_MAIN

    # ------------------------------------------------------------- SLIDE 3: Financial Performance Breakdown
    slide3 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide3)
    add_header(slide3, "Financial Overview & Core Metrics")

    card_fin = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(11.7), Inches(4.8))
    card_fin.fill.solid()
    card_fin.fill.fore_color.rgb = COLOR_CARD
    card_fin.line.color.rgb = COLOR_TEAL

    ftf = card_fin.text_frame
    ftf.margin_left = Inches(0.4)
    ftf.margin_top = Inches(0.4)
    
    fp0 = ftf.paragraphs[0]
    fp0.text = "FINANCIAL PERFORMANCE METRICS"
    fp0.font.size = Pt(14)
    fp0.font.bold = True
    fp0.font.color.rgb = COLOR_GOLD

    fp1 = ftf.add_paragraph()
    fp1.text = f"• Gross Top-Line Revenue: {rev_str}\n" \
               f"• Total Recorded Costs: {cost_str}\n" \
               f"• Bottom-Line Net Profit: {profit_str}\n" \
               f"• Operating Margin Efficiency: {margin_str}"
    fp1.font.size = Pt(16)
    fp1.font.color.rgb = COLOR_TEXT_MAIN

    # ------------------------------------------------------------- SLIDE 4: Category Distribution Breakdown
    slide4 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide4)
    add_header(slide4, "Top Revenue Categories & Concentration")

    card_cat = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(11.7), Inches(4.8))
    card_cat.fill.solid()
    card_cat.fill.fore_color.rgb = COLOR_CARD
    card_cat.line.color.rgb = COLOR_TEAL

    ctf = card_cat.text_frame
    ctf.margin_left = Inches(0.4)
    ctf.margin_top = Inches(0.4)
    
    cp0 = ctf.paragraphs[0]
    cp0.text = "CATEGORY REVENUE LEADERBOARD"
    cp0.font.size = Pt(14)
    cp0.font.bold = True
    cp0.font.color.rgb = COLOR_GOLD

    rbc = facts.get("revenue_by_category", {})
    cat_text = ""
    if rbc:
        for cat, val in list(rbc.items())[:6]:
            cat_text += f"• {cat}: {currency}{val:,.2f}\n"
    else:
        cat_text = "No category mapping selected for breakdown."

    cp1 = ctf.add_paragraph()
    cp1.text = cat_text
    cp1.font.size = Pt(14)
    cp1.font.color.rgb = COLOR_TEXT_MAIN

    # ------------------------------------------------------------- SLIDE 5: Data Reliability & Quality Audit
    slide5 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide5)
    add_header(slide5, "Data Health & Outlier Quality Check")

    meta = facts.get("metadata", {})
    add_kpi_card(slide5, Inches(0.8), Inches(1.8), Inches(3.6), Inches(1.6), "Health Score", f"{meta.get('data_health_index', 100)}%")
    add_kpi_card(slide5, Inches(4.8), Inches(1.8), Inches(3.6), Inches(1.6), "Missing Cells", f"{meta.get('missing_cells', 0):,}")
    add_kpi_card(slide5, Inches(8.8), Inches(1.8), Inches(3.6), Inches(1.6), "Duplicate Rows", f"{meta.get('duplicate_rows', 0):,}")

    anom_card = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(3.8), Inches(11.6), Inches(2.8))
    anom_card.fill.solid()
    anom_card.fill.fore_color.rgb = COLOR_CARD
    anom_card.line.color.rgb = COLOR_TEAL

    atf = anom_card.text_frame
    atf.margin_left = Inches(0.3)
    atf.margin_top = Inches(0.3)
    
    ap0 = atf.paragraphs[0]
    ap0.text = "ANOMALY & OUTLIER DETECTION"
    ap0.font.size = Pt(12)
    ap0.font.bold = True
    ap0.font.color.rgb = COLOR_GOLD

    anomalies = facts.get("anomalies", [])
    ap1 = atf.add_paragraph()
    if anomalies:
        ap1.text = f"Detected {len(anomalies)} statistical anomalies in transaction values. Verify large transactions for potential data entry errors or concentrated revenue spikes."
    else:
        ap1.text = "No statistical anomalies detected. Data distribution remains within expected bounds."
    ap1.font.size = Pt(14)
    ap1.font.color.rgb = COLOR_TEXT_MAIN

    # ------------------------------------------------------------- SLIDE 6: What-If Scenarios Diagram
    slide6 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide6)
    add_header(slide6, "What-If Growth & Sensitivity Scenarios")

    if scenarios and len(scenarios) > 0:
        left_pos = 0.8
        for i, sc in enumerate(scenarios[:3]):
            sc_card = slide6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left_pos), Inches(1.8), Inches(3.6), Inches(4.5))
            sc_card.fill.solid()
            sc_card.fill.fore_color.rgb = COLOR_CARD
            sc_card.line.color.rgb = COLOR_GOLD
            
            stf = sc_card.text_frame
            stf.margin_left = Inches(0.2)
            stf.margin_top = Inches(0.2)
            
            sp0 = stf.paragraphs[0]
            sp0.text = sc.get("scenario_name", f"Scenario {i+1}").upper()
            sp0.font.size = Pt(14)
            sp0.font.bold = True
            sp0.font.color.rgb = COLOR_GOLD
            
            sp1 = stf.add_paragraph()
            sp1.text = f"\nSimulated Rev: {currency}{sc.get('revenue', 0):,.2f}\nSimulated Costs: {currency}{sc.get('costs', 0):,.2f}\nSimulated Profit: {currency}{sc.get('net_profit', 0):,.2f}\nMargin: {sc.get('margin', 0):.1f}%"
            sp1.font.size = Pt(12)
            sp1.font.color.rgb = COLOR_TEXT_MAIN
            
            left_pos += 4.0
    else:
        no_sc = slide6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(11.6), Inches(4.5))
        no_sc.fill.solid()
        no_sc.fill.fore_color.rgb = COLOR_CARD
        no_sc.line.color.rgb = COLOR_TEAL
        
        nstf = no_sc.text_frame
        p = nstf.paragraphs[0]
        p.text = "No saved scenario models present for diagram comparison. Model price & volume adjustments in the What-If tab."
        p.font.size = Pt(14)
        p.font.color.rgb = COLOR_TEXT_MUTED

    # ------------------------------------------------------------- SLIDE 7: Strategic Recommendations
    slide7 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide7)
    add_header(slide7, "FINCH Strategic Action Plan")

    rec_card = slide7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(11.6), Inches(4.8))
    rec_card.fill.solid()
    rec_card.fill.fore_color.rgb = COLOR_CARD
    rec_card.line.color.rgb = COLOR_TEAL

    rtf = rec_card.text_frame
    rtf.margin_left = Inches(0.4)
    rtf.margin_top = Inches(0.4)

    rp0 = rtf.paragraphs[0]
    rp0.text = "RECOMMENDED ACTION ITEMS"
    rp0.font.size = Pt(14)
    rp0.font.bold = True
    rp0.font.color.rgb = COLOR_GOLD

    rp1 = rtf.add_paragraph()
    rp1.text = "1. Margin Optimization: Audit high-cost lines and optimize variable per-unit expenses.\n" \
               "2. Category Focus: Scale investment into top-performing revenue categories.\n" \
               "3. Anomaly Resolution: Verify outliers to maintain data integrity across accounting records.\n" \
               "4. Scenario Execution: Implement price/volume sensitivity targets for upcoming quarter."
    rp1.font.size = Pt(14)
    rp1.font.color.rgb = COLOR_TEXT_MAIN

    # ------------------------------------------------------------- SLIDE 8: Closing Slide
    slide8 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide8)

    tb8 = slide8.shapes.add_textbox(Inches(1.0), Inches(2.5), Inches(11.333), Inches(2.5))
    tf8 = tb8.text_frame
    
    p8_0 = tf8.paragraphs[0]
    p8_0.alignment = PP_ALIGN.CENTER
    p8_0.text = "FINCH"
    p8_0.font.size = Pt(48)
    p8_0.font.bold = True
    p8_0.font.color.rgb = COLOR_TEAL

    p8_1 = tf8.add_paragraph()
    p8_1.alignment = PP_ALIGN.CENTER
    p8_1.text = "Secure Business Intelligence Workspace"
    p8_1.font.size = Pt(16)
    p8_1.font.color.rgb = COLOR_TEXT_MUTED

    # Output to Byte Buffer
    bio = io.BytesIO()
    prs.save(bio)
    bio.seek(0)
    return bio.getvalue()