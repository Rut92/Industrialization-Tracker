import sqlite3
import pandas as pd

DB_FILE = "projects.db"


def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Projects table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    # Master stock list
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            stockcode TEXT,
            description TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    """)

    # Procurement table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS procurement (
            project_id INTEGER NOT NULL,
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
            project_id INTEGER NOT NULL,
            stockcode TEXT,
            description TEXT,
            new_supplier TEXT,
            price REAL,
            fai_lt TEXT,
            production_lt TEXT,
            fai_delivery_date TEXT,
            first_po_delivery_date TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    """)

    # Quality table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quality (
            project_id INTEGER NOT NULL,
            stockcode TEXT,
            description TEXT,
            fai_status TEXT DEFAULT 'Not Submitted',
            fai_number TEXT,
            fitcheck_ac TEXT,
            fitcheck_date TEXT,
            fitcheck_status TEXT DEFAULT 'Not Scheduled',
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    """)

    conn.commit()
    conn.close()


def add_project(name, stockcodes_df=None):
    conn = get_connection()
    cur = conn.cursor()

    # Always insert or reuse existing
    cur.execute("INSERT OR IGNORE INTO projects (name) VALUES (?)", (name,))
    conn.commit()

    # Get project id
    cur.execute("SELECT id FROM projects WHERE name = ?", (name,))
    pid = cur.fetchone()[0]

    # If stock list provided, clear and re-add
    if stockcodes_df is not None:
        cur.execute("DELETE FROM stock_list WHERE project_id = ?", (pid,))
        for _, row in stockcodes_df.iterrows():
            cur.execute(
                "INSERT INTO stock_list (project_id, stockcode, description) VALUES (?, ?, ?)",
                (pid, row["StockCode"], row["Description"])
            )
    conn.commit()
    conn.close()
    return pid


def get_projects():
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, name FROM projects ORDER BY id DESC", conn)
    conn.close()
    return df


def clear_table(project_id, table_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table_name} WHERE project_id = ?", (project_id,))
    conn.commit()
    conn.close()


def save_table(df, project_id, table_name):
    conn = get_connection()
    df["project_id"] = project_id
    df.to_sql(table_name, conn, if_exists="append", index=False)
    conn.close()


def get_project_data(project_id):
    conn = get_connection()
    query = """
        SELECT 
            sl.stockcode,
            sl.description,

            pr.current_supplier,
            pr.price AS proc_price,
            pr.ac_coverage,
            pr.production_lt AS proc_production_lt,
            pr.next_shortage_date,

            ind.new_supplier,
            ind.price AS ind_price,
            ind.fai_lt,
            ind.production_lt AS ind_production_lt,
            ind.fai_delivery_date,
            ind.first_po_delivery_date,

            q.fai_status,
            q.fai_number,
            q.fitcheck_ac,
            q.fitcheck_date,
            q.fitcheck_status

        FROM stock_list sl
        LEFT JOIN procurement pr 
            ON sl.project_id = pr.project_id AND sl.stockcode = pr.stockcode
        LEFT JOIN industrialization ind 
            ON sl.project_id = ind.project_id AND sl.stockcode = ind.stockcode
        LEFT JOIN quality q 
            ON sl.project_id = q.project_id AND sl.stockcode = q.stockcode
        WHERE sl.project_id = ?
    """
    df = pd.read_sql_query(query, conn, params=(project_id,))
    conn.close()

    if not df.empty:
        df["overlap_days"] = (
            pd.to_datetime(df["next_shortage_date"], errors="coerce")
            - pd.to_datetime(df["first_po_delivery_date"], errors="coerce")
        ).dt.days

    return df
