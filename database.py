"""
Persistent storage (database.py): user accounts, saved What-If scenarios,
tenant activity logs, user audit history, and feedback in DuckDB.
Contains automatic schema migration, scenario cost_assumed parsing, and ZERO Streamlit imports.
"""

import contextlib
import hashlib
import hmac
import json
import os
import secrets
import datetime
from typing import Optional

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
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR PRIMARY KEY,
                email VARCHAR,
                salt VARCHAR NOT NULL,
                pw_hash VARCHAR NOT NULL,
                created_at TIMESTAMP DEFAULT current_timestamp
            )
        """)
        
        try:
            c.execute("ALTER TABLE users ADD COLUMN email VARCHAR")
        except Exception:
            pass
            
        c.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                email VARCHAR PRIMARY KEY,
                company_name VARCHAR,
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                total_uploads INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                email VARCHAR,
                action VARCHAR,
                timestamp TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                email VARCHAR,
                category VARCHAR,
                message VARCHAR,
                timestamp TIMESTAMP
            )
        """)
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


def _hash(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), PBKDF2_ROUNDS).hex()


def create_user(username: str, email: str, password: str) -> bool:
    username = username.strip().lower()
    email = email.strip().lower()
    salt = secrets.token_hex(16)
    with _conn() as c:
        if c.execute("SELECT 1 FROM users WHERE username = ?", [username]).fetchone():
            return False
        if c.execute("SELECT 1 FROM users WHERE email = ?", [email]).fetchone():
            return False
        try:
            c.execute("INSERT INTO users (username, email, salt, pw_hash) VALUES (?, ?, ?, ?)",
                      [username, email, salt, _hash(password, salt)])
        except duckdb.ConstraintException:
            return False
    return True


def verify_user(username_or_email: str, password: str) -> Optional[str]:
    identifier = username_or_email.strip().lower()
    with _conn() as c:
        row = c.execute("""
            SELECT username, salt, pw_hash FROM users 
            WHERE username = ? OR email = ?
        """, [identifier, identifier]).fetchone()
    if not row:
        _hash(password, "00" * 16)
        return None
    if hmac.compare_digest(_hash(password, row[1]), row[2]):
        return row[0]
    return None


def get_user_email(username: str) -> str:
    with _conn() as c:
        row = c.execute("SELECT email FROM users WHERE username = ?", [username.strip().lower()]).fetchone()
    return row[0] if row and row[0] else username


def log_tenant_activity(email: str, action: str, increment_upload: bool = False):
    with _conn() as c:
        now = datetime.datetime.now()
        if increment_upload:
            c.execute("""
                INSERT INTO tenants (email, company_name, created_at, last_active, total_uploads)
                VALUES (?, 'Independent SME', ?, ?, 1)
                ON CONFLICT(email) DO UPDATE SET 
                    last_active = excluded.last_active,
                    total_uploads = tenants.total_uploads + 1
            """, [email, now, now])
        else:
            c.execute("""
                INSERT INTO tenants (email, company_name, created_at, last_active, total_uploads)
                VALUES (?, 'Independent SME', ?, ?, 0)
                ON CONFLICT(email) DO UPDATE SET 
                    last_active = excluded.last_active
            """, [email, now, now])
        
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
    
    results = []
    for _, row in df.iterrows():
        details = {}
        if row["details"]:
            try:
                details = json.loads(row["details"])
            except Exception:
                pass
        results.append({
            "scenario_name": row["scenario_name"],
            "revenue": row["revenue"],
            "costs": row["costs"],
            "net_profit": row["net_profit"],
            "margin": row["margin"],
            "cost_assumed": details.get("cost_assumed", False)
        })
    return results


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