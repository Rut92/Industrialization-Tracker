import sqlite3
import pandas as pd

DB_FILE = "projects.db"

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

def try_float(x):
    if x is None:
        return None
    x = str(x).strip().replace("$", "").replace(",", "")
    try:
        return float(x)
    except:
        return None

def detect_header_and_read(uploaded_file, max_rows=10):
    uploaded_file.seek(0)
    raw = pd.read_excel(uploaded_file, header=None, dtype=str)
    n = min(len(raw), max_rows)
    expected_keywords = ["stock", "description", "ac coverage", "production", "price", "fai"]
    header_row = None
    for i in range(n):
        row = raw.iloc[i].fillna("").astype(str).str.lower().tolist()
        has_stock = any("stock" in x for x in row)
        has_desc = any("description" in x for x in row)
        keyword_matches = sum(any(kw in x for x in row) for kw in expected_keywords)
        if has_stock and has_desc and keyword_matches >= 3:
            header_row = i
            break
    if header_row is None:
        header_row = 0
    uploaded_file.seek(0)
    df = pd.read_excel(uploaded_file, header=header_row, dtype=str)
    mapping = {}
    prod_count = 0
    price_count = 0
    for col in df.columns:
        norm = str(col).strip().lower()
        if "stock" in norm:
            mapping[col] = "stockcode"
        elif "description" in norm:
            mapping[col] = "description"
        elif "ac coverage" in norm:
            mapping[col] = "ac_coverage"
        elif "fai" in norm:
            mapping[col] = "fai_lt"
        elif "production" in norm:
            if prod_count == 0:
                mapping[col] = "current_production_lt"
            else:
                mapping[col] = "new_supplier_production_lt"
            prod_count += 1
        elif "price" in norm:
            if price_count == 0:
                mapping[col] = "current_price"
            else:
                mapping[col] = "new_price"
            price_count += 1
        else:
            mapping[col] = norm.replace(" ", "_")
    df.rename(columns=mapping, inplace=True)
    return df
