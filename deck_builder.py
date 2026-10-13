"""
Business Report Deck Generator (deck_builder.py)
Builds a real 12-slide strategic deck from the verified fact sheet.
Contains ZERO Streamlit imports.
"""

import io

import pandas as pd
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches, Pt

from analysis import derive_insights

THEME_BG = RGBColor(15, 23, 42)
THEME_TEXT = RGBColor(248, 250, 252)
THEME_MUTED = RGBColor(148, 163, 184)
THEME_ACCENT = RGBColor(59, 130, 246)


def _new_slide(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = THEME_BG
    return s


def _textbox(slide, x, y, w, h, items):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, (text, size, color, bold) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = text
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.font.bold = bold
        p.space_after = Pt(8)
    return tb


def _bullets(slide, lines, x=0.8, y=1.8, w=11.7, h=4.8, size=15, color=THEME_TEXT):
    _textbox(slide, x, y, w, h, [(f"•  {ln}", size, color, False) for ln in lines])


def _slide(prs, title, filename):
    s = _new_slide(prs)
    _textbox(s, 0.8, 0.5, 11.7, 1.0, [
        (title, 26, THEME_TEXT, True),
        (f"Executive Intelligence Suite (Beta)  |  {filename}", 10, THEME_MUTED, False),
    ])
    return s


def _chart(slide, cats, vals, x, y, w, h, line=False, name="Revenue"):
    cd = CategoryChartData()
    cd.categories = [str(c) for c in cats]
    cd.add_series(name, [float(v) for v in vals])
    kind = XL_CHART_TYPE.LINE_MARKERS if line else XL_CHART_TYPE.COLUMN_CLUSTERED
    chart = slide.shapes.add_chart(kind, Inches(x), Inches(y), Inches(w), Inches(h), cd).chart
    chart.has_legend = False
    chart.font.size = Pt(11)
    chart.font.color.rgb = THEME_TEXT
    series = chart.plots[0].series[0]
    if line:
        series.format.line.color.rgb = THEME_ACCENT
        series.smooth = False
    else:
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = THEME_ACCENT
    return chart


def _fmt_pct(v):
    return "n/a" if v is None or pd.isna(v) else f"{v:.1f}%"


def create_executive_deck(facts: dict, currency: str = "₦", filename: str = "dataset.csv",
                          scenarios: list = None) -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    t, meta, trend, conc = facts["totals"], facts["metadata"], facts["trend"], facts["concentration"]
    cat_col, rev_col = meta["category_column"], meta["revenue_column"]
    money = lambda v: f"{currency}{v:,.2f}"
    insights = derive_insights(facts, currency)
    scenarios = scenarios or []
    cost_known = t["cost_known"]

    # 1 Title
    s = _new_slide(prs)
    _textbox(s, 1, 2.4, 11.3, 3, [
        ("Business Performance Report", 40, THEME_TEXT, True),
        (f"Analyzed records: {meta['total_records']:,}  |  File: {filename}", 18, THEME_MUTED, False),
    ])

    # 2 Financial snapshot
    s = _slide(prs, "Your Numbers at a Glance", filename)
    kpis = [("REVENUE", money(t["total_revenue"]))]
    if cost_known:
        kpis += [("COSTS", money(t["total_costs"])), ("NET PROFIT", money(t["net_profit"])),
                 ("MARGIN", _fmt_pct(t["profit_margin"]))]
    else:
        kpis += [("COSTS", "Not provided (Assumed in models)"), ("NET PROFIT", "n/a"), ("MARGIN", "n/a")]
    for i, (lbl, val) in enumerate(kpis):
        _textbox(s, 0.8 + i * 3.0, 1.8, 2.8, 1.5, [(lbl, 11, THEME_MUTED, True), (val, 22, THEME_TEXT, True)])
    _textbox(s, 0.8, 3.7, 11.7, 0.5, [("Key observations", 16, THEME_TEXT, True)])
    _bullets(s, insights["highlights"], y=4.2, h=2.8, size=13, color=THEME_MUTED)

    # 3 Revenue by category
    s = _slide(prs, "What Sells Best", filename)
    top = facts["leaderboards"]["top_items"][:6]
    if top and cat_col:
        _chart(s, [i[cat_col] for i in top], [i[rev_col] for i in top], 0.8, 1.7, 7.8, 5.1)
        _bullets(s, [
            f"'{conc['top_category']}' leads with {conc['top1_share']:.1f}% of revenue.",
            f"The top 3 categories account for {conc['top3_share']:.1f}%.",
        ], x=8.9, y=2.0, w=3.8, h=4, size=14)
    else:
        _bullets(s, ["No category column was selected, so no category breakdown is available."])

    # 4 Executive summary
    s = _slide(prs, "Summary", filename)
    _bullets(s, insights["highlights"] + [f"Top risk: {insights['risks'][0]}"])

    # 5 Revenue and profit
    s = _slide(prs, "Money In, Money Out", filename)
    if cost_known:
        _chart(s, ["Revenue", "Costs", "Net Profit"], [t["total_revenue"], t["total_costs"], t["net_profit"]],
               0.8, 1.7, 7.8, 5.1, name="Amount")
        cost_pct = t["total_costs"] / t["total_revenue"] * 100 if t["total_revenue"] > 0 else None
        _bullets(s, [
            f"Costs absorb {_fmt_pct(cost_pct)} of revenue.",
            f"Net profit is {money(t['net_profit'])} ({_fmt_pct(t['profit_margin'])} margin).",
        ], x=8.9, y=2.0, w=3.8, h=4, size=14)
    else:
        _bullets(s, [f"Total revenue is {money(t['total_revenue'])}.",
                     "Cost data was NOT provided in source file (profitability estimated via scenario assumptions)."])

    # 6 Top and bottom performers
    s = _slide(prs, "Best and Weakest Sellers", filename)
    items = facts["leaderboards"]
    if items["top_items"] and cat_col:
        _textbox(s, 0.8, 1.8, 5.6, 0.5, [("Top performers", 16, THEME_TEXT, True)])
        _bullets(s, [f"{i[cat_col]}: {money(i[rev_col])}" for i in items["top_items"]], y=2.4, w=5.8, size=13)
        if len(facts["revenue_by_category"]) > 5:
            _textbox(s, 7.0, 1.8, 5.6, 0.5, [("Lowest performers", 16, THEME_TEXT, True)])
            _bullets(s, [f"{i[cat_col]}: {money(i[rev_col])}" for i in items["bottom_items"]],
                     x=7.0, y=2.4, w=5.6, size=13)
    else:
        _bullets(s, ["No category column was selected."])

    # 7 Trends
    s = _slide(prs, "How Sales Change Over Time", filename)
    pts = trend["points"]
    if len(pts) >= 2:
        _chart(s, [p["period"] for p in pts], [p["revenue"] for p in pts], 0.8, 1.7, 7.8, 5.1, line=True)
        lines = [f"Revenue is shown by {trend['granularity']} across {len(pts)} periods."]
        if trend["change_pct"] is not None:
            lines.append(f"Latest period moved {trend['change_pct']:+.1f}% versus the previous one.")
        best = max(pts, key=lambda p: p["revenue"])
        lines.append(f"Peak period: {best['period']} ({money(best['revenue'])}).")
        _bullets(s, lines, x=8.9, y=2.0, w=3.8, h=4, size=14)
    else:
        _bullets(s, ["No usable date column was selected, so no trend is available."])

    # 8 Scenario outlook
    s = _slide(prs, "What-If Plans (Cost-Assumed Model)", filename)
    if scenarios:
        lines = ["Note: Scenarios apply explicit fixed/variable cost separation models."]
        for sc in scenarios[-5:]:
            lines.append(f"{sc.get('scenario_name')}: revenue {money(sc['revenue'])}, "
                         f"net profit {money(sc['net_profit'])}, margin {_fmt_pct(sc.get('margin'))}")
        _bullets(s, lines, size=14)
    else:
        _bullets(s, ["No What-If scenarios have been saved yet."])

    # 9 Risks
    s = _slide(prs, "Things to Watch", filename)
    _bullets(s, insights["risks"])

    # 10 Actions
    s = _slide(prs, "What To Do Next (30/60/90 days)", filename)
    for i, days in enumerate(["30", "60", "90"]):
        items = [(f"Next {days} days", 16, THEME_ACCENT, True)] + \
                [(f"•  {a}", 13, THEME_TEXT, False) for a in insights["actions"][days]]
        _textbox(s, 0.8 + i * 4.0, 1.9, 3.8, 4.8, items)

    # 11 Data quality
    s = _slide(prs, "Is Your Data Reliable?", filename)
    lines = [f"Data health index: {meta['data_health_index']}%  |  Missing cells: {meta['missing_cells']:,}  |  "
             f"Duplicate rows: {meta['duplicate_rows']:,}"]
    if meta["anomaly_count"]:
        vals = [a.get(rev_col) for a in facts["anomalies"][:5]]
        lines.append(f"{meta['anomaly_count']} unusually large transaction(s) found.")
    else:
        lines.append("No significant outliers detected.")
    _bullets(s, lines)

    # 12 Appendix
    s = _slide(prs, "Notes: How This Was Worked Out", filename)
    lines = [
        f"Revenue column: {rev_col}. Cost column: {meta['cost_column'] or 'none (Assumed)'}.",
        "All figures computed directly from uploaded records.",
    ] + facts["warnings"][:6]
    _bullets(s, lines, size=12, color=THEME_MUTED)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()