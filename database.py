"""
Persistent storage (database.py): user accounts, saved What-If scenarios,
tenant activity logs, analysis history, and feedback in DuckDB.
Contains ZERO Streamlit imports.
"""

import contextlib
import hashlib
import hmac
import json
import os
import secrets
import datetime

import duckdb
import pandas as pd

DB_FILE = os.getenv("DB_PATH", "executive_intelligence.duckdb")
PBKDF2_ROUNDS = 200_000


@contextlib.contextmanager
def _conn():
    c = duckdb.connect(DB_FILE)
    try:
        yield c
    finally:
        c.close()


def init_db():
    with _conn() as c:
        c.execute("CREATE SEQUENCE IF NOT EXISTS scenario_seq START 1")
        c.execute("CREATE SEQUENCE IF NOT EXISTS history_seq START 1")
        
        # Table 1: What-If Growth Scenarios
        c.execute("""
            CREATE TABLE IF NOT EXISTS scenarios_v2 (
                id BIGINT PRIMARY KEY DEFAULT nextval('scenario_seq'),
                user_id VARCHAR NOT NULL,
                scenario_name VARCHAR,
                revenue DOUBLE,
                costs DOUBLE,
                net_profit DOUBLE,
                margin DOUBLE,
                details VARCHAR,
                created_at TIMESTAMP DEFAULT current_timestamp
            )
        """)
        
        # Table 2: SME Tenant Accounts
        c.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                email VARCHAR PRIMARY KEY,
                company_name VARCHAR,
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                total_uploads INTEGER DEFAULT 0
            )
        """)
        
        # Table 3: Client Activity Logs
        c.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                email VARCHAR,
                action VARCHAR,
                timestamp TIMESTAMP
            )
        """)
        
        # Table 4: In-App Feedback
        c.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                email VARCHAR,
                category VARCHAR,
                message VARCHAR,
                timestamp TIMESTAMP
            )
        """)

        # Table 5: Dedicated User History & Audit State
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_audit_history (
                id BIGINT PRIMARY KEY DEFAULT nextval('history_seq'),
                email VARCHAR,
                company_name VARCHAR,
                file_name VARCHAR,
                total_revenue DOUBLE,
                net_profit DOUBLE,
                profit_margin DOUBLE,
                ai_brief VARCHAR,
                timestamp TIMESTAMP
            )
        """)


def log_tenant_activity(email: str, company_name: str, action: str):
    with _conn() as c:
        now = datetime.datetime.now()
        c.execute("""
            INSERT INTO tenants (email, company_name, created_at, last_active, total_uploads)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(email) DO UPDATE SET 
                last_active = excluded.last_active,
                total_uploads = tenants.total_uploads + 1
        """, [email, company_name if company_name else "Independent SME", now, now])
        
        c.execute("""
            INSERT INTO activity_logs (email, action, timestamp)
            VALUES (?, ?, ?)
        """, [email, action, now])


def save_audit_history_db(email: str, company_name: str, file_name: str, totals: dict, ai_brief: str = ""):
    with _conn() as c:
        now = datetime.datetime.now()
        rev = totals.get("total_revenue", 0.0)
        net = totals.get("net_profit", 0.0)
        margin = totals.get("profit_margin", 0.0)
        c.execute("""
            INSERT INTO user_audit_history (email, company_name, file_name, total_revenue, net_profit, profit_margin, ai_brief, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [email, company_name, file_name, rev, net, margin, ai_brief, now])


def load_user_history_db(email: str) -> list:
    try:
        with _conn() as c:
            df = c.execute("""
                SELECT file_name, total_revenue, net_profit, profit_margin, ai_brief, timestamp
                FROM user_audit_history WHERE email = ? ORDER BY timestamp DESC
            """, [email]).fetchdf()
        df = df.astype(object).where(df.notna(), None)
        return df.to_dict(orient="records")
    except Exception:
        return []


def save_scenario_db(user_id: str, name: str, res: dict):
    margin = res.get("profit_margin")
    with _conn() as c:
        c.execute(
            """INSERT INTO scenarios_v2 (user_id, scenario_name, revenue, costs, net_profit, margin, details)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [user_id, (name or "Scenario")[:80], res["revenue"], res["costs"], res["net_profit"],
             margin, json.dumps(res, default=str)],
        )


def load_scenarios_db(user_id: str) -> list:
    try:
        with _conn() as c:
            df = c.execute(
                """SELECT scenario_name, revenue, costs, net_profit, margin, details
                   FROM scenarios_v2 WHERE user_id = ? ORDER BY id""", [user_id]
            ).fetchdf()
    except Exception:
        return []
    df = df.astype(object).where(df.notna(), None)
    return df.to_dict(orient="records")


def delete_scenarios_db(user_id: str):
    with _conn() as c:
        c.execute("DELETE FROM scenarios_v2 WHERE user_id = ?", [user_id])


def save_feedback_db(email: str, category: str, message: str):
    with _conn() as c:
        now = datetime.datetime.now()
        c.execute("""
            INSERT INTO feedback (email, category, message, timestamp)
            VALUES (?, ?, ?, ?)
        """, [email if email else "Anonymous Client", category, message, now])