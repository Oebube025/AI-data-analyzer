"""
SME Data Intelligence Fact Engine (analysis.py)
Automated column role detection, quality auditing, and metric aggregation.
Contains ZERO Streamlit dependencies.
"""

import pandas as pd
import numpy as np

def auto_detect_columns(df: pd.DataFrame) -> dict:
    """
    Intelligently auto-detects column roles for SMEs to minimize manual setup.
    """
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
    
    # Filter out numeric ID/code columns
    valid_nums = [c for c in num_cols if not any(k in c.lower() for k in ['id', 'code', 'zip', 'year', 'phone'])]
    
    # Auto-detect Revenue / Sales column
    rev_keywords = ['revenue', 'sales', 'total', 'amount', 'income', 'price', 'units_sold', 'turnover']
    sel_rev = next((c for c in valid_nums if any(k in c.lower() for k in rev_keywords)), valid_nums[0] if valid_nums else (num_cols[0] if num_cols else ""))
    
    # Auto-detect Cost / Expense column
    cost_keywords = ['cost', 'expense', 'cogs', 'spending', 'payout', 'unit_cost', 'fee']
    sel_cost = next((c for c in valid_nums if any(k in c.lower() for k in cost_keywords) and c != sel_rev), "None")
    
    # Auto-detect Category / Product / Client column
    cat_keywords = ['category', 'product', 'item', 'group', 'service', 'type', 'channel', 'client', 'customer', 'branch']
    sel_cat = next((c for c in cat_cols if any(k in c.lower() for k in cat_keywords)), cat_cols[0] if cat_cols else "None")
    
    # Auto-detect Date column
    date_cols = [c for c in df.columns if any(k in c.lower() for k in ['date', 'time', 'month', 'period', 'created', 'day'])]
    sel_date = date_cols[0] if date_cols else "None"
    
    return {
        "revenue_col": sel_rev,
        "cost_col": sel_cost,
        "category_col": sel_cat,
        "date_col": sel_date
    }

def analyze_dataset(df: pd.DataFrame, revenue_col: str, cost_col: str = "None", category_col: str = "None") -> dict:
    warnings = []
    
    if revenue_col not in df.columns:
        return {"warnings": ["Revenue column not found."], "totals": {}, "metadata": {}}

    rev_series = pd.to_numeric(df[revenue_col], errors='coerce').fillna(0)
    total_rev = float(rev_series.sum())
    
    if cost_col != "None" and cost_col in df.columns:
        cost_series = pd.to_numeric(df[cost_col], errors='coerce').fillna(0)
        total_cost = float(cost_series.sum())
    else:
        total_cost = 0.0
        warnings.append("No cost column selected. Operating expense tracking is disabled.")

    net_profit = total_rev - total_cost
    margin = (net_profit / total_rev * 100.0) if total_rev > 0 else 0.0

    # SME Data Quality Audit
    total_cells = df.size
    missing_cells = int(df.isnull().sum().sum())
    dup_rows = int(df.duplicated().sum())
    health_index = round(100.0 * (1.0 - (missing_cells + dup_rows) / max(total_cells, 1)), 1)

    # Category Breakdown & Leaderboards
    category_rev = {}
    top_items = []
    bottom_items = []
    
    if category_col != "None" and category_col in df.columns:
        grouped = df.groupby(category_col)[revenue_col].sum().sort_values(ascending=False)
        category_rev = {str(k): float(v) for k, v in grouped.items()}
        
        top_df = grouped.head(5).reset_index()
        bottom_df = grouped.tail(5).reset_index()
        top_items = top_df.to_dict(orient="records")
        bottom_items = bottom_df.to_dict(orient="records")

    # IQR Anomaly / Outlier Detection
    anomalies = []
    q1 = rev_series.quantile(0.25)
    q3 = rev_series.quantile(0.75)
    iqr = q3 - q1
    if iqr > 0:
        outlier_mask = (rev_series < (q1 - 1.5 * iqr)) | (rev_series > (q3 + 1.5 * iqr))
        outlier_df = df[outlier_mask]
        if not outlier_df.empty:
            anomalies = outlier_df.head(10).to_dict(orient="records")

    return {
        "metadata": {
            "total_records": len(df),
            "total_fields": len(df.columns),
            "data_health_index": max(0.0, health_index),
            "missing_cells": missing_cells,
            "duplicate_rows": dup_rows,
            "revenue_column": revenue_col,
            "cost_column": cost_col,
            "category_column": category_col
        },
        "totals": {
            "total_revenue": total_rev,
            "total_costs": total_cost,
            "net_profit": net_profit,
            "profit_margin": round(margin, 2)
        },
        "revenue_by_category": category_rev,
        "leaderboards": {
            "top_items": top_items,
            "bottom_items": bottom_items
        },
        "anomalies": anomalies,
        "warnings": warnings
    }