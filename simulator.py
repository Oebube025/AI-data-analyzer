"""
simulator.py - FINCH What-If Sensitivity & Simulation Engine
Incorporates symmetric price elasticity of demand and clamped volume bounds.
"""

def calculate_scenario(totals: dict, price_adj_pct: float, volume_adj_pct: float, fixed_change: float, var_pct: float, fixed_share: float, elasticity: float = 1.2):
    """
    Simulates financial performance with symmetric price elasticity (price cuts boost volume, price hikes reduce volume),
    clamping volume at zero so revenue and profit remain valid.
    """
    base_rev = totals.get("total_revenue", 0)
    base_costs = totals.get("total_costs", 0)
    
    # Symmetric elasticity: raising price reduces volume; lowering price increases volume
    effective_volume_adj = volume_adj_pct - (price_adj_pct * elasticity)
    
    price_multiplier = 1.0 + (price_adj_pct / 100.0)
    volume_multiplier = max(0.0, 1.0 + (effective_volume_adj / 100.0))
    
    sim_revenue = base_rev * price_multiplier * volume_multiplier
    
    fixed_costs = base_costs * fixed_share + fixed_change
    variable_costs = base_costs * (1.0 - fixed_share) * volume_multiplier * (1.0 + var_pct / 100.0)
    sim_costs = max(0.0, fixed_costs + variable_costs)
    
    sim_net_profit = sim_revenue - sim_costs
    base_profit = base_rev - base_costs
    profit_delta = sim_net_profit - base_profit
    
    profit_margin = (sim_net_profit / sim_revenue * 100.0) if sim_revenue > 0 else 0.0
    
    return {
        "revenue": sim_revenue,
        "costs": sim_costs,
        "net_profit": sim_net_profit,
        "profit_margin": profit_margin,
        "profit_delta": profit_delta
    }

def generate_sensitivity_matrix(totals: dict, fixed_share: float, elasticity: float = 1.2):
    price_steps = [-20, -10, 0, 10, 20]
    volume_steps = [-20, -10, 0, 10, 20]
    
    matrix = []
    for p in price_steps:
        row = {"Price Change": f"{p:+}%"}
        for v in volume_steps:
            res = calculate_scenario(totals, p, v, 0.0, 0.0, fixed_share, elasticity)
            row[f"Vol {v:+}%"] = round(res["net_profit"], 2)
        matrix.append(row)
        
    return matrix