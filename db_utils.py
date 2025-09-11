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

    # Master stock list (common to all tabs)
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            stockcode TEXT,
            description TEXT,
            current_supplier TEXT,
            price REAL,
            ac_coverage TEXT,
            production_lt INTEGER,
            next_shortage_date TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    """)

    # Industrialization table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS industrialization (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            stockcode TEXT,
            description TEXT,
            new_supplier TEXT,
            price REAL,
            fai_lt INTEGER,
            production_lt INTEGER,
            fai_delivery_date TEXT,
            first_po_delivery_date TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    """)

    # Quality table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quality (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    try:
        cur.execute("INSERT INTO projects (name) VALUES (?)", (name,))
        pid = cur.lastrowid

        # Save stock list if provided
        if stockcodes_df is not None:
            for _, row in stockcodes_df.iterrows():
                cur.execute("""
                    INSERT INTO stock_list (project_id, stockcode, description)
                    VALUES (?, ?, ?)
                """, (pid, row["StockCode"], row["Description"]))

        conn.commit()
    except sqlite3.IntegrityError:
        # Project already exists
        pid = None
    finally:
        conn.close()

    return pid


def get_projects():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM projects")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_project_data(project_id):
    conn = get_connection()
    query = """
        SELECT 
            sl.stockcode AS [A]StockCode,
            sl.description AS [B]Description,

            -- Procurement
            pr.current_supplier AS [C]CurrentSupplier,
            pr.price AS [D]Price,
            pr.ac_coverage AS [E]AC_Coverage,
            pr.production_lt AS [F]Production_LT,
            pr.next_shortage_date AS [G]Next_Shortage_Date,

            -- Industrialization
            ind.new_supplier AS [H]NewSupplier,
            ind.price AS [I]Price,
            ind.fai_lt AS [J]FAI_LT,
            ind.production_lt AS [K]Production_LT,
            ind.fai_delivery_date AS [L]FAI_Delivery_Date,
            ind.first_po_delivery_date AS [M]First_PO_Delivery_Date,

            -- Quality
            q.fai_status AS [N]FAI_Status,
            q.fai_number AS [O]FAI_Number,
            q.fitcheck_ac AS [P]Fitcheck_AC,
            q.fitcheck_date AS [Q]Fitcheck_Date,
            q.fitcheck_status AS [R]Fitcheck_Status

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

    # Add Overlap column
    if not df.empty:
        df["[S]Overlap_Days"] = (
            pd.to_datetime(df["[G]Next_Shortage_Date"], errors="coerce")
            - pd.to_datetime(df["[M]First_PO_Delivery_Date"], errors="coerce")
        ).dt.days

    return df
