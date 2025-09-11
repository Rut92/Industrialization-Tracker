import sqlite3
import pandas as pd

DB_FILE = "projects.db"

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Create projects table
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
            price REAL,
            ac_coverage TEXT,
            production_lt TEXT,
            next_shortage_date TEXT,
            current_supplier TEXT,
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
            price REAL,
            fai_lt TEXT,
            production_lt TEXT,
            fai_delivery_date TEXT,
            first_prod_po_date TEXT,
            new_supplier TEXT,
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
            fai_status TEXT,
            fai_number TEXT,
            fitcheck_ac TEXT,
            fitcheck_date TEXT,
            fitcheck_status TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    """)

    conn.commit()
    conn.close()


def add_project(name):
    conn = get_connection()
    cur = conn.cursor()

    # Check if project exists
    cur.execute("SELECT id FROM projects WHERE name = ?", (name,))
    existing = cur.fetchone()

    if existing:
        project_id = existing[0]
    else:
        try:
            cur.execute("INSERT INTO projects (name) VALUES (?)", (name,))
            project_id = cur.lastrowid
            conn.commit()
        except sqlite3.IntegrityError:
            # Race condition protection
            cur.execute("SELECT id FROM projects WHERE name = ?", (name,))
            project_id = cur.fetchone()[0]

    conn.close()
    return project_id


def get_projects():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM projects", conn)
    conn.close()
    return df


def save_table(df, project_id, table_name):
    conn = get_connection()
    df["project_id"] = project_id
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()


def get_project_data(project_id):
    conn = get_connection()

    # Procurement
    df_proc = pd.read_sql_query(
        "SELECT * FROM procurement WHERE project_id = ?",
        conn, params=(project_id,)
    )

    # Industrialization
    df_ind = pd.read_sql_query(
        "SELECT * FROM industrialization WHERE project_id = ?",
        conn, params=(project_id,)
    )

    # Quality
    df_qual = pd.read_sql_query(
        "SELECT * FROM quality WHERE project_id = ?",
        conn, params=(project_id,)
    )

    conn.close()

    # Merge all dataframes
    df = pd.merge(df_proc, df_ind, on=["stockcode", "description", "project_id"], how="outer", suffixes=("_proc", "_ind"))
    df = pd.merge(df, df_qual, on=["stockcode", "description", "project_id"], how="outer")

    # Calculate Overlap (Days)
    if "next_shortage_date" in df.columns and "first_prod_po_date" in df.columns:
        df["Overlap (Days)"] = pd.to_datetime(df["next_shortage_date"]) - pd.to_datetime(df["first_prod_po_date"])
        df["Overlap (Days)"] = df["Overlap (Days)"].dt.days

    return df
