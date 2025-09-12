import re
import sqlite3
import pandas as pd
from datetime import datetime

DB_FILE = "projects.db"


def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            stockcode TEXT,
            description TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            UNIQUE(project_id, stockcode)
        )
    """)

    # procurement
    cur.execute("""
        CREATE TABLE IF NOT EXISTS procurement (
            project_id INTEGER NOT NULL,
            stockcode TEXT,
            description TEXT,
            current_supplier TEXT,
            ac_coverage TEXT,
            next_shortage_date TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            UNIQUE(project_id, stockcode)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS procurement_undo AS SELECT * FROM procurement WHERE 0;
    """)

    # industrialization
    cur.execute("""
        CREATE TABLE IF NOT EXISTS industrialization (
            project_id INTEGER NOT NULL,
            stockcode TEXT,
            description TEXT,
            new_supplier TEXT,
            fai_delivery_date TEXT,
            first_po_delivery_date TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            UNIQUE(project_id, stockcode)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS industrialization_undo AS SELECT * FROM industrialization WHERE 0;
    """)

    # quality
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quality (
            project_id INTEGER NOT NULL,
            stockcode TEXT,
            description TEXT,
            fai_status TEXT DEFAULT 'Not Submitted',
            fai_number TEXT,
            fitcheck_ac TEXT,
            fitcheck_date TEXT,
            fitcheck_status TEXT DEFAULT '',
            FOREIGN KEY(project_id) REFERENCES projects(id),
            UNIQUE(project_id, stockcode)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quality_undo AS SELECT * FROM quality WHERE 0;
    """)

    conn.commit()
    conn.close()


def reset_tables():
    """Drop and recreate all tables (useful if schema changed)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript("""
        DROP TABLE IF EXISTS stock_list;
        DROP TABLE IF EXISTS procurement;
        DROP TABLE IF EXISTS industrialization;
        DROP TABLE IF EXISTS quality;
        DROP TABLE IF EXISTS procurement_undo;
        DROP TABLE IF EXISTS industrialization_undo;
        DROP TABLE IF EXISTS quality_undo;
    """)
    conn.commit()
    conn.close()
    init_db()


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    col_map = {}
    for col in df.columns:
        norm = re.sub(r'[^a-z0-9]', '_', str(col).lower())
        norm = re.sub(r'_+', '_', norm).strip('_')
        col_map[col] = norm
    df = df.rename(columns=col_map)

    # normalize stockcodes
    if "stockcode" in df.columns:
        df["stockcode"] = df["stockcode"].astype(str).str.strip().str.upper()

    return df


def try_date(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    try:
        return datetime.strptime(str(x).strip(), "%Y-%m-%d").date().isoformat()
    except Exception:
        pass
    try:
        dt = pd.to_datetime(x, errors="coerce")
        if pd.isna(dt):
            return None
        return dt.date().isoformat()
    except Exception:
        return None


def add_project(name, stockcodes_df=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO projects (name) VALUES (?)", (name,))
    conn.commit()

    cur.execute("SELECT id FROM projects WHERE name = ?", (name,))
    pid = cur.fetchone()[0]

    if stockcodes_df is not None:
        stockcodes_df = normalize_columns(stockcodes_df)
        for _, row in stockcodes_df.iterrows():
            cur.execute("""
                INSERT INTO stock_list (project_id, stockcode, description)
                VALUES (?, ?, ?)
                ON CONFLICT(project_id, stockcode) DO UPDATE SET
                    description=excluded.description
            """, (pid, row.get("stockcode"), row.get("description")))
    conn.commit()
    conn.close()
    return pid


def get_projects():
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, name FROM projects ORDER BY id DESC", conn)
    conn.close()
    return df


def save_table(df, project_id, table_name):
    """UPSERT rows, saving current table state into undo before overwriting."""
    df = normalize_columns(df)

    schema = {
        "procurement": ["stockcode", "description", "current_supplier", "ac_coverage", "next_shortage_date"],
        "industrialization": ["stockcode", "description", "new_supplier", "fai_delivery_date", "first_po_delivery_date"],
        "quality": ["stockcode", "description", "fai_status", "fai_number", "fitcheck_ac", "fitcheck_date", "fitcheck_status"],
    }
    if table_name not in schema:
        raise ValueError(f"Unknown table {table_name}")

    for col in schema[table_name]:
        if col not in df.columns:
            df[col] = None
    df = df[schema[table_name]]
    df = df.drop_duplicates(subset=["stockcode"], keep="last")

    for col in ["next_shortage_date", "fai_delivery_date", "first_po_delivery_date", "fitcheck_date"]:
        if col in df.columns:
            df[col] = df[col].apply(try_date)

    if table_name == "quality":
        df["fai_status"] = df["fai_status"].fillna("Not Submitted")
        df["fitcheck_status"] = df["fitcheck_status"].fillna("")

    conn = get_connection()
    cur = conn.cursor()

    # save undo snapshot
    cur.execute(f"DELETE FROM {table_name}_undo WHERE project_id=?", (project_id,))
    cur.execute(f"INSERT INTO {table_name}_undo SELECT * FROM {table_name} WHERE project_id=?", (project_id,))

    # upsert each row
    for _, row in df.iterrows():
        columns = ["project_id"] + list(df.columns)
        placeholders = ", ".join("?" * len(columns))
        updates = ", ".join([f"{c}=excluded.{c}" for c in df.columns if c not in ["stockcode"]])
        sql = f"""
            INSERT INTO {table_name} ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(project_id, stockcode) DO UPDATE SET {updates}
        """
        cur.execute(sql, (project_id,) + tuple(row))

    conn.commit()
    conn.close()


def undo_last_save(project_id, table_name):
    """Restore last saved version of a table from its undo copy."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table_name} WHERE project_id=?", (project_id,))
    cur.execute(f"""
        INSERT INTO {table_name}
        SELECT * FROM {table_name}_undo WHERE project_id=?
    """, (project_id,))
    conn.commit()
    conn.close()


def get_project_data(project_id):
    conn = get_connection()
    query = """
        SELECT 
            sl.stockcode,
            sl.description,

            pr.current_supplier,
            pr.ac_coverage,
            pr.next_shortage_date,

            ind.new_supplier,
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

    if df.empty:
        cols = [
            "stockcode", "description",
            "current_supplier", "ac_coverage", "next_shortage_date",
            "new_supplier", "fai_delivery_date", "first_po_delivery_date", "overlap_days",
            "fai_status", "fai_number", "fitcheck_ac", "fitcheck_date", "fitcheck_status"
        ]
        return pd.DataFrame(columns=cols)

    df["overlap_days"] = (
        pd.to_datetime(df["next_shortage_date"], errors="coerce")
        - pd.to_datetime(df["first_po_delivery_date"], errors="coerce")
    ).dt.days

    return df[
        [
            "stockcode", "description",
            "current_supplier", "ac_coverage", "next_shortage_date",
            "new_supplier", "fai_delivery_date", "first_po_delivery_date", "overlap_days",
            "fai_status", "fai_number", "fitcheck_ac", "fitcheck_date", "fitcheck_status"
        ]
    ]
