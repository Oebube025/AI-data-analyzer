"""
Persistent Session & Tenant Management Database (database.py)
Stores saved what-if scenarios, SME tenant accounts, activity logs, and feedback using DuckDB.
Contains ZERO Streamlit imports.
"""

import duckdb
import datetime
import json
import os

DB_FILE = "sme_intelligence.duckdb"

def init_db():
    """Initializes all DuckDB tables safely without strict ID constraints."""
    conn = duckdb.connect(DB_FILE)
    
    # Table 1: Saved What-If Growth Scenarios
    conn.execute("""
        CREATE TABLE IF NOT EXISTS saved_scenarios (
            session_id VARCHAR,
            scenario_name VARCHAR,
            revenue DOUBLE,
            costs DOUBLE,
            net_profit DOUBLE,
            margin DOUBLE,
            details VARCHAR
        )
    """)
    
    # Table 2: SME Tenant Accounts
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            email VARCHAR PRIMARY KEY,
            company_name VARCHAR,
            created_at TIMESTAMP,
            last_active TIMESTAMP,
            total_uploads INTEGER DEFAULT 0
        )
    """)
    
    # Table 3: Client Activity Logs
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            email VARCHAR,
            action VARCHAR,
            timestamp TIMESTAMP
        )
    """)
    
    # Table 4: In-App Feedback & Bug Reports
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            email VARCHAR,
            category VARCHAR,
            message VARCHAR,
            timestamp TIMESTAMP
        )
    """)
    
    conn.close()

def save_scenario_db(session_id: str, name: str, res: dict):
    """Saves a What-If scenario model to the database."""
    init_db()
    conn = duckdb.connect(DB_FILE)
    conn.execute("""
        INSERT INTO saved_scenarios (session_id, scenario_name, revenue, costs, net_profit, margin, details)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [session_id, name, res["revenue"], res["costs"], res["net_profit"], res["profit_margin"], json.dumps(res)])
    conn.close()

def load_scenarios_db(session_id: str) -> list:
    """Loads all saved What-If scenarios for a specific tenant session."""
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

def log_tenant_activity(email: str, company_name: str, action: str):
    """Tracks SME tenant sign-ins, file uploads, and workspace actions without primary key collisions."""
    init_db()
    conn = duckdb.connect(DB_FILE)
    now = datetime.datetime.now()
    
    # Upsert tenant record
    conn.execute("""
        INSERT INTO tenants (email, company_name, created_at, last_active, total_uploads)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(email) DO UPDATE SET 
            last_active = excluded.last_active,
            total_uploads = tenants.total_uploads + 1
    """, [email, company_name if company_name else "Independent SME", now, now])
    
    # Log specific activity event
    conn.execute("""
        INSERT INTO activity_logs (email, action, timestamp)
        VALUES (?, ?, ?)
    """, [email, action, now])
    conn.close()

def save_feedback_db(email: str, category: str, message: str):
    """Saves client feedback or bug reports submitted from within the app."""
    init_db()
    conn = duckdb.connect(DB_FILE)
    now = datetime.datetime.now()
    conn.execute("""
        INSERT INTO feedback (email, category, message, timestamp)
        VALUES (?, ?, ?, ?)
    """, [email if email else "Anonymous Client", category, message, now])
    conn.close()