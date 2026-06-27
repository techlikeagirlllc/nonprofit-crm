import sqlite3
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH    = os.path.join(os.path.dirname(__file__), "crm.db")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            address TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            donation_amount REAL DEFAULT 0,
            contact_type TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            interaction_date TEXT NOT NULL,
            thanked INTEGER DEFAULT 0,
            FOREIGN KEY (contact_id) REFERENCES contacts (id)
        )
    """)
    for col, defn in [
        ("phone",           "TEXT NOT NULL DEFAULT ''"),
        ("address",         "TEXT NOT NULL DEFAULT ''"),
        ("notes",           "TEXT NOT NULL DEFAULT ''"),
        ("donation_amount", "REAL DEFAULT 0"),
    ]:
        try:
            conn.execute(f"ALTER TABLE contacts ADD COLUMN {col} {defn}")
        except Exception:
            pass
    try:
        conn.execute("ALTER TABLE contacts ADD COLUMN email TEXT NOT NULL DEFAULT ''")
    except Exception:
        pass
    conn.commit()
    conn.close()


# ── Config (org name + password) ──────────────────────────────────────────────

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def is_setup_complete():
    cfg = load_config()
    return bool(cfg.get("org_name") and cfg.get("password_hash"))


def get_org_name():
    return load_config().get("org_name", "NonProfit CRM")


def verify_password(password):
    ph = load_config().get("password_hash", "")
    return bool(ph and check_password_hash(ph, password))


def run_setup(org_name, password):
    cfg = load_config()
    cfg["org_name"] = org_name.strip()
    cfg["password_hash"] = generate_password_hash(password)
    save_config(cfg)
