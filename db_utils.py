import sqlite3
import pandas as pd

DB_NAME = "projects.db"

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Projects table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)

    # Procurement data
    cur.execute("""
        CREATE TABLE IF NOT EXISTS procurement (
            project_id INTEGER,
            stockcode TEXT,
            description TEXT,
            price REAL,
            ac_coverage TEXT,
            production_lt TEXT,
            next_shortage_date TEXT,
            current_supplier TEXT,
            PRIMARY KEY (project_id, stockcode),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

    # Industrialization data
    cur.execute("""
        CREATE TABLE IF NOT EXISTS industrialization (
            project_id INTEGER,
            stockcode TEXT,
            description TEXT,
            price REAL,
            fai_lt TEXT,
            production_lt TEXT,
            fai_delivery_date TEXT,
            first_po_delivery_date TEXT,
            new_supplier TEXT,
            PRIMARY KEY (project_id, stockcode),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

    # Quality data
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quality (
            project_id INTEGER,
            stockcode TEXT,
            description TEXT,
            fair_status TEXT,
            fair_number TEXT,
            fitcheck_ac TEXT,
            fitcheck_date TEXT,
            fitcheck_status TEXT,
            PRIMARY KEY (project_id, stockcode),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

    conn.commit()
    conn.close()

def add_project(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM projects WHERE name = ?", (name,))
    existing = cur.fetchone()
    if existing:
        project_id = existing[0]
    else:
        cur.execute("INSERT INTO projects (name) VALUES (?)", (name,))
        project_id = cur.lastrowid
    conn.commit()
    conn.close()
    return project_id

def get_projects():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM projects", conn)
    conn.close()
    return df

def save_table(df, project_id, table_name):
    conn = get_connection()
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()

def get_project_data(project_id):
    conn = get_connection()

    # Procurement
    df_proc = pd.read_sql_query(
        "SELECT * FROM procurement WHERE project_id = ?", conn, params=(project_id,)
    )

    # Industrialization
    df_ind = pd.read_sql_query(
        "SELECT * FROM industrialization WHERE project_id = ?", conn, params=(project_id,)
    )

    # Quality
    df_qual = pd.read_sql_query(
        "SELECT * FROM quality WHERE project_id = ?", conn, params=(project_id,)
    )

    conn.close()

    # Merge all data
    df_final = pd.merge(df_proc, df_ind, on=["project_id", "stockcode", "description"], how="outer", suffixes=("_proc", "_ind"))
    df_final = pd.merge(df_final, df_qual, on=["project_id", "stockcode", "description"], how="outer")

    # Calculate Overlap (Days)
    if "next_shortage_date" in df_final and "first_po_delivery_date" in df_final:
        try:
            df_final["Overlap (Days)"] = (
                pd.to_datetime(df_final["next_shortage_date"]) -
                pd.to_datetime(df_final["first_po_delivery_date"])
            ).dt.days
        except Exception:
            df_final["Overlap (Days)"] = None
    else:
        df_final["Overlap (Days)"] = None

    return df_final
