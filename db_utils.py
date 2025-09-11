import sqlite3
import pandas as pd
import streamlit as st  # for error reporting in get_project_data

DB_FILE = "projects.db"

# ------------------ DB Connection ------------------ #
def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

# ------------------ Initialize DB ------------------ #
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

# ------------------ Add Project ------------------ #
def add_project(name, stockcodes_df=None):
    conn = get_connection()
    cur = conn.cursor()
    pid = None
    try:
        name = name.strip()
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

# ------------------ Get Projects ------------------ #
def get_projects():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM projects")
    rows = cur.fetchall()
    conn.close()
    return rows

# ------------------ Get Project Data ------------------ #
def get_project_data(project_id):
    conn = get_connection()
    
    query = """
        SELECT 
            sl.stockcode AS StockCode,
            sl.description AS Description,

            -- Procurement
            pr.current_supplier AS CurrentSupplier,
            pr.price AS CurrentPrice,
            pr.ac_coverage AS ACCoverage,
            pr.production_lt AS ProductionLT,
            pr.next_shortage_date AS NextShortageDate,

            -- Industrialization
            ind.new_supplier AS NewSupplier,
            ind.price AS NewPrice,
            ind.fai_lt AS FAI_LT,
            ind.production_lt AS IndProductionLT,
            ind.fai_delivery_date AS FAIDeliveryDate,
            ind.first_po_delivery_date AS FirstPODeliveryDate,

            -- Quality
            q.fai_status AS FAI_Status,
            q.fai_number AS FAI_Number,
            q.fitcheck_ac AS FitcheckAC,
            q.fitcheck_date AS FitcheckDate,
            q.fitcheck_status AS FitcheckStatus

        FROM stock_list sl
        LEFT JOIN procurement pr 
            ON sl.project_id = pr.project_id AND sl.stockcode = pr.stockcode
        LEFT JOIN industrialization ind 
            ON sl.project_id = ind.project_id AND sl.stockcode = ind.stockcode
        LEFT JOIN quality q 
            ON sl.project_id = q.project_id AND sl.stockcode = q.stockcode
        WHERE sl.project_id = ?
    """

    try:
        df = pd.read_sql_query(query, conn, params=(project_id,))
        
        # Add Overlap column
        if not df.empty:
            df["OverlapDays"] = (
                pd.to_datetime(df["NextShortageDate"], errors="coerce")
                - pd.to_datetime(df["FirstPODeliveryDate"], errors="coerce")
            ).dt.days

    except Exception as e:
        st.error(f"Error fetching project data: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()

    return df
