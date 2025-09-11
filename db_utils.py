import sqlite3
import pandas as pd

DB_FILE = "projects.db"

# ---- DB INIT ----
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Projects table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    """)

    # Project data table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS project_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        stockcode TEXT,
        description TEXT,
        ac_coverage TEXT,
        current_production_lt TEXT,
        current_price TEXT,
        next_shortage_date TEXT,
        fai_lt TEXT,
        new_supplier_production_lt TEXT,
        new_price TEXT,
        fai_delivery_date TEXT,
        fai_status TEXT DEFAULT 'Not Submitted',
        fitcheck_status TEXT DEFAULT 'Not Scheduled',
        fitcheck_ac TEXT,
        first_production_po_delivery_date TEXT,
        overlap_days TEXT,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    )
    """)

    conn.commit()
    conn.close()

# ---- Project Management ----
def add_project(name):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO projects (name) VALUES (?)", (name,))
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid

def get_projects():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT id, name FROM projects", conn)
    conn.close()
    return df

def update_project_name(pid, new_name):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE projects SET name=? WHERE id=?", (new_name, pid))
    conn.commit()
    conn.close()

# ---- Project Data ----
def add_project_data(pid, df, replace=False):
    conn = sqlite3.connect(DB_FILE)
    if replace:
        conn.execute("DELETE FROM project_data WHERE project_id=?", (pid,))
    df["project_id"] = pid
    df.to_sql("project_data", conn, if_exists="append", index=False)
    conn.close()

def get_project_data(pid):
    conn = sqlite3.connect(DB_FILE)
    query = """
    SELECT stockcode, description, ac_coverage,
           current_production_lt, current_price, next_shortage_date,
           fai_lt, new_supplier_production_lt, new_price,
           fai_delivery_date, fai_status, fitcheck_status,
           fitcheck_ac, first_production_po_delivery_date, overlap_days
    FROM project_data WHERE project_id=?
    """
    df = pd.read_sql_query(query, conn, params=(pid,))
    conn.close()

    # --- Auto-calc Overlap (Days) ---
    if not df.empty:
        if "next_shortage_date" in df and "first_production_po_delivery_date" in df:
            df["overlap_days"] = pd.to_datetime(df["next_shortage_date"], errors="coerce") - \
                                 pd.to_datetime(df["first_production_po_delivery_date"], errors="coerce")
            df["overlap_days"] = df["overlap_days"].dt.days

    return df

# ---- File Upload ----
def detect_header_and_read(uploaded_file):
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    col_map = {
        "stockcode": "stockcode",
        "description": "description",
        "ac_coverage": "ac_coverage",
        "production_lt": "current_production_lt",
        "price": "current_price",
        "next_shortage_date": "next_shortage_date",
        "fai_lt": "fai_lt",
        "production_lt.1": "new_supplier_production_lt",
        "price.1": "new_price",
        "fai_delivery_date": "fai_delivery_date",
        "fai_status": "fai_status",
        "fitcheck_status": "fitcheck_status",
        "fitcheck_a/c": "fitcheck_ac",
        "1st_production_po_delivery_date": "first_production_po_delivery_date",
        "overlap_(days)": "overlap_days"
    }

    df = df.rename(columns={c: col_map[c] for c in df.columns if c in col_map})
    return df
