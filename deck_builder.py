"""
Executive Deck Builder (deck_builder.py)
Generates bank-ready PowerPoint presentations with defensive key lookups.
"""

import io
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor


def create_executive_deck(facts: dict, currency: str = "₦", filename: str = "Financial_Report.xlsx", scenarios: list = None) -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    blank_slide_layout = prs.slide_layouts[6]
    
    totals = facts.get("totals", {})
    rev = totals.get("total_revenue", 0.0)
    costs = totals.get("total_costs")
    profit = totals.get("net_profit")
    margin = totals.get("profit_margin")
    cost_known = totals.get("cost_known", False)

    # Slide 1: Title Slide
    slide1 = prs.slides.add_slide(blank_slide_layout)
    txBox = slide1.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11.333), Inches(2))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = "Executive Financial Intelligence Brief"
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = RGBColor(15, 23, 42)
    
    p2 = tf.add_paragraph()
    p2.text = f"Source File: {filename} | Currency: {currency}"
    p2.font.size = Pt(20)
    p2.font.color.rgb = RGBColor(100, 116, 139)

    # Slide 2: Financial Summary
    slide2 = prs.slides.add_slide(blank_slide_layout)
    txBox2 = slide2.shapes.add_textbox(Inches(1), Inches(1), Inches(11.333), Inches(5))
    tf2 = txBox2.text_frame
    
    p = tf2.paragraphs[0]
    p.text = "Financial Performance Overview"
    p.font.size = Pt(28)
    p.font.bold = True
    
    p = tf2.add_paragraph()
    p.text = f"• Total Revenue: {currency}{rev:,.2f}"
    p.font.size = Pt(20)
    
    p = tf2.add_paragraph()
    if cost_known and profit is not None:
        p.text = f"• Total Costs: {currency}{costs:,.2f} | Net Profit: {currency}{profit:,.2f} ({margin:.1f}% margin)"
    else:
        p.text = "• Costs: Not provided | Net Profit: n/a"
    p.font.size = Pt(20)

    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()