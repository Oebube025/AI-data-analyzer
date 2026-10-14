"""
simulator.py - FINCH What-If Sensitivity & Simulation Engine
Incorporates price elasticity modeling and profit matrix generation.
"""

import pandas as pd
import numpy as np

def calculate_scenario(totals: dict, price_adj_pct: float, volume_adj_pct: float, fixed_change: float, var_pct: float, fixed_share: float):
    """
    Simulates financial performance under price, volume, and cost adjustments,
    factoring in price elasticity of demand (raising prices reduces volume slightly unless elastic).
    """
    base_rev = totals.get("total_revenue", 0)
    base_costs = totals.get("total_costs", 0)
    
    # Apply standard price elasticity (e.g. elasticity coefficient = 1.2)
    elasticity = 1.2
    effective_volume_adj = volume_adj_pct - (price_adj_pct * elasticity) if price_adj_pct > 0 else volume_adj_pct
    
    price_multiplier = 1 + (price_adj_pct / 100.0)
    volume_multiplier = 1 + (effective_volume_adj / 100.0)
    
    sim_revenue = base_rev * price_multiplier * volume_multiplier
    
    fixed_costs = base_costs * fixed_share + fixed_change
    variable_costs = base_costs * (1 - fixed_share) * volume_multiplier * (1 + var_pct / 100.0)
    sim_costs = max(0.0, fixed_costs + variable_costs)
    
    sim_net_profit = sim_revenue - sim_costs
    base_profit = base_rev - base_costs
    profit_delta = sim_net_profit - base_profit
    
    profit_margin = (sim_net_profit / sim_revenue * 100) if sim_revenue > 0 else 0.0
    
    return {
        "revenue": sim_revenue,
        "costs": sim_costs,
        "net_profit": sim_net_profit,
        "profit_margin": profit_margin,
        "profit_delta": profit_delta
    }

def generate_sensitivity_matrix(totals: dict, fixed_share: float):
    """Generates a 5x5 profit sensitivity matrix across price and volume changes."""
    price_steps = [-20, -10, 0, 10, 20]
    volume_steps = [-20, -10, 0, 10, 20]
    
    matrix = []
    for p in price_steps:
        row = {"Price Change": f"{p:+}%"}
        for v in volume_steps:
            res = calculate_scenario(totals, p, v, 0.0, 0.0, fixed_share)
            row[f"Vol {v:+}%"] = round(res["net_profit"], 2)
        matrix.append(row)
        
    return matrix