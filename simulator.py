"""
Advanced Financial Scenario & Sensitivity Engine (simulator.py)
Handles multi-scenario calculations and sensitivity matrices.
Contains ZERO Streamlit imports.
"""

def calculate_scenario(totals: dict, price_adj: float, volume_adj: float, fixed_cost_change: float, variable_cost_pct: float) -> dict:
    base_rev = totals["total_revenue"]
    base_cost = totals["total_costs"]
    base_profit = totals["net_profit"]

    sim_rev = base_rev * (1 + price_adj / 100.0) * (1 + volume_adj / 100.0)
    sim_cost = (base_cost * (1 + variable_cost_pct / 100.0)) + fixed_cost_change
    sim_profit = sim_rev - sim_cost
    sim_margin = (sim_profit / sim_rev * 100.0) if sim_rev > 0 else 0.0

    return {
        "revenue": sim_rev,
        "costs": sim_cost,
        "net_profit": sim_profit,
        "profit_margin": sim_margin,
        "profit_delta": sim_profit - base_profit,
        "price_adj": price_adj,
        "volume_adj": volume_adj,
        "fixed_cost_change": fixed_cost_change,
        "variable_cost_pct": variable_cost_pct
    }

def generate_sensitivity_matrix(totals: dict) -> list:
    """Generates a matrix of net profit outcomes across price and volume variations."""
    price_steps = [-20, -10, 0, 10, 20]
    volume_steps = [-20, -10, 0, 10, 20]
    
    matrix = []
    base_rev = totals["total_revenue"]
    base_cost = totals["total_costs"]

    for p in price_steps:
        row = {"Price Adj (%)": f"{p:+d}%"}
        for v in volume_steps:
            sim_rev = base_rev * (1 + p / 100.0) * (1 + v / 100.0)
            sim_profit = sim_rev - base_cost
            row[f"Vol {v:+d}%"] = sim_profit
        matrix.append(row)
        
    return matrix