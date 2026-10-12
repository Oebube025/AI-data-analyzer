"""
Core Analytics Fact Sheet Engine (analysis.py)
Single source of truth for the dashboard, the deck and the AI advisor.
Contains ZERO Streamlit or FastAPI imports. Never mutates the DataFrame passed in.
"""

import math
import re
import warnings as _warnings

import numpy as np
import pandas as pd

SUMMARY_CELL_RE = re.compile(r"^\s*(grand\s+|sub\s*-?\s*)?(totals?|sum|overall)\s*:?\s*$", re.I)
ID_TOKENS = {"id", "code", "year", "month", "day", "phone", "zip", "sku", "no", "number", "index"}
REV_HINTS = ["revenue", "sales", "turnover", "income", "amount"]
COST_HINTS = ["cost", "expense", "cogs", "expenditure", "spend"]
QTY_HINTS = ["qty", "quantity", "units", "pcs"]
PRICE_HINTS = ["price", "rate"]
DATE_HINTS = ["date", "time", "period", "month"]
COMPUTED_REV = "Revenue (Qty x Price)"


# ----------------------------------------------------------------- helpers
def _tokens(name) -> set:
    return {t for t in re.split(r"[^a-z0-9]+", str(name).lower()) if t}


def _has(name, hints) -> bool:
    n = str(name).lower()
    return any(h in n for h in hints)


def _is_id_like(name) -> bool:
    return bool(_tokens(name) & ID_TOKENS)


def valid_numeric_columns(df: pd.DataFrame) -> list:
    return [c for c in df.select_dtypes(include=[np.number]).columns if not _is_id_like(c)]


def _text_to_number(s: pd.Series) -> pd.Series:
    t = s.astype("string").str.strip()
    neg = t.str.match(r"^\(.*\)$", na=False).astype(bool)
    t = t.str.replace(r"[₦$€£,\s()]", "", regex=True)
    out = pd.to_numeric(t, errors="coerce").astype("float64")
    return out.where(~neg, -out.abs())


def _parse_dates(series: pd.Series):
    """Return a datetime Series if >=80% of non-null values parse, else None."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    if pd.api.types.is_numeric_dtype(series):
        return None
    nonnull = series.dropna()
    if nonnull.empty:
        return None
    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore")
        parsed = pd.to_datetime(series, errors="coerce")
    if parsed.notna().sum() / len(nonnull) >= 0.8:
        return parsed
    return None


def to_jsonable(o):
    """Recursively convert numpy/pandas values to JSON-safe Python values (NaN -> None)."""
    if isinstance(o, dict):
        return {str(k): to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_jsonable(v) for v in o]
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (bool, str)) or o is None:
        return o
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        return None if (math.isnan(f) or math.isinf(f)) else f
    return str(o)


# ------------------------------------------------------------- preparation
def prepare_dataframe(df: pd.DataFrame):
    """
    Clean a raw upload once. Returns (clean_df, notes).
    - strips column names
    - removes Total/Sum/Overall rows (so they are never double counted)
    - converts text-numbers such as '₦1,200' or '(500)' to numbers
    - creates 'Revenue (Qty x Price)' when only quantity and unit price exist
    """
    notes = []
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]

    obj_cols = list(out.select_dtypes(include=["object", "string"]).columns)
    if obj_cols:
        mask = pd.Series(False, index=out.index)
        for c in obj_cols:
            mask |= out[c].astype("string").str.match(SUMMARY_CELL_RE.pattern, case=False, na=False).astype(bool)
        n = int(mask.sum())
        if n:
            out = out[~mask].copy()
            notes.append(f"Excluded {n} summary row(s) (Total/Sum/Overall) so they are not double counted.")

    for c in list(out.select_dtypes(include=["object", "string"]).columns):
        nonnull = out[c].dropna()
        if nonnull.empty:
            continue
        if not nonnull.astype("string").str.contains(r"[₦$€£,()]", regex=True, na=False).any():
            continue
        if _text_to_number(nonnull).notna().mean() >= 0.9:
            out[c] = _text_to_number(out[c])
            notes.append(f"Converted text-numeric column '{c}' to numbers.")

    nums = valid_numeric_columns(out)
    has_rev = any(_has(c, REV_HINTS) and not _has(c, COST_HINTS) for c in nums)
    if not has_rev:
        q = next((c for c in nums if _has(c, QTY_HINTS)), None)
        p = next((c for c in nums if _has(c, PRICE_HINTS)), None)
        if q and p and q != p:
            out[COMPUTED_REV] = out[q] * out[p]
            notes.append(f"No revenue column found, so '{COMPUTED_REV}' was computed from '{q}' x '{p}'.")

    return out.reset_index(drop=True), notes


def suggest_columns(df: pd.DataFrame) -> dict:
    nums = valid_numeric_columns(df)
    rev = None
    for h in REV_HINTS:
        rev = next((c for c in nums if h in c.lower() and not _has(c, COST_HINTS)), None)
        if rev:
            break
    if rev is None and COMPUTED_REV in df.columns:
        rev = COMPUTED_REV
    if rev is None:
        others = [c for c in nums if not _has(c, COST_HINTS + QTY_HINTS + PRICE_HINTS)]
        rev = others[0] if others else (nums[0] if nums else None)
    cost = next((c for c in nums if c != rev and _has(c, COST_HINTS)), None)

    category = None
    limit = min(100, max(2, int(len(df) * 0.5)))
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c]):
            continue
        if pd.api.types.is_datetime64_any_dtype(df[c]) or _is_id_like(c) or _has(c, DATE_HINTS):
            continue
        if 2 <= df[c].nunique(dropna=True) <= limit:
            category = c
            break

    date = next((c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])), None)
    if date is None:
        date = next((c for c in df.columns if _has(c, DATE_HINTS) and _parse_dates(df[c]) is not None), None)

    return {"revenue": rev, "cost": cost, "category": category, "date": date}


# ---------------------------------------------------------------- analysis
def _resolve(col, df, auto):
    """'None' means explicitly none; missing/invalid means use the auto suggestion."""
    if col == "None":
        return None
    if col is not None and col in df.columns:
        return col
    return auto


def analyze_dataset(df, revenue_col=None, cost_col=None, category_col=None,
                    date_col=None, prep_notes=None) -> dict:
    """Pass a DataFrame from prepare_dataframe(). Does not modify it."""
    df = df.copy()
    warnings = list(prep_notes or [])
    sug = suggest_columns(df)

    revenue_col = _resolve(revenue_col, df, sug["revenue"])
    cost_col = _resolve(cost_col, df, sug["cost"])
    category_col = _resolve(category_col, df, sug["category"])
    date_col = _resolve(date_col, df, sug["date"])
    if cost_col == revenue_col:
        cost_col = None

    if revenue_col is not None:
        df[revenue_col] = pd.to_numeric(df[revenue_col], errors="coerce")
    tot_rev = float(df[revenue_col].sum()) if revenue_col else 0.0
    if revenue_col is None:
        warnings.append("No numeric revenue column could be identified.")

    cost_known = cost_col is not None
    if cost_known:
        df[cost_col] = pd.to_numeric(df[cost_col], errors="coerce")
        tot_cost = float(df[cost_col].sum())
        net_profit = tot_rev - tot_cost
        margin = round(net_profit / tot_rev * 100, 2) if tot_rev > 0 else None
    else:
        tot_cost, net_profit, margin = 0.0, None, None
        warnings.append("No cost column selected: profit and margin are not available. Select a cost column to see them.")

    total_cells = df.size
    missing_cells = int(df.isna().sum().sum())
    health_index = max(0.0, min(100.0, (total_cells - missing_cells) / max(1, total_cells) * 100))
    duplicates = int(df.duplicated().sum())

    revenue_by_category, top_items, bottom_items = {}, [], []
    concentration = {"top_category": None, "top1_share": 0.0, "top3_share": 0.0}
    if category_col and revenue_col:
        grouped = (df.groupby(category_col, dropna=True)[revenue_col].sum().reset_index()
                   .sort_values(by=revenue_col, ascending=False))
        revenue_by_category = {str(k): float(v) for k, v in zip(grouped[category_col], grouped[revenue_col])}
        top_items = grouped.head(5).to_dict(orient="records")
        bottom_items = grouped.tail(5).to_dict(orient="records")
        pos_total = sum(v for v in revenue_by_category.values() if v > 0)
        if pos_total > 0 and revenue_by_category:
            vals = list(revenue_by_category.items())
            concentration = {
                "top_category": vals[0][0],
                "top1_share": round(vals[0][1] / pos_total * 100, 1),
                "top3_share": round(sum(v for _, v in vals[:3]) / pos_total * 100, 1),
            }

    trend = {"granularity": None, "points": [], "change_pct": None}
    if date_col and revenue_col:
        parsed = _parse_dates(df[date_col])
        if parsed is None:
            warnings.append(f"Column '{date_col}' could not be read as dates, so no trend is shown.")
        else:
            tmp = pd.DataFrame({"p": parsed, "r": df[revenue_col]}).dropna()
            if not tmp.empty:
                span = (tmp["p"].max() - tmp["p"].min()).days
                freq, gran = ("M", "month") if span > 45 else ("D", "day")
                series = tmp.groupby(tmp["p"].dt.to_period(freq))["r"].sum().sort_index()
                points = [{"period": str(k), "revenue": float(v)} for k, v in series.items()]
                change = None
                if len(points) >= 2 and points[-2]["revenue"] != 0:
                    change = round((points[-1]["revenue"] - points[-2]["revenue"]) / abs(points[-2]["revenue"]) * 100, 1)
                trend = {"granularity": gran, "points": points, "change_pct": change}

    anomalies, anomaly_count = [], 0
    if revenue_col:
        s = df[revenue_col].dropna()
        if len(s) >= 4:
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                out = df[df[revenue_col] > q3 + 1.5 * iqr].sort_values(revenue_col, ascending=False)
                anomaly_count = len(out)
                anomalies = out.head(10).to_dict(orient="records")

    return {
        "metadata": {
            "total_records": len(df),
            "total_fields": len(df.columns),
            "data_health_index": round(health_index, 1),
            "missing_cells": missing_cells,
            "duplicate_rows": duplicates,
            "anomaly_count": anomaly_count,
            "revenue_column": revenue_col,
            "cost_column": cost_col,
            "category_column": category_col,
            "date_column": date_col,
        },
        "totals": {
            "total_revenue": tot_rev,
            "total_costs": tot_cost,
            "net_profit": net_profit,
            "profit_margin": margin,
            "cost_known": cost_known,
        },
        "revenue_by_category": revenue_by_category,
        "leaderboards": {"top_items": top_items, "bottom_items": bottom_items},
        "concentration": concentration,
        "trend": trend,
        "anomalies": anomalies,
        "warnings": warnings,
    }


def build_ai_payload(facts: dict) -> dict:
    """
    Privacy-minimised, JSON-safe fact sheet for the AI provider.
    Raw dataset rows are never included: only aggregates and outlier values.
    """
    rev_col = facts["metadata"]["revenue_column"]
    top_values = [r.get(rev_col) for r in facts["anomalies"]]
    payload = {
        "metadata": facts["metadata"],
        "totals": facts["totals"],
        "revenue_by_category": dict(list(facts["revenue_by_category"].items())[:15]),
        "leaderboards": facts["leaderboards"],
        "concentration": facts["concentration"],
        "trend": facts["trend"],
        "anomaly_summary": {"count": facts["metadata"]["anomaly_count"], "top_values": top_values},
        "warnings": facts["warnings"][:10],
    }
    return to_jsonable(payload)


def derive_insights(facts: dict, currency: str = "") -> dict:
    """Rule-based, fully grounded highlights, risks and 30/60/90 actions."""
    t, m, conc, trend = facts["totals"], facts["metadata"], facts["concentration"], facts["trend"]
    highlights, risks = [], []

    highlights.append(f"Revenue totals {currency}{t['total_revenue']:,.2f} across {m['total_records']:,} records.")
    if t["cost_known"] and t["profit_margin"] is not None:
        highlights.append(f"Net profit is {currency}{t['net_profit']:,.2f}, a {t['profit_margin']:.1f}% margin.")
    elif not t["cost_known"]:
        highlights.append("Cost data was not provided, so profitability is not assessed.")
    if conc["top_category"]:
        highlights.append(f"'{conc['top_category']}' is the largest category at {conc['top1_share']:.1f}% of revenue.")
    if trend["change_pct"] is not None:
        highlights.append(f"Latest {trend['granularity']} revenue moved {trend['change_pct']:+.1f}% versus the prior {trend['granularity']}.")

    if not t["cost_known"]:
        risks.append("No cost data: profit and margin cannot be assessed.")
    elif t["net_profit"] is not None and t["net_profit"] < 0:
        risks.append(f"Loss-making: net profit is {currency}{t['net_profit']:,.2f}.")
    elif t["profit_margin"] is not None and t["profit_margin"] < 10:
        risks.append(f"Thin margin of {t['profit_margin']:.1f}% leaves little buffer against cost increases.")
    if conc["top_category"] and conc["top1_share"] >= 40:
        risks.append(f"Concentration: '{conc['top_category']}' drives {conc['top1_share']:.1f}% of revenue.")
    if m["anomaly_count"] > 0:
        risks.append(f"{m['anomaly_count']} unusually large transaction(s) could distort totals.")
    if m["duplicate_rows"] > 0:
        risks.append(f"{m['duplicate_rows']} duplicate row(s) may inflate figures.")
    if m["data_health_index"] < 95:
        risks.append(f"Data health index is {m['data_health_index']}%, so some figures may be incomplete.")
    if trend["change_pct"] is not None and trend["change_pct"] < -5:
        risks.append(f"Revenue fell {abs(trend['change_pct']):.1f}% in the latest {trend['granularity']}.")
    if not risks:
        risks.append("Automated checks found no major risks.")

    a30 = ["Confirm the data is complete and correct."]
    if m["duplicate_rows"] or m["anomaly_count"]:
        a30.append("Review duplicate rows and unusually large transactions.")
    if not t["cost_known"]:
        a30.append("Add cost data so margin can be tracked.")
    a60 = []
    if conc["top_category"] and conc["top1_share"] >= 40:
        a60.append(f"Plan to reduce dependence on '{conc['top_category']}'.")
    if t["profit_margin"] is not None and t["profit_margin"] < 10:
        a60.append("Identify the cost lines with the most room for savings.")
    a60.append("Review the lowest-performing categories for pricing or discontinuation.")
    a90 = ["Set revenue and margin targets using the saved What-If scenarios.",
           "Re-run this analysis monthly and compare against the targets."]
    return {"highlights": highlights, "risks": risks, "actions": {"30": a30, "60": a60, "90": a90}}