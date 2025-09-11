import streamlit as st
import pandas as pd
from io import BytesIO
import db_utils

st.set_page_config(page_title="📊 Industrialization Tracker", layout="wide")
db_utils.init_db()

st.title("📊 Industrialization Tracker")

# --- Create project ---
with st.expander("➕ Create New Project"):
    new_project_name = st.text_input("Project Name")
    uploaded_file = st.file_uploader("Upload Stock Codes & Descriptions (Excel)", type=["xlsx"])

    if st.button("Create Project"):
        if new_project_name.strip():
            stockcodes_df = None
            if uploaded_file:
                stockcodes_df = pd.read_excel(uploaded_file)
                if not all(c in stockcodes_df.columns for c in ["StockCode", "Description"]):
                    st.error("Excel must have 'StockCode' and 'Description' columns.")
                    stockcodes_df = None
            pid = db_utils.add_project(new_project_name.strip(), stockcodes_df)
            st.success(f"Project '{new_project_name}' created or opened.")
        else:
            st.error("Enter a project name.")

# --- Select project ---
projects = db_utils.get_projects()
if projects.empty:
    st.info("No projects yet. Create one above.")
    st.stop()

project_map = {name: pid for pid, name in projects.values}
selected_name = st.selectbox("Select Project", list(project_map.keys()))
pid = project_map[selected_name]

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["📌 Summary", "📦 Procurement", "🏭 Industrialization", "✅ Quality"])

# --- Summary ---
with tab1:
    st.subheader("📌 Project Summary")
    df = db_utils.get_project_data(pid)
    if df.empty:
        st.info("No data yet. Upload in other tabs.")
    else:
        st.dataframe(df, use_container_width=True)

        buf = BytesIO()
        df.to_excel(buf, index=False)
        st.download_button("📥 Download Summary", buf.getvalue(), file_name="summary.xlsx")

# --- Procurement ---
with tab2:
    st.subheader("📦 Procurement Data")
    cols = ["StockCode", "Description", "CurrentSupplier", "Price", "AC_Coverage", "Production_LT", "Next_Shortage_Date"]

    buf = BytesIO()
    pd.DataFrame(columns=cols).to_excel(buf, index=False)
    st.download_button("📥 Download Template", buf.getvalue(), file_name="procurement_template.xlsx")

    f = st.file_uploader("Upload Procurement Data", type=["xlsx"], key="proc")
    if f:
        df_upload = pd.read_excel(f)
        db_utils.clear_table(pid, "procurement")
        db_utils.save_table(df_upload, pid, "procurement")
        st.success("Procurement data saved.")
        st.experimental_rerun()

# --- Industrialization ---
with tab3:
    st.subheader("🏭 Industrialization Data")
    cols = ["StockCode", "Description", "NewSupplier", "Price", "FAI_LT", "Production_LT", "FAI_Delivery_Date", "First_PO_Delivery_Date"]

    buf = BytesIO()
    pd.DataFrame(columns=cols).to_excel(buf, index=False)
    st.download_button("📥 Download Template", buf.getvalue(), file_name="industrialization_template.xlsx")

    f = st.file_uploader("Upload Industrialization Data", type=["xlsx"], key="ind")
    if f:
        df_upload = pd.read_excel(f)
        db_utils.clear_table(pid, "industrialization")
        db_utils.save_table(df_upload, pid, "industrialization")
        st.success("Industrialization data saved.")
        st.experimental_rerun()

# --- Quality ---
with tab4:
    st.subheader("✅ Quality Data")
    cols = ["StockCode", "Description", "FAI_Status", "FAI_Number", "Fitcheck_AC", "Fitcheck_Date", "Fitcheck_Status"]

    buf = BytesIO()
    pd.DataFrame(columns=cols).to_excel(buf, index=False)
    st.download_button("📥 Download Template", buf.getvalue(), file_name="quality_template.xlsx")

    f = st.file_uploader("Upload Quality Data", type=["xlsx"], key="qual")
    if f:
        df_upload = pd.read_excel(f)
        db_utils.clear_table(pid, "quality")
        db_utils.save_table(df_upload, pid, "quality")
        st.success("Quality data saved.")
        st.experimental_rerun()
