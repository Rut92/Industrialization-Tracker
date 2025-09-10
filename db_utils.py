import sqlite3
import pandas as pd

DB_FILE = "projects.db"  # Updated database name

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS project_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            stockcode TEXT,
            description TEXT,
            ac_coverage TEXT,
            current_production_lt TEXT,
            current_price REAL,
            fai_lt TEXT,
            new_supplier_production_lt TEXT,
            new_price REAL,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    """)
    conn.commit()
    conn.close()

def add_project(name, df):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO projects (name) VALUES (?)", (name,))
    project_id = cur.lastrowid
    for _, row in df.iterrows():
        cur.execute("""
            INSERT INTO project_data (
                project_id, stockcode, description, ac_coverage,
                current_production_lt, current_price, fai_lt,
                new_supplier_production_lt, new_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            row.get("stockcode"),
            row.get("description"),
            row.get("ac_coverage"),
            row.get("current_production_lt"),
            try_float(row.get("current_price")),
            row.get("fai_lt"),
            row.get("new_supplier_production_lt"),
            try_float(row.get("new_price")),
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
               current_production_lt, current_price, fai_lt,
               new_supplier_production_lt, new_price
        FROM project_data
        WHERE project_id = ?
    """, conn, params=(project_id,))
    conn.close()
    return df

def save_project_data(project_id, df):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM project_data WHERE project_id = ?", (project_id,))
    for _, r in df.iterrows():
        cur.execute("""
            INSERT INTO project_data (
                project_id, stockcode, description, ac_coverage,
                current_production_lt, current_price, fai_lt,
                new_supplier_production_lt, new_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            r.get("stockcode"),
            r.get("description"),
            r.get("ac_coverage"),
            r.get("current_production_lt"),
            try_float(r.get("current_price")),
            r.get("fai_lt"),
            r.get("new_supplier_production_lt"),
            try_float(r.get("new_price")),
        ))
    conn.commit()
    conn.close()

def try_float(x):
    if x is None or str(x).strip() == "":
        return None
    x = str(x).replace("$","").replace(",","").strip()
    try:
        return float(x)
    except:
        return None
