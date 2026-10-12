"""
Persistent Session Database (database.py)
Stores saved business scenarios using DuckDB.
Contains ZERO Streamlit dependencies.
"""

import duckdb
import json
import os

DB_FILE = "sme_intelligence.duckdb"

def init_db():
    conn = duckdb.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS saved_scenarios (
            id INTEGER PRIMARY KEY,
            session_id VARCHAR,
            scenario_name VARCHAR,
            revenue DOUBLE,
            costs DOUBLE,
            net_profit DOUBLE,
            margin DOUBLE,
            details VARCHAR
        )
    """)
    conn.close()

def save_scenario_db(session_id: str, name: str, res: dict):
    init_db()
    conn = duckdb.connect(DB_FILE)
    conn.execute("""
        INSERT INTO saved_scenarios (session_id, scenario_name, revenue, costs, net_profit, margin, details)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [session_id, name, res["revenue"], res["costs"], res["net_profit"], res["profit_margin"], json.dumps(res)])
    conn.close()

def load_scenarios_db(session_id: str) -> list:
    if not os.path.exists(DB_FILE):
        return []
    conn = duckdb.connect(DB_FILE)
    try:
        df = conn.execute("SELECT scenario_name, revenue, costs, net_profit, margin, details FROM saved_scenarios WHERE session_id = ?", [session_id]).fetchdf()
        return df.to_dict(orient="records")
    except Exception:
        return []
    finally:
        conn.close()