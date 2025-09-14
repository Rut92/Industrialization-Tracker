import re
import sqlite3
import pandas as pd
from datetime import datetime
import os
import bcrypt

DB_FILE = "projects.db"
USERS_FILE = "users.xlsx"  # Optional seed file: columns = Email, Role, Password


def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # ---- projects ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    # ---- stock list (master) ----
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

    # ---- procurement ----
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
    cur.execute("""CREATE TABLE IF NOT EXISTS procurement_undo AS SELECT * FROM procurement WHERE 0;""")

    # ---- industrialization ----
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
    cur.execute("""CREATE TABLE IF NOT EXISTS industrialization_undo AS SELECT * FROM industrialization WHERE 0;""")

    # ---- quality ----
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
    cur.execute("""CREATE TABLE IF NOT EXISTS quality_undo AS SELECT * FROM quality WHERE 0;""")

    # ---- audit log (row-level history) ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            table_name TEXT,
            stockcode TEXT,
            column_name TEXT,
            old_value TEXT,
            new_value TEXT,
            changed_by TEXT,
            changed_at TEXT
        )
    """)

    # ---- attachments (BLOB storage) ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            stockcode TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_data BLOB NOT NULL,
            uploaded_by TEXT,
            uploaded_at TEXT
        )
    """)

    # ---- users (auth) ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

    # Auto-load users from Excel if available (idempotent)
    if os.path.exists(USERS_FILE):
        try:
            df_users = pd.read_excel(USERS_FILE)
            load_users_from_excel(df_users)
            print("✅ Users loaded from Excel into database.")
        except Exception as e:
            print(f"⚠️ Could not load users.xlsx: {e}")


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
        DROP TABLE IF EXISTS audit_log;
        DROP TABLE IF EXISTS attachments;
        DROP TABLE IF EXISTS users;
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


def _fetch_existing_row_dict(conn, table_name, project_id, stockcode):
    q = f"SELECT * FROM {table_name} WHERE project_id=? AND stockcode=?"
    cur = conn.cursor()
    cur.execute(q, (project_id, stockcode))
    row = cur.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def log_audit_changes(conn, project_id, table_name, stockcode, old_row, new_row, changed_by):
    """Write one audit row per changed column."""
    cur = conn.cursor()
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    for col, new_val in new_row.items():
        if col in ["project_id", "stockcode"]:
            continue
        old_val = None if not old_row else old_row.get(col)
        # normalize both to strings for comparison
        if pd.isna(new_val) if isinstance(new_val, (float, pd.Series)) else new_val is None:
            new_s = None
        else:
            new_s = str(new_val)
        old_s = None if old_val is None else str(old_val)
        if old_s != new_s:
            cur.execute("""
                INSERT INTO audit_log (
                    project_id, table_name, stockcode, column_name,
                    old_value, new_value, changed_by, changed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (project_id, table_name, stockcode, col, old_s, new_s, changed_by or "unknown", now))


def save_table(df, project_id, table_name, changed_by=None):
    """UPSERT rows, saving current table state into undo before overwriting, and log audit."""
    df = normalize_columns(df)

    schema = {
        "procurement": ["stockcode", "description", "current_supplier", "ac_coverage", "next_shortage_date"],
        "industrialization": ["stockcode", "description", "new_supplier", "fai_delivery_date", "first_po_delivery_date"],
        "quality": ["stockcode", "description", "fai_status", "fai_number", "fitcheck_ac", "fitcheck_date", "fitcheck_status"],
    }
    if table_name not in schema:
        raise ValueError(f"Unknown table {table_name}")

    # ensure required columns exist
    for col in schema[table_name]:
        if col not in df.columns:
            df[col] = None
    df = df[schema[table_name]]
    df = df.drop_duplicates(subset=["stockcode"], keep="last")

    # normalize dates
    for col in ["next_shortage_date", "fai_delivery_date", "first_po_delivery_date", "fitcheck_date"]:
        if col in df.columns:
            df[col] = df[col].apply(try_date)

    # defaults
    if table_name == "quality":
        df["fai_status"] = df["fai_status"].fillna("Not Submitted")
        df["fitcheck_status"] = df["fitcheck_status"].fillna("")

    conn = get_connection()
    cur = conn.cursor()

    # save undo snapshot
    cur.execute(f"DELETE FROM {table_name}_undo WHERE project_id=?", (project_id,))
    cur.execute(f"INSERT INTO {table_name}_undo SELECT * FROM {table_name} WHERE project_id=?", (project_id,))

    # upsert + audit
    for _, row in df.iterrows():
        # prepare upsert
        row_tuple = tuple(row[col] for col in df.columns)
        columns = ["project_id"] + list(df.columns)
        placeholders = ", ".join("?" * len(columns))
        updates = ", ".join([f"{c}=excluded.{c}" for c in df.columns if c not in ["stockcode"]])
        sql = f"""
            INSERT INTO {table_name} ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(project_id, stockcode) DO UPDATE SET {updates}
        """

        # fetch old row for audit
        old_row = _fetch_existing_row_dict(conn, table_name, project_id, row["stockcode"])

        # execute upsert
        cur.execute(sql, (project_id,) + row_tuple)

        # fetch new row for audit (as dict)
        new_row = _fetch_existing_row_dict(conn, table_name, project_id, row["stockcode"]) or {}

        # log differences
        log_audit_changes(conn, project_id, table_name, row["stockcode"], old_row, new_row, changed_by)

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


# ---------- Attachments ----------

def save_attachment(project_id: int, stockcode: str, filename: str, file_bytes: bytes, uploaded_by: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO attachments (project_id, stockcode, file_name, file_data, uploaded_by, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (project_id, stockcode.upper().strip(), filename, sqlite3.Binary(file_bytes), uploaded_by or "unknown",
          datetime.utcnow().isoformat(timespec="seconds") + "Z"))
    conn.commit()
    conn.close()


def get_attachments(project_id: int, stockcode: str):
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT id, file_name, uploaded_by, uploaded_at
        FROM attachments
        WHERE project_id=? AND stockcode=?
        ORDER BY uploaded_at DESC
    """, conn, params=(project_id, stockcode.upper().strip()))
    conn.close()
    return df


def get_attachment_blob(attach_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT file_name, file_data FROM attachments WHERE id=?", (attach_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None, None
    return row[0], row[1]


# ---------- Users (Auth) ----------

def load_users_from_excel(df):
    """Insert or update users from an Excel DataFrame."""
    conn = get_connection()
    cur = conn.cursor()

    for _, row in df.iterrows():
        email = str(row.get("Email", "")).strip().lower()
        role = str(row.get("Role", "")).strip().lower()
        password = str(row.get("Password", "")).strip()

        if not email or not password:
            continue

        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        cur.execute("""
            INSERT INTO users (email, role, password_hash)
            VALUES (?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                role=excluded.role,
                password_hash=excluded.password_hash
        """, (email, role, hashed))

    conn.commit()
    conn.close()


def reload_users_from_excel():
    """Reload users.xlsx into the users table."""
    if os.path.exists(USERS_FILE):
        try:
            df_users = pd.read_excel(USERS_FILE)
            load_users_from_excel(df_users)
            print("✅ Users reloaded from Excel.")
        except Exception as e:
            print(f"⚠️ Could not reload users.xlsx: {e}")


def get_user_credentials(email):
    """Fetch role and hashed password for login check."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT role, password_hash FROM users WHERE email=?", (email.lower(),))
    row = cur.fetchone()
    conn.close()
    return row if row else None


def list_users():
    conn = get_connection()
    df = pd.read_sql_query("SELECT email, role FROM users ORDER BY role, email", conn)
    conn.close()
    return df


def set_user_password(email: str, new_password: str):
    conn = get_connection()
    cur = conn.cursor()
    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    cur.execute("UPDATE users SET password_hash=? WHERE email=?", (hashed, email.lower()))
    conn.commit()
    conn.close()
