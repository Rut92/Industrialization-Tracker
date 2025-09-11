import sqlite3
import pandas as pd

DB_FILE = "projects.db"

# ------------------ DB Init ------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Projects table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    # Project data table with all columns
    cur.execute("""
        CREATE TABLE IF NOT EXISTS project_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            stockcode TEXT,
            description TEXT,
            ac_coverage TEXT,
            current_production_lt TEXT,
            current_price REAL,
            next_shortage_date TEXT,
            fai_lt TEXT,
            new_supplier_production_lt TEXT,
            new_price REAL,
            fai_delivery_date TEXT,
            fai_status TEXT DEFAULT 'Not Submitted',
            fitcheck_status TEXT DEFAULT 'Not Scheduled',
            fitcheck_ac TEXT,
            first_production_po_delivery_date TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    """)
    conn.commit()
    conn.close()


# ------------------ Utilities ------------------
def try_float(x):
    if x is None:
        return None
    x = str(x).strip()
    if x == "":
        return None
    x = x.replace("$", "").replace(",", "")
    try:
        return float(x)
    except:
        return None


# ------------------ Project CRUD ------------------
def add_project(name, df):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO projects (name) VALUES (?)", (name,))
    project_id = cur.lastrowid

    for _, row in df.iterrows():
        cur.execute("""
            INSERT INTO project_data (
                project_id, stockcode, description, ac_coverage,
                current_production_lt, current_price, next_shortage_date,
                fai_lt, new_supplier_production_lt, new_price,
                fai_delivery_date, fai_status, fitcheck_status,
                fitcheck_ac, first_production_po_delivery_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            row.get("stockcode"),
            row.get("description"),
            row.get("ac_coverage"),
            row.get("current_production_lt"),
            try_float(row.get("current_price")),
            row.get("next_shortage_date"),
            row.get("fai_lt"),
            row.get("new_supplier_production_lt"),
            try_float(row.get("new_price")),
            row.get("fai_delivery_date"),
            row.get("fai_status", "Not Submitted"),
            row.get("fitcheck_status", "Not Scheduled"),
            row.get("fitcheck_ac"),
            row.get("first_production_po_delivery_date"),
        ))

    conn.commit()
    conn.close()


def get_projects():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM projects ORDER BY id DESC")
    projects = cur.fetchall()
    conn.close()
    return projects


def update_project_name(project_id, new_name):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE projects SET name = ? WHERE id = ?", (new_name, project_id))
    conn.commit()
    conn.close()


def get_project_data(project_id):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("""
        SELECT stockcode, description, ac_coverage,
               current_production_lt, current_price, next_shortage_date,
               fai_lt, new_supplier_production_lt, new_price,
               fai_delivery_date, fai_status, fitcheck_status,
               fitcheck_ac, first_production_po_delivery_date
        FROM project_data
        WHERE project_id = ?
    """, conn, params=(project_id,))
    conn.close()
    return df


def save_project_data(project_id, df):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM project_data WHERE project_id = ?", (project_id,))
    for _, row in df.iterrows():
        cur.execute("""
            INSERT INTO project_data (
                project_id, stockcode, description, ac_coverage,
                current_production_lt, current_price, next_shortage_date,
                fai_lt, new_supplier_production_lt, new_price,
                fai_delivery_date, fai_status, fitcheck_status,
                fitcheck_ac, first_production_po_delivery_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            row.get("stockcode"),
            row.get("description"),
            row.get("ac_coverage"),
            row.get("current_production_lt"),
            try_float(row.get("current_price")),
            row.get("next_shortage_date"),
            row.get("fai_lt"),
            row.get("new_supplier_production_lt"),
            try_float(row.get("new_price")),
            row.get("fai_delivery_date"),
            row.get("fai_status", "Not Submitted"),
            row.get("fitcheck_status", "Not Scheduled"),
            row.get("fitcheck_ac"),
            row.get("first_production_po_delivery_date"),
        ))
    conn.commit()
    conn.close()


# ------------------ File Utilities ------------------
def detect_header_and_read(uploaded_file):
    """Simple reader assuming first row is header."""
    df = pd.read_excel(uploaded_file, dtype=str)
    return df
