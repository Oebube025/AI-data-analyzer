"""
analysis.py - FINCH Data Analysis & Parsing Engine
"""
import re
import pandas as pd
import numpy as np

FORBIDDEN_COL_PATTERNS = re.compile(r"\b(id|code|zip|phone|status|email|year|month|day|index|ref)\b", re.IGNORECASE)

def prepare_dataframe(df: pd.DataFrame):
    notes = []
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    
    before_rows = len(df)
    df.dropna(how="all", inplace=True)
    
    if len(df) > 0:
        for col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                mask = df[col].astype(str).str.contains(r"^(total|grand total|sum|subtotal)$", case=False, na=False, regex=True)
                if mask.any():
                    df = df[~mask]
                    notes.append(f"Removed {mask.sum()} summary/total row(s) detected in column '{col}'.")
                    break

    if len(df) < before_rows:
        notes.append(f"Removed {before_rows - len(df)} empty/summary rows.")

    return df, notes

def parse_numeric_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    
    sample = series.dropna().astype(str)
    if any(re.search(r"[A-Za-z]", s) for s in sample.head(10)):
        return pd.Series([np.nan] * len(series))

    cleaned = series.astype(str).str.replace(r"[^\d.,\-]", "", regex=True)
    sample_clean = cleaned.dropna().head(20).astype(str)
    if any("," in s and "." in s and s.rfind(",") > s.rfind(".") for s in sample_clean):
        cleaned = cleaned.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    else:
        cleaned = cleaned.str.replace(",", "", regex=False)
        
    return pd.to_numeric(cleaned, errors="coerce")

def valid_numeric_columns(df: pd.DataFrame) -> list:
    valid = []
    for col in df.columns:
        if FORBIDDEN_COL_PATTERNS.search(col):
            continue
        parsed = parse_numeric_series(df[col])
        if parsed.notna().sum() > 0.2 * len(df):
            valid.append(col)
    return valid

def suggest_columns(df: pd.DataFrame):
    nums = valid_numeric_columns(df)
    cats = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
    
    rev_col = nums[0] if nums else (df.columns[0] if len(df.columns) > 0 else None)
    for c in nums:
        if re.search(r"(revenue|sales|amount|total|price|gross|income|paid)", c, re.IGNORECASE):
            rev_col = c
            break
            
    cost_col = "None"
    for c in nums:
        if c != rev_col and re.search(r"(cost|expense|cogs|spend|fee)", c, re.IGNORECASE):
            cost_col = c
            break
            
    cat_col = cats[0] if cats else "None"
    for c in cats:
        if re.search(r"(category|department|region|product|store|client|branch|type)", c, re.IGNORECASE):
            cat_col = c
            break
            
    date_col = "None"
    for c in df.columns:
        if re.search(r"(date|time|period|created|timestamp)", c, re.IGNORECASE):
            date_col = c
            break
            
    return {"revenue": rev_col, "cost": cost_col, "category": cat_col, "date": date_col}

def analyze_dataset(df: pd.DataFrame, revenue_col: str, cost_col: str, category_col: str, date_col: str, prep_notes: list):
    warnings = []
    
    rev_series = parse_numeric_series(df[revenue_col]) if revenue_col in df.columns else pd.Series([0]*len(df))
    total_revenue = float(rev_series.sum())
    
    cost_known = False
    total_costs = 0.0
    if cost_col and cost_col != "None" and cost_col in df.columns:
        cost_series = parse_numeric_series(df[cost_col])
        total_costs = float(cost_series.sum())
        cost_known = True
        
    net_profit = total_revenue - total_costs if cost_known else None
    profit_margin = (net_profit / total_revenue * 100) if cost_known and total_revenue > 0 else None
    
    revenue_by_category = {}
    if category_col and category_col != "None" and category_col in df.columns:
        cat_df = pd.DataFrame({"category": df[category_col].astype(str), "revenue": rev_series})
        grouped = cat_df.groupby("category")["revenue"].sum().sort_values(ascending=False)
        revenue_by_category = grouped.to_dict()

    anomalies = []
    clean_rev = rev_series.dropna()
    if len(clean_rev) > 5:
        q1 = clean_rev.quantile(0.25)
        q3 = clean_rev.quantile(0.75)
        iqr = q3 - q1
        if iqr > 0:
            upper_bound = q3 + (1.5 * iqr)
            outlier_df = df[rev_series > upper_bound].copy()
            outlier_df["parsed_revenue"] = rev_series[rev_series > upper_bound]
            for idx, row in outlier_df.iterrows():
                anomalies.append({
                    "row_index": int(idx),
                    "revenue": float(row["parsed_revenue"]),
                    "category": str(row[category_col]) if category_col != "None" and category_col in df.columns else "N/A"
                })

    trend_points = []
    granularity = "None"
    change_pct = None
    if date_col and date_col != "None" and date_col in df.columns:
        try:
            dates = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
            trend_df = pd.DataFrame({"date": dates, "revenue": rev_series}).dropna(subset=["date"])
            if not trend_df.empty:
                trend_df["period"] = trend_df["date"].dt.to_period("M").astype(str)
                monthly = trend_df.groupby("period")["revenue"].sum().reset_index()
                trend_points = monthly.to_dict(orient="records")
                granularity = "Month"
                if len(monthly) >= 2:
                    last_val = monthly.iloc[-1]["revenue"]
                    prev_val = monthly.iloc[-2]["revenue"]
                    if prev_val > 0:
                        change_pct = ((last_val - prev_val) / prev_val) * 100
        except Exception:
            pass

    missing_cells = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())
    total_cells = max(1, len(df) * max(1, len(df.columns)))
    
    missing_penalty = int((missing_cells / total_cells) * 50)
    dup_penalty = int((duplicate_rows / max(1, len(df))) * 50)
    data_health_index = max(0, 100 - missing_penalty - dup_penalty)

    return {
        "totals": {"total_revenue": total_revenue, "total_costs": total_costs, "cost_known": cost_known, "net_profit": net_profit, "profit_margin": profit_margin},
        "metadata": {"total_rows": len(df), "data_health_index": data_health_index, "missing_cells": missing_cells, "duplicate_rows": duplicate_rows, "anomaly_count": len(anomalies)},
        "trend": {"granularity": granularity, "points": trend_points, "change_pct": change_pct},
        "revenue_by_category": revenue_by_category,
        "anomalies": anomalies,
        "warnings": warnings
    }

def build_ai_payload(facts: dict) -> dict:
    return {
        "totals": facts.get("totals", {}),
        "metadata": facts.get("metadata", {}),
        "revenue_by_category": facts.get("revenue_by_category", {}),
        "trend": facts.get("trend", {}),
        "anomaly_count": len(facts.get("anomalies", []))
    }