"""
Core Analytics Fact Sheet Engine (analysis.py)
Phase 1: Centralized Single Source of Truth for Dashboard, Deck, and AI Advisor.
Contains ZERO Streamlit or FastAPI imports.
"""

import pandas as pd
import numpy as np

def analyze_dataset(df: pd.DataFrame, revenue_col: str = None, cost_col: str = None, category_col: str = None) -> dict:
    warnings = []
    
    # 1. Detect potential summary/totals rows
    for col in df.columns:
        if df[col].astype(str).str.contains(r'^(total|sum|overall)', case=False, na=False).any():
            warnings.append(f"Potential summary/total row detected in column '{col}'.")
    
    # Identify numeric columns and clean text-numeric formats (currency symbols, commas, brackets)
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    for col in df.columns:
        if col not in num_cols:
            sample = df[col].dropna().head(20).astype(str)
            if sample.str.contains(r'[₦$€£,\(\)]', regex=True).any():
                try:
                    converted = sample.str.replace(r'[₦$€£,]', '', regex=True).str.replace(r'\((.*?)\)', r'-\1', regex=True)
                    pd.to_numeric(converted, errors='raise')
                    df[col] = df[col].astype(str).str.replace(r'[₦$€£,]', '', regex=True).str.replace(r'\((.*?)\)', r'-\1', regex=True)
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    num_cols.append(col)
                    warnings.append(f"Converted text-numeric column '{col}' to numeric format.")
                except Exception:
                    pass

    # Auto-select revenue and cost columns if not provided
    valid_nums = [c for c in num_cols if not any(k in c.lower() for k in ['id', 'code', 'year'])]
    if not revenue_col or revenue_col not in df.columns:
        revenue_col = valid_nums[0] if valid_nums else (num_cols[0] if num_cols else None)
    
    if not cost_col or cost_col not in df.columns or cost_col == "None":
        cost_candidates = [c for c in valid_nums if c != revenue_col and any(k in c.lower() for k in ['cost', 'expense', 'cogs'])]
        cost_col = cost_candidates[0] if cost_candidates else "None"

    # Calculate core financials
    tot_rev = float(df[revenue_col].sum()) if revenue_col and revenue_col in df else 0.0
    tot_cost = float(df[cost_col].sum()) if cost_col != "None" and cost_col in df else 0.0
    net_profit = tot_rev - tot_cost
    profit_margin = (net_profit / tot_rev * 100) if tot_rev > 0 else 0.0

    # Data Health Index & Audits
    total_cells = df.size
    missing_cells = int(df.isna().sum().sum())
    health_index = max(0.0, min(100.0, ((total_cells - missing_cells) / max(1, total_cells)) * 100))
    duplicates = int(df.duplicated().sum())

    # Category breakdowns & leaderboards
    cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
    if not category_col or category_col not in df.columns:
        category_col = cat_cols[0] if cat_cols else None

    revenue_by_category = {}
    top_items = []
    bottom_items = []
    if category_col and revenue_col and category_col in df and revenue_col in df:
        grouped = df.groupby(category_col)[revenue_col].sum().reset_index().sort_values(by=revenue_col, ascending=False)
        revenue_by_category = grouped.set_index(category_col)[revenue_col].to_dict()
        top_items = grouped.head(5).to_dict(orient="records")
        bottom_items = grouped.tail(5).to_dict(orient="records")

    # IQR Anomaly Detection
    anomalies = []
    if revenue_col and revenue_col in df:
        q1 = df[revenue_col].quantile(0.25)
        q3 = df[revenue_col].quantile(0.75)
        iqr = q3 - q1
        upper_bound = q3 + 1.5 * iqr
        outlier_df = df[df[revenue_col] > upper_bound]
        anomalies = outlier_df.head(10).to_dict(orient="records")

    return {
        "metadata": {
            "total_records": len(df),
            "total_fields": len(df.columns),
            "data_health_index": round(health_index, 1),
            "missing_cells": missing_cells,
            "duplicate_rows": duplicates,
            "revenue_column": revenue_col,
            "cost_column": cost_col,
            "category_column": category_col
        },
        "totals": {
            "total_revenue": tot_rev,
            "total_costs": tot_cost,
            "net_profit": net_profit,
            "profit_margin": round(profit_margin, 2)
        },
        "revenue_by_category": revenue_by_category,
        "leaderboards": {
            "top_items": top_items,
            "bottom_items": bottom_items
        },
        "anomalies": anomalies,
        "warnings": warnings
    }