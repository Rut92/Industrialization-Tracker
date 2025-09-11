import streamlit as st
import pandas as pd
from io import BytesIO
import db_utils

st.set_page_config(page_title="📊 Industrialization Tracker", layout="wide")

db_utils.init_db()

st.title("📊 Industrialization Tracker")

# ---------------- Project Selector ---------------- #
projects = db_utils.get_projects()
project_names = [p[1] for p in projects]
project_lookup = {p[1]: p[0] for p in projects}

selected_project = st.selectbox("Select a project", [""] + project_names)

with st.expander("➕ Create a new project"):
    new_project_name = st.text_input("Project name")
    uploaded_list = st.file_uploader("Upload Stock Codes & Descriptions (Excel)", type=["xlsx"])
    if st.button("Create Project"):
        if new_project_name.strip() != "":
            db_utils.add_project(new_project_name.strip())
            st.success(f"Project '{new_project_name}' created! Refresh dropdown to see it.")
        else:
            st.error("Please enter a project name.")

# ---------------- Utility: Download template ---------------- #
def download_excel_template(columns, filename):
    df_template = pd.DataFrame(columns=columns)
    buffer = BytesIO()
    df_template.to_excel(buffer, index=False)
    st.download_button(
        label=f"📥 Download {filename} Template",
        data=buffer.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ---------------- Tabs ---------------- #
if selected_project:
    pid = project_lookup[selected_project]
    tabs = st.tabs(["Summary", "Procurement", "Industrialization", "Quality"])

    # Summary Tab
    with tabs[0]:
        st.subheader("📌 Summary")
        df_summary = db_utils.get_project_data(pid)
        if df_summary.empty:
            st.info("No data available yet for this project.")
        else:
            st.dataframe(df_summary, use_container_width=True)

    # Procurement Tab
    with tabs[1]:
        st.subheader("📦 Procurement Data")
        cols = ["stockcode", "description", "current_supplier", "price", "ac_coverage", "production_lt", "next_shortage_date"]

        download_excel_template(cols, "Procurement.xlsx")
        upload_file = st.file_uploader("Upload Procurement Data", type=["xlsx"], key="proc_upload")

        if upload_file:
            df = pd.read_excel(upload_file)
            db_utils.clear_table(pid, "procurement")
            db_utils.save_table(df, pid, "procurement")
            st.success("Procurement data uploaded successfully!")

    # Industrialization Tab
    with tabs[2]:
        st.subheader("🏭 Industrialization Data")
        cols = ["stockcode", "description", "new_supplier", "price", "fai_lt", "production_lt", "fai_delivery_date", "first_prod_po_date"]

        download_excel_template(cols, "Industrialization.xlsx")
        upload_file = st.file_uploader("Upload Industrialization Data", type=["xlsx"], key="ind_upload")

        if upload_file:
            df = pd.read_excel(upload_file)
            db_utils.clear_table(pid, "industrialization")
            db_utils.save_table(df, pid, "industrialization")
            st.success("Industrialization data uploaded successfully!")

    # Quality Tab
    with tabs[3]:
        st.subheader("✅ Quality Data")
        cols = ["stockcode", "description", "fair_status", "fair_number", "fitcheck_ac", "fitcheck_date", "fitcheck_status"]

        download_excel_template(cols, "Quality.xlsx")
        upload_file = st.file_uploader("Upload Quality Data", type=["xlsx"], key="qual_upload")

        if upload_file:
            df = pd.read_excel(upload_file)
            db_utils.clear_table(pid, "quality")
            db_utils.save_table(df, pid, "quality")
            st.success("Quality data uploaded successfully!")
