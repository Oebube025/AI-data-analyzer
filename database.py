"""
Persistent storage (database.py): user accounts and saved What-If scenarios in DuckDB.
Contains ZERO Streamlit imports.
"""

import contextlib
import hashlib
import hmac
import json
import os
import secrets

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


# ------------------------------------------------------------------ users
def _hash(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), PBKDF2_ROUNDS).hex()


def create_user(username: str, password: str) -> bool:
    """Returns False if the username already exists."""
    username = username.strip().lower()
    salt = secrets.token_hex(16)
    with _conn() as c:
        if c.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            return False
        try:
            c.execute("INSERT INTO users (username, salt, pw_hash) VALUES (?, ?, ?)",
                      (username, salt, _hash(password, salt)))
        except duckdb.ConstraintException:
            return False
    return True


def verify_user(username: str, password: str) -> bool:
    username = username.strip().lower()
    with _conn() as c:
        row = c.execute("SELECT salt, pw_hash FROM users WHERE username = ?", (username,)).fetchone()
    if not row:
        _hash(password, "00" * 16)  # constant-ish timing for unknown users
        return False
    return hmac.compare_digest(_hash(password, row[0]), row[1])


# -------------------------------------------------------------- scenarios
def save_scenario_db(user_id: str, name: str, res: dict):
    margin = res.get("profit_margin")
    with _conn() as c:
        c.execute(
            """INSERT INTO scenarios_v2 (user_id, scenario_name, revenue, costs, net_profit, margin, details)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, (name or "Scenario")[:80], res["revenue"], res["costs"], res["net_profit"],
             margin, json.dumps(res, default=str)),
        )


def load_scenarios_db(user_id: str) -> list:
    try:
        with _conn() as c:
            df = c.execute(
                """SELECT scenario_name, revenue, costs, net_profit, margin, details
                   FROM scenarios_v2 WHERE user_id = ? ORDER BY id""", (user_id,)
            ).fetchdf()
    except Exception:
        return []
    df = df.astype(object).where(df.notna(), None)  # NaN -> None so it is JSON safe
    return df.to_dict(orient="records")


def delete_scenarios_db(user_id: str):
    with _conn() as c:
        c.execute("DELETE FROM scenarios_v2 WHERE user_id = ?", (user_id,))