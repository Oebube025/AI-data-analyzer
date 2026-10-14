"""
analysis.py - FINCH Data Analysis & Parsing Engine
Handles data cleaning, numeric series detection, anomaly detection, and AI payload compilation.
"""

import re
import pandas as pd
import numpy as np

FORBIDDEN_COL_PATTERNS = re.compile(r"(id|code|zip|phone|date|status|email|year|month|day|index|ref)", re.IGNORECASE)

def prepare_dataframe(df: pd.DataFrame):
    """Cleans dataframe columns and parses numeric/date types safely."""
    notes = []
    df = df.copy()
    
    # Strip whitespace from column headers
    df.columns = [str(c).strip() for c in df.columns]
    
    # Drop completely empty rows and columns
    before_rows = len(df)
    df.dropna(how="all", inplace=True)
    if len(df) < before_rows:
        notes.append(f"Removed {before_rows - len(df)} completely empty rows.")

    return df, notes

def parse_numeric_series(series: pd.Series) -> pd.Series:
    """Safely parses numeric columns, handling currency symbols, commas, and European formats."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    
    cleaned = series.astype(str).str.replace(r"[^\d.,\-]", "", regex=True)
    # Check if European format (e.g. 1.200,50)
    sample = cleaned.dropna().head(20).astype(str)
    if any("," in s and "." in s and s.rfind(",") > s.rfind(".") for s in sample):
        cleaned = cleaned.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    else:
        cleaned = cleaned.str.replace(",", "", regex=False)
        
    return pd.to_numeric(cleaned, errors="coerce")

def valid_numeric_columns(df: pd.DataFrame) -> list:
    """Returns columns that are valid numeric candidates, excluding IDs and codes."""
    valid = []
    for col in df.columns:
        if FORBIDDEN_COL_PATTERNS.search(col):
            continue
        parsed = parse_numeric_series(df[col])
        if parsed.notna().sum() > 0.3 * len(df):  # At least 30% valid numbers
            valid.append(col)
    return valid

def suggest_columns(df: pd.DataFrame):
    """Suggests best-fit columns for revenue, cost, category, and date."""
    nums = valid_numeric_columns(df)
    cats = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
    
    rev_col = nums[0] if nums else (df.columns[0] if len(df.columns) > 0 else None)
    for c in nums:
        if re.search(r"(revenue|sales|amount|total|price|gross|income)", c, re.IGNORECASE):
            rev_col = c
            break
            
    cost_col = "None"
    for c in nums:
        if c != rev_col and re.search(r"(cost|expense|cogs|spend)", c, re.IGNORECASE):
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
    """Executes the complete statistical audit and anomaly detection."""
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
    
    # Category revenue breakdown
    revenue_by_category = {}
    if category_col and category_col != "None" and category_col in df.columns:
        cat_df = pd.DataFrame({"category": df[category_col].astype(str), "revenue": rev_series})
        grouped = cat_df.groupby("category")["revenue"].sum().sort_values(ascending=False)
        revenue_by_category = grouped.to_dict()

    # Anomaly detection (Fixed Phase 2: compute total anomalies before slicing)
    anomalies = []
    if len(rev_series.dropna()) > 5:
        mean_val = rev_series.mean()
        std_val = rev_series.std()
        if std_val > 0:
            threshold = mean_val + (3 * std_val)
            outlier_df = df[rev_series > threshold].copy()
            outlier_df["parsed_revenue"] = rev_series[rev_series > threshold]
            for idx, row in outlier_df.iterrows():
                anomalies.append({
                    "row_index": int(idx),
                    "revenue": float(row["parsed_revenue"]),
                    "category": str(row[category_col]) if category_col != "None" and category_col in df.columns else "N/A"
                })
                
    anomaly_count = len(anomalies)

    # Trends calculation
    trend_points = []
    granularity = "None"
    change_pct = None
    if date_col and date_col != "None" and date_col in df.columns:
        try:
            dates = pd.to_datetime(df[date_col], errors="coerce")
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

    data_health_index = 100
    missing_cells = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())
    if missing_cells > 0:
        data_health_index -= min(15, int((missing_cells / (len(df) * max(1, len(df.columns)))) * 100))
    if duplicate_rows > 0:
        data_health_index -= min(15, int((duplicate_rows / len(df)) * 100))

    totals = {
        "total_revenue": total_revenue,
        "total_costs": total_costs,
        "cost_known": cost_known,
        "net_profit": net_profit,
        "profit_margin": profit_margin
    }
    
    metadata = {
        "total_rows": len(df),
        "data_health_index": max(0, data_health_index),
        "missing_cells": missing_cells,
        "duplicate_rows": duplicate_rows,
        "anomaly_count": anomaly_count
    }
    
    trend = {
        "granularity": granularity,
        "points": trend_points,
        "change_pct": change_pct
    }

    return {
        "totals": totals,
        "metadata": metadata,
        "trend": trend,
        "revenue_by_category": revenue_by_category,
        "anomalies": anomalies,
        "warnings": warnings
    }

def build_ai_payload(facts: dict) -> dict:
    """Prepares concise, privacy-safe aggregated facts for AI prompt execution."""
    rbc = facts.get("revenue_by_category", {})
    top_categories = dict(list(rbc.items())[:10]) # Truncate to top 10 categories to avoid payload bloat
    return {
        "totals": facts.get("totals", {}),
        "metadata": facts.get("metadata", {}),
        "top_categories": top_categories,
        "anomaly_count": len(facts.get("anomalies", []))
    }