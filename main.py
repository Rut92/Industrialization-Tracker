import streamlit as st
import pandas as pd
from io import BytesIO
from db_utils import (
    init_db,
    add_project,
    get_projects,
    add_project_data,
    get_project_data,
)

# Initialize DB
init_db()
st.set_page_config(page_title="📊 Industrialization Tracker", layout="wide")
st.title("📊 Industrialization Tracker")

# Sidebar - Manage projects
st.sidebar.header("📁 Projects")

projects = get_projects()
project_names = [p[1] for p in projects]
project_ids = [p[0] for p in projects]

# ========== Create New Project ==========
with st.sidebar.expander("➕ Create Project"):
    new_project_name = st.text_input("Project Name")
    uploaded_master = st.file_uploader(
        "Upload Stock Codes & Descriptions (Excel)",
        type=["xlsx"],
        key="proj_upload"
    )

    if st.button("Create Project"):
        if not new_project_name.strip():
            st.error("❌ Project name is required")
        elif uploaded_master is None:
            st.error("❌ Please upload stock codes & descriptions Excel")
        else:
            # Read stock codes & descriptions
            df_master = pd.read_excel(uploaded_master)
            if not {"stockcode", "description"}.issubset(df_master.columns.str.lower()):
                st.error("❌ Excel must have 'stockcode' and 'description' columns.")
            else:
                add_project(new_project_name.strip())
                st.success(f"✅ Project '{new_project_name}' created!")
                st.rerun()

# ========== Select Project ==========
selected_project = st.sidebar.selectbox("Select Project", project_names)

if selected_project:
    pid = project_ids[project_names.index(selected_project)]

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📑 Summary",
        "📦 Procurement",
        "🏭 Industrialization",
        "✅ Quality"
    ])

    # ---------------- TAB 1: SUMMARY ----------------
    with tab1:
        st.header(f"Summary - {selected_project}")
        df_summary = get_project_data(pid)

        if df_summary.empty:
            st.info("Upload data in Procurement, Industrialization, or Quality tabs.")
        else:
            # Calculate Overlap (Days)
            df_summary["overlap_days"] = pd.to_datetime(
                df_summary["next_shortage_date"], errors="coerce"
            ) - pd.to_datetime(
                df_summary["first_production_po_delivery_date"], errors="coerce"
            )
            df_summary["overlap_days"] = df_summary["overlap_days"].dt.days

            # Column groups
            procurement_cols = [
                "price", "ac_coverage", "production_lt", "next_shortage_date"
            ]
            indust_cols = [
                "price_new", "fai_lt", "production_lt_ind", "fai_delivery_date",
                "first_production_po_delivery_date", "overlap_days"
            ]
            quality_cols = [
                "fai_status", "fai_no", "fitcheck_ac", "fitcheck_date", "fitcheck_status"
            ]

            column_order = ["stockcode", "description"] + \
                           procurement_cols + indust_cols + quality_cols

            df_display = df_summary[column_order]

            # Label columns with groups
            col_labels = {
                "stockcode": "[A] Stockcode",
                "description": "[B] Description",
                "price": "[C] Price",
                "ac_coverage": "[D] AC Coverage",
                "production_lt": "[E] Production LT",
                "next_shortage_date": "[F] Next Shortage Date",
                "price_new": "[G] Price",
                "fai_lt": "[H] FAI LT",
                "production_lt_ind": "[I] Production LT",
                "fai_delivery_date": "[J] FAI Delivery Date",
                "first_production_po_delivery_date": "[K] 1st Production PO Date",
                "overlap_days": "[L] Overlap (Days)",
                "fai_status": "[M] FAI Status",
                "fai_no": "[N] FAI#",
                "fitcheck_ac": "[O] Fitcheck AC",
                "fitcheck_date": "[P] Fitcheck Date",
                "fitcheck_status": "[Q] Fitcheck Status"
            }

            df_display = df_display.rename(columns=col_labels)

            st.dataframe(df_display, use_container_width=True)

    # ---------------- TAB 2: PROCUREMENT ----------------
    with tab2:
        st.header("Procurement Data")

        # Template download
        template = pd.DataFrame(columns=["stockcode", "description", "price", "ac_coverage", "production_lt", "next_shortage_date"])
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            template.to_excel(writer, index=False)
        st.download_button("⬇️ Download Procurement Template", data=buffer.getvalue(), file_name="procurement_template.xlsx")

        upload_file = st.file_uploader("Upload Procurement Data (Excel)", type=["xlsx"], key="proc_upload")
        if upload_file:
            df_upload = pd.read_excel(upload_file)
            add_project_data(pid, df_upload, replace=False)
            st.success("✅ Procurement data uploaded!")

        # Editable table
        df_proc = get_project_data(pid)
        if not df_proc.empty:
            cols = ["stockcode", "description", "price", "ac_coverage", "production_lt", "next_shortage_date"]
            df_edit = df_proc[cols]
            edited = st.data_editor(df_edit, use_container_width=True, num_rows="dynamic")
            if st.button("💾 Save Procurement"):
                add_project_data(pid, edited, replace=False)
                st.success("Saved Procurement data!")
                st.rerun()

    # ---------------- TAB 3: INDUSTRIALIZATION ----------------
    with tab3:
        st.header("Industrialization Data")

        template = pd.DataFrame(columns=["stockcode", "description", "price_new", "fai_lt", "production_lt_ind", "fai_delivery_date", "first_production_po_delivery_date"])
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            template.to_excel(writer, index=False)
        st.download_button("⬇️ Download Industrialization Template", data=buffer.getvalue(), file_name="industrialization_template.xlsx")

        upload_file = st.file_uploader("Upload Industrialization Data (Excel)", type=["xlsx"], key="ind_upload")
        if upload_file:
            df_upload = pd.read_excel(upload_file)
            add_project_data(pid, df_upload, replace=False)
            st.success("✅ Industrialization data uploaded!")

        df_ind = get_project_data(pid)
        if not df_ind.empty:
            cols = ["stockcode", "description", "price_new", "fai_lt", "production_lt_ind", "fai_delivery_date", "first_production_po_delivery_date"]
            df_edit = df_ind[cols]
            edited = st.data_editor(df_edit, use_container_width=True, num_rows="dynamic")
            if st.button("💾 Save Industrialization"):
                add_project_data(pid, edited, replace=False)
                st.success("Saved Industrialization data!")
                st.rerun()

    # ---------------- TAB 4: QUALITY ----------------
    with tab4:
        st.header("Quality Data")

        template = pd.DataFrame(columns=["stockcode", "description", "fai_status", "fai_no", "fitcheck_ac", "fitcheck_date", "fitcheck_status"])
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            template.to_excel(writer, index=False)
        st.download_button("⬇️ Download Quality Template", data=buffer.getvalue(), file_name="quality_template.xlsx")

        upload_file = st.file_uploader("Upload Quality Data (Excel)", type=["xlsx"], key="qual_upload")
        if upload_file:
            df_upload = pd.read_excel(upload_file)
            add_project_data(pid, df_upload, replace=False)
            st.success("✅ Quality data uploaded!")

        df_q = get_project_data(pid)
        if not df_q.empty:
            cols = ["stockcode", "description", "fai_status", "fai_no", "fitcheck_ac", "fitcheck_date", "fitcheck_status"]
            df_edit = df_q[cols]
            edited = st.data_editor(df_edit, use_container_width=True, num_rows="dynamic")
            if st.button("💾 Save Quality"):
                add_project_data(pid, edited, replace=False)
                st.success("Saved Quality data!")
                st.rerun()
