"""
Persistent storage (database.py): user accounts, saved What-If scenarios,
tenant activity logs, and in-app feedback in DuckDB.
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
                salt VARCHAR NOT NULL,
                pw_hash VARCHAR NOT NULL,
                created_at TIMESTAMP DEFAULT current_timestamp
            )
        """)
        # New SME Tenant & Activity tracking tables
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


# ------------------------------------------------------------------ users
def _hash(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), PBKDF2_ROUNDS).hex()


def create_user(username: str, password: str) -> bool:
    username = username.strip().lower()
    salt = secrets.token_hex(16)
    with _conn() as c:
        if c.execute("SELECT 1 FROM users WHERE username = ?", [username]).fetchone():
            return False
        try:
            c.execute("INSERT INTO users (username, salt, pw_hash) VALUES (?, ?, ?)",
                      [username, salt, _hash(password, salt)])
        except duckdb.ConstraintException:
            return False
    return True


def verify_user(username: str, password: str) -> bool:
    username = username.strip().lower()
    with _conn() as c:
        row = c.execute("SELECT salt, pw_hash FROM users WHERE username = ?", [username]).fetchone()
    if not row:
        _hash(password, "00" * 16)
        return False
    return hmac.compare_digest(_hash(password, row[0]), row[1])


# -------------------------------------------------------------- scenarios
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


# -------------------------------------------------------------- tenant & feedback tracking
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


def save_feedback_db(email: str, category: str, message: str):
    with _conn() as c:
        now = datetime.datetime.now()
        c.execute("""
            INSERT INTO feedback (email, category, message, timestamp)
            VALUES (?, ?, ?, ?)
        """, [email if email else "Anonymous Client", category, message, now])