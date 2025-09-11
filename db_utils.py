import sqlite3
import pandas as pd
import json

DB_FILE = "projects.db"

# ------------------ Init ------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Projects table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)

    # Data table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS project_data (
            project_id INTEGER,
            data TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)
    conn.commit()
    conn.close()

# ------------------ Project Functions ------------------
def add_project(name, df):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO projects (name) VALUES (?)", (name,))
    pid = cur.lastrowid
    cur.execute("INSERT INTO project_data (project_id, data) VALUES (?, ?)",
                (pid, df.to_json(orient="records")))
    conn.commit()
    conn.close()

def get_projects():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM projects ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_project_name(pid, new_name):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE projects SET name=? WHERE id=?", (new_name, pid))
    conn.commit()
    conn.close()

# ------------------ Data Functions ------------------
def get_project_data(pid):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT data FROM project_data WHERE project_id=?", (pid,))
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        return pd.DataFrame()

    df = pd.DataFrame(json.loads(row[0]))

    # Auto-migrate missing columns
    df = ensure_all_columns(df)

    return df

def save_project_data(pid, df):
    # Ensure schema consistency before saving
    df = ensure_all_columns(df)

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE project_data SET data=? WHERE project_id=?",
                (df.to_json(orient="records"), pid))
    conn.commit()
    conn.close()

# ------------------ Utility ------------------
def try_float(x):
    try:
        return float(x)
    except:
        return None

def detect_header_and_read(file):
    """Reads Excel file, maps headers to unified schema, returns normalized DataFrame"""
    df = pd.read_excel(file)

    # Normalize headers
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Rename known headers to internal schema
    header_map = {
        "stockcode": "stockcode",
        "description": "description",
        "ac_coverage_(confirmed_pos)": "ac_coverage",
        "ac_coverage": "ac_coverage",
        "production_lt": "current_production_lt",
        "price": "current_price",
        "fai_lt": "fai_lt",
        "new_supplier_production_lt": "new_supplier_production_lt",
        "new_price": "new_price",
    }
    df = df.rename(columns=header_map)

    # Ensure schema compliance
    df = ensure_all_columns(df)

    return df

def ensure_all_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensures that all required + workflow columns exist with defaults"""
    required = [
        "stockcode", "description", "ac_coverage",
        "current_production_lt", "current_price",
        "fai_lt", "new_supplier_production_lt", "new_price"
    ]
    workflow_cols = {
        "next_shortage_date": "",
        "fai_delivery_date": "",
        "fai_status": "Not Submitted",
        "fitcheck_status": "Not Scheduled",
        "fitcheck_ac": "",
        "first_production_po_delivery_date": "",
        "overlap_days": ""
    }

    # Add required columns if missing
    for col in required:
        if col not in df.columns:
            df[col] = ""

    # Add workflow columns with defaults
    for col, default in workflow_cols.items():
        if col not in df.columns:
            df[col] = default

    return df
