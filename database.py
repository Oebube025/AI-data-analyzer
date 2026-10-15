"""
database.py - FINCH Database & Security Persistence Layer (v2.12)
"""
import datetime
import hashlib
import hmac
import json
import os
import secrets
from contextlib import contextmanager

import duckdb

DB_PATH = os.getenv("FINCH_DB_PATH", "finch_v3.duckdb")
PBKDF2_ROUNDS = 200_000
LEGACY_ROUNDS = 100_000
MAX_FAILS = 5
LOCK_MINUTES = 15
SESSION_HOURS = int(os.getenv("FINCH_SESSION_HOURS", "72"))
RESET_MINUTES = 30
_COMMON_PASSWORDS = {"password", "password1", "12345678", "123456789", "qwertyui", "qwerty123", "11111111",
                     "iloveyou", "admin123", "abc12345", "00000000", "welcome1"}
_initialised = set()


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


@contextmanager
def get_connection():
    conn = duckdb.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    if DB_PATH in _initialised:
        return
    with get_connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS tenants (
            username VARCHAR PRIMARY KEY, email VARCHAR UNIQUE, password_hash VARCHAR, salt VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_uploads INTEGER DEFAULT 0)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY, username VARCHAR, scenario_name VARCHAR, data_key VARCHAR, payload VARCHAR)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS audit_history (
            id INTEGER PRIMARY KEY, email VARCHAR, company VARCHAR, file_name VARCHAR, total_revenue DOUBLE,
            net_profit DOUBLE, profit_margin DOUBLE, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, summary TEXT)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY, username VARCHAR, feedback_text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        conn.execute("CREATE TABLE IF NOT EXISTS login_attempts (identifier VARCHAR, ts TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS sessions (token_hash VARCHAR PRIMARY KEY, username VARCHAR, expires_at TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS reset_codes (username VARCHAR PRIMARY KEY, code_hash VARCHAR, expires_at TIMESTAMP)")
    _initialised.add(DB_PATH)


def _insert_with_id(conn, table: str, columns: list, values: list, tries: int = 5):
    marks = ", ".join(["?"] * (len(columns) + 1))
    sql = f"INSERT INTO {table} (id, {', '.join(columns)}) VALUES ({marks})"
    last = None
    for _ in range(tries):
        next_id = conn.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}").fetchone()[0]
        try:
            conn.execute(sql, [next_id] + list(values))
            return
        except Exception as e:
            last = e
    raise last


def password_problem(password: str, username: str = ""):
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if len(password) > 128:
        return "Password is too long (max 128 characters)."
    if password.lower() in _COMMON_PASSWORDS or (username and password.lower() == username.strip().lower()):
        return "That password is too easy to guess. Choose another."
    if password.isdigit():
        return "Use letters as well as numbers in your password."
    return None


def hash_password(password: str, salt: str = None, rounds: int = PBKDF2_ROUNDS) -> tuple:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), rounds).hex()
    return f"pbkdf2${rounds}${digest}", salt


def _check_password(password: str, salt: str, stored: str) -> tuple:
    if stored.startswith("pbkdf2$"):
        _, r, digest = stored.split("$", 2)
        rounds = int(r)
    else:
        digest, rounds = stored, LEGACY_ROUNDS
    test = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), rounds).hex()
    return hmac.compare_digest(test, digest), rounds


_DUMMY_SALT = "00" * 16
_DUMMY_HASH = hash_password("dummy-password", _DUMMY_SALT)[0]


def create_user(username: str, email: str, password: str) -> bool:
    init_db()
    uname, uemail = username.strip().lower(), email.strip().lower()
    if password_problem(password, uname):
        return False
    pwd_hash, salt = hash_password(password)
    try:
        with get_connection() as conn:
            if conn.execute("SELECT 1 FROM tenants WHERE username = ? OR email = ?", [uname, uemail]).fetchone():
                return False
            conn.execute("INSERT INTO tenants (username, email, password_hash, salt) VALUES (?, ?, ?, ?)",
                         [uname, uemail, pwd_hash, salt])
        return True
    except Exception:
        return False


def _record_failure(conn, key: str):
    now = _now()
    conn.execute("DELETE FROM login_attempts WHERE ts < ?", [now - datetime.timedelta(days=1)])
    conn.execute("INSERT INTO login_attempts (identifier, ts) VALUES (?, ?)", [key, now])


def _is_locked(conn, key: str) -> bool:
    since = _now() - datetime.timedelta(minutes=LOCK_MINUTES)
    n = conn.execute("SELECT COUNT(*) FROM login_attempts WHERE identifier = ? AND ts > ?", [key, since]).fetchone()[0]
    return n >= MAX_FAILS


def login_locked(identifier: str) -> bool:
    init_db()
    with get_connection() as conn:
        return _is_locked(conn, identifier.strip().lower())


def verify_user(username_or_email: str, password: str):
    init_db()
    key = username_or_email.strip().lower()
    if not key or len(password) > 128:
        return None
    with get_connection() as conn:
        if _is_locked(conn, key):
            return None
        row = conn.execute("SELECT username, password_hash, salt FROM tenants WHERE username = ? OR email = ?",
                           [key, key]).fetchone()
        if not row:
            _check_password(password, _DUMMY_SALT, _DUMMY_HASH)
            _record_failure(conn, key)
            return None
        uname, stored, salt = row
        ok, rounds = _check_password(password, salt, stored)
        if not ok:
            _record_failure(conn, key)
            return None
        conn.execute("DELETE FROM login_attempts WHERE identifier = ?", [key])
        if rounds < PBKDF2_ROUNDS:
            new_hash, _ = hash_password(password, salt)
            conn.execute("UPDATE tenants SET password_hash = ? WHERE username = ?", [new_hash, uname])
        conn.execute("UPDATE tenants SET last_active = ? WHERE username = ?", [_now(), uname])
        return uname


def _sha(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(username: str, hours: int = None) -> str:
    init_db()
    token = secrets.token_urlsafe(32)
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", [_now()])
        conn.execute("INSERT INTO sessions (token_hash, username, expires_at) VALUES (?, ?, ?)",
                     [_sha(token), username, _now() + datetime.timedelta(hours=hours or SESSION_HOURS)])
    return token


def get_session_user(token: str):
    if not token or len(token) > 200:
        return None
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT username FROM sessions WHERE token_hash = ? AND expires_at > ?",
                           [_sha(token), _now()]).fetchone()
    return row[0] if row else None


def delete_session(token: str):
    if token:
        init_db()
        with get_connection() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", [_sha(token)])


def create_reset_code(identifier: str):
    init_db()
    key = identifier.strip().lower()
    with get_connection() as conn:
        row = conn.execute("SELECT username FROM tenants WHERE username = ? OR email = ?", [key, key]).fetchone()
        if not row:
            return None
        code = secrets.token_hex(4).upper()
        conn.execute("DELETE FROM reset_codes WHERE username = ?", [row[0]])
        conn.execute("INSERT INTO reset_codes (username, code_hash, expires_at) VALUES (?, ?, ?)",
                     [row[0], _sha(code), _now() + datetime.timedelta(minutes=RESET_MINUTES)])
    return row[0], code


def redeem_reset_code(identifier: str, code: str, new_password: str) -> bool:
    init_db()
    key = identifier.strip().lower()
    guard = "reset:" + key
    with get_connection() as conn:
        if _is_locked(conn, guard):
            return False
        row = conn.execute("SELECT username FROM tenants WHERE username = ? OR email = ?", [key, key]).fetchone()
        rc = conn.execute("SELECT code_hash FROM reset_codes WHERE username = ? AND expires_at > ?",
                          [row[0], _now()]).fetchone() if row else None
        good = bool(rc) and hmac.compare_digest(rc[0], _sha(code.strip().upper()))
        if not good or password_problem(new_password, row[0] if row else ""):
            _record_failure(conn, guard)
            return False
        new_hash, salt = hash_password(new_password)
        conn.execute("UPDATE tenants SET password_hash = ?, salt = ? WHERE username = ?", [new_hash, salt, row[0]])
        conn.execute("DELETE FROM reset_codes WHERE username = ?", [row[0]])
        conn.execute("DELETE FROM sessions WHERE username = ?", [row[0]])
        conn.execute("DELETE FROM login_attempts WHERE identifier IN (?, ?, ?)", [key, row[0], guard])
    return True


def get_user_email(username: str) -> str:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT email FROM tenants WHERE username = ?", [username]).fetchone()
    return row[0] if row else ""


def save_scenario_db(username: str, name: str, data_key: str, payload: dict):
    init_db()
    with get_connection() as conn:
        _insert_with_id(conn, "scenarios", ["username", "scenario_name", "data_key", "payload"],
                        [username, (name or "Scenario")[:80], data_key, json.dumps(payload, default=str)])


def load_scenarios_db(username: str, data_key: str) -> list:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT scenario_name, payload FROM scenarios WHERE username = ? AND data_key = ? ORDER BY id",
                            [username, data_key]).fetchall()
    out = []
    for name, raw in rows:
        try:
            p = json.loads(raw)
        except Exception:
            continue
        p["scenario_name"] = name
        p.setdefault("margin", p.get("profit_margin"))
        out.append(p)
    return out


def delete_scenarios_db(username: str, data_key: str):
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM scenarios WHERE username = ? AND data_key = ?", [username, data_key])


def save_feedback_db(username: str, feedback_text: str):
    init_db()
    with get_connection() as conn:
        _insert_with_id(conn, "feedback", ["username", "feedback_text", "timestamp"],
                        [username, (feedback_text or "")[:2000], _now()])


def log_tenant_activity(email: str, activity: str, increment_upload: bool = False):
    init_db()
    with get_connection() as conn:
        if increment_upload:
            conn.execute("UPDATE tenants SET total_uploads = total_uploads + 1, last_active = ? WHERE email = ?", [_now(), email])
        else:
            conn.execute("UPDATE tenants SET last_active = ? WHERE email = ?", [_now(), email])


def save_audit_history_db(email: str, company: str, file_name: str, totals: dict, summary: str):
    init_db()
    with get_connection() as conn:
        _insert_with_id(conn, "audit_history",
                        ["email", "company", "file_name", "total_revenue", "net_profit", "profit_margin", "timestamp", "summary"],
                        [email, company, file_name, totals.get("total_revenue"), totals.get("net_profit"),
                         totals.get("profit_margin"), _now(), summary])


def load_user_history_db(email: str) -> list:
    init_db()
    try:
        with get_connection() as conn:
            rows = conn.execute("SELECT file_name, total_revenue, net_profit, profit_margin, timestamp "
                                "FROM audit_history WHERE email = ? ORDER BY timestamp DESC, id DESC", [email]).fetchall()
    except Exception:
        return []
    return [{"file_name": r[0], "total_revenue": r[1], "net_profit": r[2], "profit_margin": r[3], "timestamp": r[4]}
            for r in rows]


def export_user_data(username: str) -> dict:
    init_db()
    email = get_user_email(username)
    with get_connection() as conn:
        acct = conn.execute("SELECT username, email, created_at, last_active, total_uploads FROM tenants WHERE username = ?",
                            [username]).fetchone()
        scen = conn.execute("SELECT scenario_name, payload FROM scenarios WHERE username = ? ORDER BY id", [username]).fetchall()
        hist = conn.execute("SELECT file_name, total_revenue, net_profit, profit_margin, timestamp, summary "
                            "FROM audit_history WHERE email = ? ORDER BY id", [email]).fetchall()
        fb = conn.execute("SELECT feedback_text, timestamp FROM feedback WHERE username = ? ORDER BY id", [username]).fetchall()
    return json.loads(json.dumps({
        "account": dict(zip(["username", "email", "created_at", "last_active", "total_uploads"], acct)) if acct else {},
        "scenarios": [{"name": n, **json.loads(p)} for n, p in scen],
        "reports": [dict(zip(["file_name", "total_revenue", "net_profit", "profit_margin", "timestamp", "summary"], h)) for h in hist],
        "feedback": [{"text": t, "timestamp": ts} for t, ts in fb],
    }, default=str))


def delete_user_data(username: str):
    init_db()
    email = get_user_email(username)
    with get_connection() as conn:
        conn.execute("DELETE FROM scenarios WHERE username = ?", [username])
        conn.execute("DELETE FROM feedback WHERE username = ?", [username])
        conn.execute("DELETE FROM sessions WHERE username = ?", [username])
        conn.execute("DELETE FROM reset_codes WHERE username = ?", [username])
        if email:
            conn.execute("DELETE FROM audit_history WHERE email = ?", [email])
        conn.execute("DELETE FROM login_attempts WHERE identifier IN (?, ?)", [username, email or username])
        conn.execute("DELETE FROM tenants WHERE username = ?", [username])


def get_tenants_overview() -> list:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT email, created_at, last_active, total_uploads FROM tenants ORDER BY last_active DESC").fetchall()
    return [dict(zip(["email", "created_at", "last_active", "total_uploads"], r)) for r in rows]


def backup_database(dest_dir: str = "backups") -> str:
    init_db()
    path = os.path.join(dest_dir, "finch_backup_" + _now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(path, exist_ok=True)
    safe = path.replace("'", "''")
    with get_connection() as conn:
        conn.execute(f"EXPORT DATABASE '{safe}' (FORMAT PARQUET)")
    return path