"""
Financial Scenario & Sensitivity Engine (simulator.py)
Uses an explicit fixed/variable cost split:
  - variable costs scale with volume (and with the variable cost adjustment)
  - fixed costs do not scale with volume
  - price changes affect revenue only
Contains ZERO Streamlit imports.
"""

DEFAULT_FIXED_SHARE = 0.30


def _split_costs(base_cost: float, fixed_share: float):
    fixed_share = min(max(fixed_share, 0.0), 1.0)
    return base_cost * fixed_share, base_cost * (1.0 - fixed_share)


def _simulate(base_rev, base_cost, price_adj, volume_adj, fixed_cost_change, variable_cost_pct, fixed_share):
    base_fixed, base_var = _split_costs(base_cost, fixed_share)
    vol = 1 + volume_adj / 100.0
    rev = base_rev * (1 + price_adj / 100.0) * vol
    var_cost = base_var * vol * (1 + variable_cost_pct / 100.0)
    fixed_cost = max(0.0, base_fixed + fixed_cost_change)
    return rev, var_cost + fixed_cost


def calculate_scenario(totals: dict, price_adj: float, volume_adj: float, fixed_cost_change: float,
                       variable_cost_pct: float, fixed_cost_share: float = DEFAULT_FIXED_SHARE) -> dict:
    base_rev = totals.get("total_revenue", 0.0)
    base_cost = totals.get("total_costs", 0.0)
    base_profit = base_rev - base_cost

    sim_rev, sim_cost = _simulate(base_rev, base_cost, price_adj, volume_adj,
                                  fixed_cost_change, variable_cost_pct, fixed_cost_share)
    sim_profit = sim_rev - sim_cost
    sim_margin = (sim_profit / sim_rev * 100.0) if sim_rev > 0 else None

    return {
        "revenue": sim_rev,
        "costs": sim_cost,
        "net_profit": sim_profit,
        "profit_margin": sim_margin,
        "profit_delta": sim_profit - base_profit,
        "price_adj": price_adj,
        "volume_adj": volume_adj,
        "fixed_cost_change": fixed_cost_change,
        "variable_cost_pct": variable_cost_pct,
        "fixed_cost_share": fixed_cost_share,
    }


def generate_sensitivity_matrix(totals: dict, fixed_cost_share: float = DEFAULT_FIXED_SHARE) -> list:
    """Net profit across price x volume changes, with variable costs scaling with volume."""
    steps = [-20, -10, 0, 10, 20]
    matrix = []
    base_rev = totals.get("total_revenue", 0.0)
    base_cost = totals.get("total_costs", 0.0)
    for p in steps:
        row = {"Price Adj (%)": f"{p:+d}%"}
        for v in steps:
            rev, cost = _simulate(base_rev, base_cost, p, v, 0.0, 0.0, fixed_cost_share)
            row[f"Vol {v:+d}%"] = rev - cost
        matrix.append(row)
    return matrix