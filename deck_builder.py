"""
Executive Deck Builder (deck_builder.py)
Generates a professional 8-slide bank-ready PowerPoint presentation.
"""

import io
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN


def create_executive_deck(facts: dict, currency: str = "₦", filename: str = "Financial_Report.xlsx", scenarios: list = None) -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    layout = prs.slide_layouts[6]  # Blank slide
    
    totals = facts.get("totals", {})
    meta = facts.get("metadata", {})
    rev = totals.get("total_revenue", 0.0)
    costs = totals.get("total_costs")
    profit = totals.get("net_profit")
    margin = totals.get("profit_margin")
    cost_known = totals.get("cost_known", False)
    concentration = facts.get("concentration", {})
    leaderboards = facts.get("leaderboards", {})
    warnings = facts.get("warnings", [])

    def add_header(slide, title_text, subtitle_text):
        tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(11.7), Inches(1.2))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = RGBColor(15, 23, 42)
        
        p2 = tf.add_paragraph()
        p2.text = subtitle_text
        p2.font.size = Pt(14)
        p2.font.color.rgb = RGBColor(100, 116, 139)

    def add_footer(slide, slide_num):
        tb = slide.shapes.add_textbox(Inches(0.8), Inches(7.0), Inches(11.7), Inches(0.3))
        tf = tb.text_frame
        p = tf.paragraphs[0]
        p.text = f"Executive Intelligence Suite | Source: {filename} | Slide {slide_num} of 8"
        p.font.size = Pt(10)
        p.font.color.rgb = RGBColor(148, 163, 184)

    # --- Slide 1: Title Slide ---
    slide1 = prs.slides.add_slide(layout)
    tb1 = slide1.shapes.add_textbox(Inches(1), Inches(2.2), Inches(11.3), Inches(3))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "Executive Financial Intelligence Brief"
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = RGBColor(15, 23, 42)
    
    p2 = tf1.add_paragraph()
    p2.text = f"Prepared for SME Audit & Bank Review\nFile: {filename} | Currency: {currency}"
    p2.font.size = Pt(18)
    p2.font.color.rgb = RGBColor(100, 116, 139)
    add_footer(slide1, 1)

    # --- Slide 2: Executive Summary ---
    slide2 = prs.slides.add_slide(layout)
    add_header(slide2, "1. Executive Summary", "High-level financial health overview of your business records.")
    tb2 = slide2.shapes.add_textbox(Inches(0.8), Inches(2.0), Inches(11.7), Inches(4.5))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    
    bullets = [
        f"Total Verified Revenue: {currency}{rev:,.2f}",
        f"Total Recorded Costs: {currency}{costs:,.2f}" if cost_known else "Total Recorded Costs: Not provided in dataset",
        f"Net Profitability: {currency}{profit:,.2f} ({margin:.1f}% margin)" if cost_known and profit is not None else "Net Profitability: n/a (Requires cost column)",
        f"Data Reliability Index: {meta.get('data_health_index', 100)}% (Based on missing cells & duplicates)"
    ]
    for b in bullets:
        p = tf2.add_paragraph()
        p.text = f"• {b}"
        p.font.size = Pt(18)
        p.font.color.rgb = RGBColor(30, 41, 59)
        p.space_after = Pt(14)
    add_footer(slide2, 2)

    # --- Slide 3: Revenue & Profitability Breakdown ---
    slide3 = prs.slides.add_slide(layout)
    add_header(slide3, "2. Revenue & Profitability Breakdown", "Core financial margins and earnings analysis.")
    tb3 = slide3.shapes.add_textbox(Inches(0.8), Inches(2.0), Inches(11.7), Inches(4.5))
    tf3 = tb3.text_frame
    tf3.word_wrap = True
    p = tf3.paragraphs[0]
    p.text = f"Your business generated {currency}{rev:,.2f} across {meta.get('total_records', 0):,} transaction rows."
    p.font.size = Pt(18)
    p.font.color.rgb = RGBColor(30, 41, 59)
    p.space_after = Pt(14)
    
    p2 = tf3.add_paragraph()
    if cost_known and profit is not None:
        if profit > 0:
            p2.text = f"The business operated at a net profit of {currency}{profit:,.2f}, representing a healthy {margin:.1f}% return on revenue."
        else:
            p2.text = f"Warning: The business incurred a net loss of {currency}{abs(profit):,.2f}. Immediate cost rationalization is recommended."
    else:
        p2.text = "Cost metrics were not explicitly mapped. Establishing a baseline cost ratio (e.g., 70% of revenue) is recommended for accurate forecasting."
    p2.font.size = Pt(16)
    p2.font.color.rgb = RGBColor(71, 85, 105)
    add_footer(slide3, 3)

    # --- Slide 4: Category Leaderboards ---
    slide4 = prs.slides.add_slide(layout)
    add_header(slide4, "3. Top Performing Categories", "Revenue distribution across product lines and categories.")
    tb4 = slide4.shapes.add_textbox(Inches(0.8), Inches(2.0), Inches(11.7), Inches(4.5))
    tf4 = tb4.text_frame
    tf4.word_wrap = True
    
    if leaderboards:
        p = tf4.paragraphs[0]
        p.text = "Top Revenue Drivers:"
        p.font.size = Pt(18)
        p.font.bold = True
        for cat, val in list(leaderboards.items())[:5]:
            p_item = tf4.add_paragraph()
            p_item.text = f"• {cat}: {currency}{val:,.2f}"
            p_item.font.size = Pt(16)
            p_item.font.color.rgb = RGBColor(51, 65, 85)
            p_item.space_after = Pt(8)
    else:
        p = tf4.paragraphs[0]
        p.text = "No category column was mapped for leaderboard analysis."
        p.font.size = Pt(16)
    add_footer(slide4, 4)

    # --- Slide 5: Concentration Risk ---
    slide5 = prs.slides.add_slide(layout)
    add_header(slide5, "4. Revenue Concentration Risk", "Evaluating reliance on top revenue streams.")
    tb5 = slide5.shapes.add_textbox(Inches(0.8), Inches(2.0), Inches(11.7), Inches(4.5))
    tf5 = tb5.text_frame
    tf5.word_wrap = True
    p = tf5.paragraphs[0]
    p.text = f"Concentration Analysis: {concentration.get('share', 'Moderate')}"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = RGBColor(15, 23, 42)
    p.space_after = Pt(14)
    
    p2 = tf5.add_paragraph()
    p2.text = f"Top Category: {concentration.get('top_category', 'N/A')}\nDiversification is key to mitigating supply chain and customer demand shocks."
    p2.font.size = Pt(16)
    p2.font.color.rgb = RGBColor(71, 85, 105)
    add_footer(slide5, 5)

    # --- Slide 6: Data Integrity & Reliability ---
    slide6 = prs.slides.add_slide(layout)
    add_header(slide6, "5. Record-Keeping & Data Health", "Auditability score of uploaded records.")
    tb6 = slide6.shapes.add_textbox(Inches(0.8), Inches(2.0), Inches(11.7), Inches(4.5))
    tf6 = tb6.text_frame
    tf6.word_wrap = True
    p = tf6.paragraphs[0]
    p.text = f"Data Health Index: {meta.get('data_health_index', 100)} / 100"
    p.font.size = Pt(20)
    p.font.bold = True
    p.space_after = Pt(14)
    
    p2 = tf6.add_paragraph()
    p2.text = f"• Missing Cells: {meta.get('missing_cells', 0):,}\n• Duplicate Rows: {meta.get('duplicate_rows', 0):,}\n• Statistical Outliers Detected: {meta.get('anomaly_count', 0)}"
    p2.font.size = Pt(16)
    p2.font.color.rgb = RGBColor(71, 85, 105)
    add_footer(slide6, 6)

    # --- Slide 7: What-If Scenarios & Risks ---
    slide7 = prs.slides.add_slide(layout)
    add_header(slide7, "6. Key Risks & Warnings", "Identified operational risks from dataset audit.")
    tb7 = slide7.shapes.add_textbox(Inches(0.8), Inches(2.0), Inches(11.7), Inches(4.5))
    tf7 = tb7.text_frame
    tf7.word_wrap = True
    if warnings:
        p = tf7.paragraphs[0]
        p.text = "Identified Warnings:"
        p.font.size = Pt(18)
        p.font.bold = True
        for w in warnings:
            pw = tf7.add_paragraph()
            pw.text = f"• {w}"
            pw.font.size = Pt(15)
            pw.font.color.rgb = RGBColor(185, 28, 28)
            pw.space_after = Pt(8)
    else:
        p = tf7.paragraphs[0]
        p.text = "No critical data warnings identified in this audit."
        p.font.size = Pt(16)
    add_footer(slide7, 7)

    # --- Slide 8: 30 / 60 / 90-Day Action Plan ---
    slide8 = prs.slides.add_slide(layout)
    add_header(slide8, "7. Recommended Action Plan", "Strategic milestones for the next quarter.")
    tb8 = slide8.shapes.add_textbox(Inches(0.8), Inches(2.0), Inches(11.7), Inches(4.5))
    tf8 = tb8.text_frame
    tf8.word_wrap = True
    p = tf8.paragraphs[0]
    p.text = "• Next 30 Days: Reconcile missing cost records and verify inventory counts.\n• Next 60 Days: Focus marketing efforts on top-performing product categories.\n• Next 90 Days: Implement monthly scenario forecasting to protect net margins."
    p.font.size = Pt(16)
    p.font.color.rgb = RGBColor(30, 41, 59)
    add_footer(slide8, 8)

    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()