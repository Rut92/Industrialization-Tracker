import sqlite3
import pandas as pd
import os

DB_FILE = "projects.db"

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

    # Procurement table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS procurement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            stockcode TEXT,
            description TEXT,
            current_supplier TEXT,
            price REAL,
            ac_coverage TEXT,
            production_lt TEXT,
            next_shortage_date TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    """)

    # Industrialization table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS industrialization (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            stockcode TEXT,
            description TEXT,
            new_supplier TEXT,
            price REAL,
            fai_lt TEXT,
            production_lt TEXT,
            fai_delivery_date TEXT,
            first_prod_po_date TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    """)

    # Quality table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quality (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            stockcode TEXT,
            description TEXT,
            fair_status TEXT,
            fair_number TEXT,
            fitcheck_ac TEXT,
            fitcheck_date TEXT,
            fitcheck_status TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    """)

    conn.commit()
    conn.close()


def get_connection():
    return sqlite3.connect(DB_FILE)


def add_project(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO projects (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()


def get_projects():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM projects")
    rows = cur.fetchall()
    conn.close()
    return rows


def save_table(df, project_id, table_name):
    conn = get_connection()
    df["project_id"] = project_id
    df.to_sql(table_name, conn, if_exists="append", index=False)
    conn.close()


def clear_table(project_id, table_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table_name} WHERE project_id = ?", (project_id,))
    conn.commit()
    conn.close()


def get_project_data(project_id):
    conn = get_connection()

    def safe_query(query, params):
        try:
            return pd.read_sql_query(query, conn, params=params)
        except Exception:
            return pd.DataFrame()

    # Procurement
    df_proc = safe_query("SELECT * FROM procurement WHERE project_id = ?", (project_id,))
    # Industrialization
    df_ind = safe_query("SELECT * FROM industrialization WHERE project_id = ?", (project_id,))
    # Quality
    df_qual = safe_query("SELECT * FROM quality WHERE project_id = ?", (project_id,))

    conn.close()

    if df_proc.empty and df_ind.empty and df_qual.empty:
        return pd.DataFrame()

    for df in [df_proc, df_ind, df_qual]:
        if not df.empty and "project_id" not in df.columns:
            df["project_id"] = project_id

    # Merge
    df = pd.merge(df_proc, df_ind, on=["stockcode", "description", "project_id"], how="outer", suffixes=("_proc", "_ind"))
    df = pd.merge(df, df_qual, on=["stockcode", "description", "project_id"], how="outer")

    # Calculate Overlap (Days)
    if "next_shortage_date" in df.columns and "first_prod_po_date" in df.columns:
        df["Overlap (Days)"] = (
            pd.to_datetime(df["next_shortage_date"], errors="coerce")
            - pd.to_datetime(df["first_prod_po_date"], errors="coerce")
        ).dt.days

    return df
