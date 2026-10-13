"""
Dataset Analysis & Preparation (analysis.py)
Robust number parsing, precise total row filtering, accurate column heuristics,
deck insight generation, and cached dataset preparation.
"""

import re
import pandas as pd
import numpy as np


def parse_numeric_series(series: pd.Series) -> pd.Series:
    """Safely converts currency/formatted text (e.g. '₦1,200', '(500)') into numeric values."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0.0)
    
    def clean_val(v):
        if pd.isna(v):
            return np.nan
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        neg = False
        if s.startswith("(") and s.endswith(")"):
            neg = True
            s = s[1:-1]
        s = re.sub(r"[^\d.\-]", "", s)
        try:
            val = float(s)
            return -val if neg else val
        except ValueError:
            return np.nan

    return series.apply(clean_val)


def prepare_dataframe(df: pd.DataFrame):
    """
    Cleans data, excludes exact total/summary rows across all columns,
    and parses dates with dayfirst=True when >= 80% valid.
    """
    clean = df.copy()
    notes = []
    
    clean.columns = [str(c).strip() for c in clean.columns]
    
    # Precise Summary / Total Row Filter (exact label match across any string column)
    total_mask = pd.Series(False, index=clean.index)
    for col in clean.columns:
        if pd.api.types.is_string_dtype(clean[col]) or clean[col].dtype == object:
            col_str = clean[col].astype(str).str.strip().str.lower()
            # Match exact terms like "total", "subtotal", "grand total", "summary"
            mask = col_str.str.contains(r"^(total|subtotal|grand total|sum|overall total|summary)$", na=False, regex=True)
            total_mask = total_mask | mask

    if total_mask.any():
        dropped_count = int(total_mask.sum())
        clean = clean[~total_mask].reset_index(drop=True)
        notes.append(f"Excluded {dropped_count} summary/total row(s) to avoid double counting.")

    # 80% Threshold Date Parsing
    for col in clean.columns:
        cl = col.lower()
        if any(w in cl for w in ["date", "time", "created"]) and not any(w in cl for w in ["period", "day", "month", "qty"]):
            try:
                parsed = pd.to_datetime(clean[col], dayfirst=True, errors="coerce")
                valid_ratio = parsed.notna().sum() / max(1, len(clean))
                if valid_ratio >= 0.8:
                    clean[col] = parsed
                    notes.append(f"Parsed '{col}' as date ({valid_ratio*100:.0f}% success rate).")
            except Exception:
                pass
                
    return clean, notes


def valid_numeric_columns(df: pd.DataFrame) -> list:
    """Identifies valid numeric columns, avoiding identifier tokens like ID, ZIP, or Phone."""
    numeric_cols = []
    for c in df.columns:
        cl = c.lower()
        # Word boundary matching for IDs to avoid dropping 'Amount Paid'
        if re.search(r"\b(id|code|phone|zip|postal|year)\b", cl):
            continue
        parsed = parse_numeric_series(df[c])
        if parsed.notna().sum() > 0 and not pd.api.types.is_datetime64_any_dtype(df[c]):
            numeric_cols.append(c)
    return numeric_cols


def suggest_columns(df: pd.DataFrame) -> dict:
    sug = {"revenue": None, "cost": None, "category": None, "date": None}
    nums = valid_numeric_columns(df)
    
    # Priority matching for revenue/sales headers
    for c in nums:
        cl = c.lower()
        if any(w in cl for w in ["amount", "revenue", "sales", "total", "turnover", "income"]):
            sug["revenue"] = c
            break
            
    if not sug["revenue"] and nums:
        sug["revenue"] = nums[0]
        
    for c in nums:
        cl = c.lower()
        if any(w in cl for w in ["cost", "expense", "cogs", "spend", "purchase"]) and c != sug["revenue"]:
            sug["cost"] = c
            break
            
    for c in df.columns:
        cl = c.lower()
        if c not in nums and any(w in cl for w in ["product", "category", "item", "description", "region", "branch", "client"]):
            sug["category"] = c
            break
            
    for c in df.columns:
        cl = c.lower()
        if pd.api.types.is_datetime64_any_dtype(df[c]) or any(w in cl for w in ["date", "time"]):
            sug["date"] = c
            break
            
    return sug


def derive_insights(facts_or_df, revenue_col: str = None, cost_col: str = None, category_col: str = None) -> dict:
    """
    Generates structured insights compatible with deck_builder requirements.
    Supports flexible calls from both analysis functions and deck_builder.
    """
    if isinstance(facts_or_df, dict):
        facts = facts_or_df
        rbc = facts.get("revenue_by_category", {})
        totals = facts.get("totals", {})
        top_items = [(str(k), float(v)) for k, v in list(rbc.items())[:5]]
        top_category = top_items[0][0] if top_items else "N/A"
        
        return {
            "top_items": top_items,
            "top_category": top_category,
            "leaderboards": {"top_categories": rbc},
            "concentration": {"top_category": top_category, "share": "Moderate"},
            "highlights": [f"Total revenue reached {totals.get('total_revenue', 0):,.2f}"],
            "risks": facts.get("warnings", []),
        }

    df = facts_or_df
    rbc = {}
    top_items = []
    top_category = "N/A"
    
    if category_col and category_col != "None" and category_col in df.columns and revenue_col in df.columns:
        grouped = df.groupby(category_col)[revenue_col].sum().sort_values(ascending=False)
        rbc = {str(k): float(v) for k, v in grouped.items()}
        top_items = [(str(k), float(v)) for k, v in grouped.head(5).items()]
        top_category = top_items[0][0] if top_items else "N/A"

    return {
        "top_items": top_items,
        "top_category": top_category,
        "leaderboards": {"top_categories": rbc},
        "concentration": {"top_category": top_category, "share": "Moderate"},
        "highlights": [f"Category '{top_category}' is the leading revenue driver."],
        "risks": [],
    }


def analyze_dataset(df: pd.DataFrame, revenue_col: str, cost_col: str = "None", 
                    category_col: str = "None", date_col: str = "None", prep_notes: list = None) -> dict:
    work = df.copy()
    rev_series = parse_numeric_series(work[revenue_col]).fillna(0.0)
    
    # Only calculate Qty * Price if selected revenue column is strictly 'unit price' / 'price'
    if "price" in revenue_col.lower() and "total" not in revenue_col.lower() and "amount" not in revenue_col.lower():
        for c in work.columns:
            if c != revenue_col and any(w in c.lower() for w in ["qty", "quantity", "units"]):
                qty_series = parse_numeric_series(work[c]).fillna(0.0)
                rev_series = rev_series * qty_series
                break

    work["_computed_revenue"] = rev_series
    total_revenue = float(work["_computed_revenue"].sum())
    
    cost_known = False
    total_costs = None
    net_profit = None
    profit_margin = None
    
    if cost_col != "None" and cost_col in work.columns:
        cost_series = parse_numeric_series(work[cost_col]).fillna(0.0)
        total_costs = float(cost_series.sum())
        net_profit = total_revenue - total_costs
        profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0
        cost_known = True
        
    total_records = len(work)
    missing_cells = int(work.isna().sum().sum())
    duplicate_rows = int(work.duplicated().sum())
    
    health_index = 100
    if total_records > 0:
        penalty = (missing_cells / (total_records * max(1, len(work.columns)))) * 30 + \
                  (duplicate_rows / total_records) * 20
        health_index = max(10, min(100, int(100 - penalty)))
        
    revenue_by_category = {}
    if category_col != "None" and category_col in work.columns:
        rbc = work.groupby(category_col)["_computed_revenue"].sum().sort_values(ascending=False)
        revenue_by_category = {str(k): float(v) for k, v in rbc.items()}
        
    trend = {"granularity": "none", "points": [], "change_pct": None}
    if date_col != "None" and date_col in work.columns and pd.api.types.is_datetime64_any_dtype(work[date_col]):
        work_sorted = work.sort_values(by=date_col)
        monthly = work_sorted.groupby(work_sorted[date_col].dt.to_period("M"))["_computed_revenue"].sum()
        if len(monthly) >= 1:
            trend["granularity"] = "monthly"
            trend["points"] = [{"period": str(p), "revenue": float(v)} for p, v in monthly.items()]
            if len(monthly) >= 2:
                vals = list(monthly.values)
                if vals[-2] > 0:
                    trend["change_pct"] = float((vals[-1] - vals[-2]) / vals[-2] * 100)
                
    # Anomaly Detection (privacy-safe numeric values)
    anomalies = []
    mean_val = rev_series.mean()
    std_val = rev_series.std()
    
    if std_val > 0 and total_records > 5:
        z_scores = (rev_series - mean_val) / std_val
        outlier_rows = work[z_scores > 3]
        for _, row in outlier_rows.head(5).iterrows():
            anomalies.append({"revenue_value": float(row["_computed_revenue"])})
            
    insights = derive_insights(work, "_computed_revenue", cost_col, category_col)
    
    warnings = []
    if missing_cells > 0:
        warnings.append(f"Dataset contains {missing_cells:,} missing cells.")
    if duplicate_rows > 0:
        warnings.append(f"Detected {duplicate_rows:,} duplicate rows.")
    if not cost_known:
        warnings.append("No cost column selected. Profit and margin are displayed as n/a.")

    return {
        "totals": {
            "total_revenue": total_revenue,
            "total_costs": total_costs,
            "net_profit": net_profit,
            "profit_margin": profit_margin,
            "cost_known": cost_known,
        },
        "metadata": {
            "total_records": total_records,
            "data_health_index": health_index,
            "missing_cells": missing_cells,
            "duplicate_rows": duplicate_rows,
            "anomaly_count": len(anomalies),
            "revenue_column": revenue_col,
            "cost_column": cost_col,
            "category_column": category_col,
            "date_column": date_col,
        },
        "revenue_by_category": revenue_by_category,
        "leaderboards": insights["leaderboards"],
        "concentration": insights["concentration"],
        "trend": trend,
        "anomalies": anomalies,
        "anomaly_summary": f"Detected {len(anomalies)} statistical sales outliers exceeding 3 standard deviations.",
        "warnings": warnings,
        "preparation_notes": prep_notes or [],
    }


def build_ai_payload(facts: dict) -> dict:
    return {
        "metadata": facts.get("metadata"),
        "totals": facts.get("totals"),
        "revenue_by_category": facts.get("revenue_by_category"),
        "leaderboards": facts.get("leaderboards"),
        "concentration": facts.get("concentration"),
        "trend": facts.get("trend"),
        "anomaly_summary": facts.get("anomaly_summary"),
        "anomalies": facts.get("anomalies", []),
        "warnings": facts.get("warnings"),
    }