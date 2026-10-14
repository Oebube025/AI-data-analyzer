"""
database.py - FINCH Database & Security Persistence Layer
"""
import os
import hashlib
import secrets
from contextlib import contextmanager
import duckdb

DB_PATH = "finch_v3.duckdb"

@contextmanager
def get_connection():
    conn = duckdb.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                username VARCHAR PRIMARY KEY,
                email VARCHAR UNIQUE,
                password_hash VARCHAR,
                salt VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_uploads INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scenarios (
                id INTEGER PRIMARY KEY,
                username VARCHAR,
                scenario_name VARCHAR,
                data_key VARCHAR,
                payload VARCHAR
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_history (
                id INTEGER PRIMARY KEY,
                email VARCHAR,
                company VARCHAR,
                file_name VARCHAR,
                total_revenue DOUBLE,
                net_profit DOUBLE,
                profit_margin DOUBLE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                summary TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY,
                username VARCHAR,
                feedback_text TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def hash_password(password: str, salt: str = None) -> tuple:
    if not salt:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        bytes.fromhex(salt),
        100000
    ).hex()
    return pwd_hash, salt

def create_user(username: str, email: str, password: str) -> bool:
    init_db()
    uname = username.strip().lower()
    uemail = email.strip().lower()
    pwd_hash, salt = hash_password(password)
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO tenants (username, email, password_hash, salt) VALUES (?, ?, ?, ?)",
                (uname, uemail, pwd_hash, salt)
            )
        return True
    except Exception:
        return False

def verify_user(username_or_email: str, password: str) -> str:
    init_db()
    key = username_or_email.strip().lower()
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT username, password_hash, salt FROM tenants WHERE username = ? OR email = ?",
                (key, key)
            ).fetchone()
            if not row:
                return None
            uname, stored_hash, salt = row
            test_hash, _ = hash_password(password, salt)
            if secrets.compare_digest(test_hash, stored_hash):
                conn.execute("UPDATE tenants SET last_active = CURRENT_TIMESTAMP WHERE username = ?", (uname,))
                return uname
    except Exception:
        pass
    return None

def get_user_email(username: str) -> str:
    with get_connection() as conn:
        row = conn.execute("SELECT email FROM tenants WHERE username = ?", (username,)).fetchone()
        return row[0] if row else ""

def save_scenario_db(username: str, name: str, data_key: str, payload: dict):
    import json
    with get_connection() as conn:
        # Get next ID for DuckDB table insertion
        max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM scenarios").fetchone()[0]
        next_id = max_id + 1
        conn.execute(
            "INSERT INTO scenarios (id, username, scenario_name, data_key, payload) VALUES (?, ?, ?, ?, ?)",
            (next_id, username, name, data_key, json.dumps(payload))
        )

def load_scenarios_db(username: str, data_key: str) -> list:
    import json
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT scenario_name, payload FROM scenarios WHERE username = ? AND data_key = ?",
            [username, data_key]
        ).fetchall()
        res = []
        for r in rows:
            p = json.loads(r[1])
            p["scenario_name"] = r[0]
            res.append(p)
        return res

def delete_scenarios_db(username: str, data_key: str):
    with get_connection() as conn:
        conn.execute("DELETE FROM scenarios WHERE username = ? AND data_key = ?", (username, data_key))

def save_feedback_db(username: str, feedback_text: str):
    with get_connection() as conn:
        max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM feedback").fetchone()[0]
        conn.execute(
            "INSERT INTO feedback (id, username, feedback_text) VALUES (?, ?, ?)",
            (max_id + 1, username, feedback_text)
        )

def log_tenant_activity(email: str, activity: str, increment_upload: bool = False):
    with get_connection() as conn:
        if increment_upload:
            conn.execute("UPDATE tenants SET total_uploads = total_uploads + 1, last_active = CURRENT_TIMESTAMP WHERE email = ?", (email,))
        else:
            conn.execute("UPDATE tenants SET last_active = CURRENT_TIMESTAMP WHERE email = ?", (email,))

def save_audit_history_db(email: str, company: str, file_name: str, totals: dict, summary: str):
    with get_connection() as conn:
        max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM audit_history").fetchone()[0]
        conn.execute(
            """INSERT INTO audit_history (id, email, company, file_name, total_revenue, net_profit, profit_margin, summary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (max_id + 1, email, company, file_name, totals.get("total_revenue", 0), totals.get("net_profit", 0), totals.get("profit_margin", 0), summary)
        )

def load_user_history_db(email: str) -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT file_name, total_revenue, net_profit, profit_margin, timestamp FROM audit_history WHERE email = ? ORDER BY timestamp DESC",
            (email,)
        ).fetchall()
        return [
            {"file_name": r[0], "total_revenue": r[1], "net_profit": r[2], "profit_margin": r[3], "timestamp": r[4]}
            for r in rows
        ]