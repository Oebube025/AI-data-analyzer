"""
database.py - FINCH Persistence Layer
Fixed tuple parameter binding for DuckDB queries.
"""

import os
import duckdb
import pandas as pd
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    return duckdb.connect("executive_intelligence.duckdb")

def init_db():
    conn = get_connection()
    if DATABASE_URL:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                email TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                password_hash TEXT,
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                total_uploads INT DEFAULT 0
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scenarios (
                id SERIAL PRIMARY KEY,
                username TEXT,
                scenario_name TEXT,
                data_key TEXT,
                revenue FLOAT,
                costs FLOAT,
                net_profit FLOAT,
                margin FLOAT,
                timestamp TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_history (
                id SERIAL PRIMARY KEY,
                email TEXT,
                company_type TEXT,
                file_name TEXT,
                total_revenue FLOAT,
                net_profit FLOAT,
                profit_margin FLOAT,
                ai_brief TEXT,
                timestamp TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                email TEXT,
                category TEXT,
                message TEXT,
                timestamp TIMESTAMP
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
    else:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                email VARCHAR PRIMARY KEY,
                username VARCHAR UNIQUE,
                password_hash VARCHAR,
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                total_uploads INTEGER DEFAULT 0
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR,
                scenario_name VARCHAR,
                data_key VARCHAR,
                revenue DOUBLE,
                costs DOUBLE,
                net_profit DOUBLE,
                margin DOUBLE,
                timestamp TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR,
                company_type VARCHAR,
                file_name VARCHAR,
                total_revenue DOUBLE,
                net_profit DOUBLE,
                profit_margin DOUBLE,
                ai_brief TEXT,
                timestamp TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR,
                category VARCHAR,
                message TEXT,
                timestamp TIMESTAMP
            );
        """)
        conn.close()

def create_user(username: str, email: str, password_hash: str) -> bool:
    conn = get_connection()
    try:
        now = datetime.now()
        if DATABASE_URL:
            cur = conn.cursor()
            cur.execute("INSERT INTO tenants (email, username, password_hash, created_at, last_active, total_uploads) VALUES (%s, %s, %s, %s, %s, 0)",
                        (email.strip().lower(), username.strip().lower(), password_hash, now, now))
            conn.commit()
            cur.close()
        else:
            conn.execute("INSERT INTO tenants VALUES (?, ?, ?, ?, ?, 0)",
                         (email.strip().lower(), username.strip().lower(), password_hash, now, now))
        conn.close()
        return True
    except Exception:
        conn.close()
        return False

def verify_user(identifier: str, password_hash: str):
    conn = get_connection()
    ident = identifier.strip().lower()
    if DATABASE_URL:
        cur = conn.cursor()
        cur.execute("SELECT username FROM tenants WHERE (email = %s OR username = %s) AND password_hash = %s",
                    (ident, ident, password_hash))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE tenants SET last_active = %s WHERE email = %s OR username = %s", (datetime.now(), ident, ident))
            conn.commit()
        cur.close()
        conn.close()
        return row[0] if row else None
    else:
        res = conn.execute("SELECT username FROM tenants WHERE (email = ? OR username = ?) AND password_hash = ?",
                           (ident, ident, password_hash)).fetchone()
        if res:
            conn.execute("UPDATE tenants SET last_active = ? WHERE email = ? OR username = ?", (datetime.now(), ident, ident))
        conn.close()
        return res[0] if res else None

def get_user_email(username: str) -> str:
    conn = get_connection()
    u_clean = username.lower().strip()
    if DATABASE_URL:
        cur = conn.cursor()
        cur.execute("SELECT email FROM tenants WHERE username = %s OR email = %s", (u_clean, u_clean))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row else u_clean
    else:
        res = conn.execute("SELECT email FROM tenants WHERE username = ? OR email = ?", (u_clean, u_clean)).fetchone()
        conn.close()
        return res[0] if res else u_clean

def log_tenant_activity(email: str, activity_desc: str, increment_upload: bool = False):
    conn = get_connection()
    now = datetime.now()
    e_clean = email.lower().strip()
    if DATABASE_URL:
        cur = conn.cursor()
        if increment_upload:
            cur.execute("UPDATE tenants SET last_active = %s, total_uploads = total_uploads + 1 WHERE email = %s", (now, e_clean))
        else:
            cur.execute("UPDATE tenants SET last_active = %s WHERE email = %s", (now, e_clean))
        conn.commit()
        cur.close()
    else:
        if increment_upload:
            conn.execute("UPDATE tenants SET last_active = ?, total_uploads = total_uploads + 1 WHERE email = ?", (now, e_clean))
        else:
            conn.execute("UPDATE tenants SET last_active = ? WHERE email = ?", (now, e_clean))
    conn.close()

def save_scenario_db(username: str, scenario_name: str, data_key: str, res: dict):
    conn = get_connection()
    now = datetime.now()
    if DATABASE_URL:
        cur = conn.cursor()
        cur.execute("INSERT INTO scenarios (username, scenario_name, data_key, revenue, costs, net_profit, margin, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (username, scenario_name, data_key, res["revenue"], res["costs"], res["net_profit"], res["profit_margin"], now))
        conn.commit()
        cur.close()
    else:
        conn.execute("INSERT INTO scenarios (username, scenario_name, data_key, revenue, costs, net_profit, margin, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (username, scenario_name, data_key, res["revenue"], res["costs"], res["net_profit"], res["profit_margin"], now))
    conn.close()

def load_scenarios_db(username: str, data_key: str):
    conn = get_connection()
    if DATABASE_URL:
        cur = conn.cursor()
        cur.execute("SELECT scenario_name, revenue, costs, net_profit, margin, timestamp FROM scenarios WHERE username = %s AND data_key = %s ORDER BY timestamp DESC", (username, data_key))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"scenario_name": r[0], "revenue": r[1], "costs": r[2], "net_profit": r[3], "margin": r[4], "timestamp": r[5]} for r in rows]
    else:
        res = conn.execute("SELECT scenario_name, revenue, costs, net_profit, margin, timestamp FROM scenarios WHERE username = ? AND data_key = ? ORDER BY timestamp DESC", (username, data_key)).fetchall()
        conn.close()
        return [{"scenario_name": r[0], "revenue": r[1], "costs": r[2], "net_profit": r[3], "margin": r[4], "timestamp": r[5]} for r in res]

def delete_scenarios_db(username: str, data_key: str):
    conn = get_connection()
    if DATABASE_URL:
        cur = conn.cursor()
        cur.execute("DELETE FROM scenarios WHERE username = %s AND data_key = %s", (username, data_key))
        conn.commit()
        cur.close()
    else:
        conn.execute("DELETE FROM scenarios WHERE username = ? AND data_key = ?", (username, data_key))
    conn.close()

def save_audit_history_db(email: str, company_type: str, file_name: str, totals: dict, ai_brief: str):
    conn = get_connection()
    now = datetime.now()
    if DATABASE_URL:
        cur = conn.cursor()
        cur.execute("INSERT INTO audit_history (email, company_type, file_name, total_revenue, net_profit, profit_margin, ai_brief, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (email, company_type, file_name, totals.get("total_revenue", 0), totals.get("net_profit", 0), totals.get("profit_margin", 0), ai_brief, now))
        conn.commit()
        cur.close()
    else:
        conn.execute("INSERT INTO audit_history (email, company_type, file_name, total_revenue, net_profit, profit_margin, ai_brief, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (email, company_type, file_name, totals.get("total_revenue", 0), totals.get("net_profit", 0), totals.get("profit_margin", 0), ai_brief, now))
    conn.close()

def load_user_history_db(email: str):
    conn = get_connection()
    e_clean = email.lower().strip()
    if DATABASE_URL:
        cur = conn.cursor()
        cur.execute("SELECT file_name, total_revenue, net_profit, profit_margin, ai_brief, timestamp FROM audit_history WHERE email = %s ORDER BY timestamp DESC", (e_clean,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"file_name": r[0], "total_revenue": r[1], "net_profit": r[2], "profit_margin": r[3], "ai_brief": r[4], "timestamp": r[5]} for r in rows]
    else:
        res = conn.execute("SELECT file_name, total_revenue, net_profit, profit_margin, ai_brief, timestamp FROM audit_history WHERE email = ? ORDER BY timestamp DESC", (e_clean,)).fetchall()
        conn.close()
        return [{"file_name": r[0], "total_revenue": r[1], "net_profit": r[2], "profit_margin": r[3], "ai_brief": r[4], "timestamp": r[5]} for r in res]

def save_feedback_db(email: str, category: str, message: str):
    conn = get_connection()
    now = datetime.now()
    if DATABASE_URL:
        cur = conn.cursor()
        cur.execute("INSERT INTO feedback (email, category, message, timestamp) VALUES (%s, %s, %s, %s)", (email, category, message, now))
        conn.commit()
        cur.close()
    else:
        conn.execute("INSERT INTO feedback (email, category, message, timestamp) VALUES (?, ?, ?, ?)", (email, category, message, now))
    conn.close()