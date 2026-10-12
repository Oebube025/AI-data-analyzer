"""
SME What-If Simulator & Price Calculator (simulator.py)
Calculates business growth scenarios and profit sensitivity grids.
Contains ZERO Streamlit dependencies.
"""

def calculate_scenario(totals: dict, price_adj: float, volume_adj: float, fixed_cost_change: float, variable_cost_pct: float) -> dict:
    base_rev = totals.get("total_revenue", 0.0)
    base_cost = totals.get("total_costs", 0.0)
    base_profit = totals.get("net_profit", 0.0)

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
    """Generates a matrix showing estimated take-home profit across price vs sales volume shifts."""
    price_steps = [-15, -5, 0, 5, 15]
    volume_steps = [-15, -5, 0, 5, 15]
    
    matrix = []
    base_rev = totals.get("total_revenue", 0.0)
    base_cost = totals.get("total_costs", 0.0)

    for p in price_steps:
        row = {"Price Shift (%)": f"{p:+d}%"}
        for v in volume_steps:
            sim_rev = base_rev * (1 + p / 100.0) * (1 + v / 100.0)
            sim_profit = sim_rev - base_cost
            row[f"Sales Vol {v:+d}%"] = sim_profit
        matrix.append(row)
        
    return matrix