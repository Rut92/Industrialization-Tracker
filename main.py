import streamlit as st
import pandas as pd
from io import BytesIO
import db_utils

# Initialize DB first
db_utils.init_db()

st.set_page_config(page_title="📊 Industrialization Tracker", layout="wide")
st.title("📊 Industrialization Tracker")

# ------------------ Create a new project ------------------ #
with st.expander("➕ Create a new project"):
    new_project_name = st.text_input("Project name")
    uploaded_file = st.file_uploader("Upload Stock Codes & Descriptions (Excel)", type=["xlsx"])

    if st.button("Create Project"):
        if new_project_name.strip() != "":
            stockcodes_df = None
            if uploaded_file:
                stockcodes_df = pd.read_excel(uploaded_file)
                # Validate required columns
                if not all(col in stockcodes_df.columns for col in ["StockCode", "Description"]):
                    st.error("Excel must have 'StockCode' and 'Description' columns")
                    stockcodes_df = None

            pid = db_utils.add_project(new_project_name.strip(), stockcodes_df)
            if pid:
                st.success(f"Project '{new_project_name}' created successfully!")
            else:
                st.warning(f"Project '{new_project_name}' already exists.")

# ------------------ Select project ------------------ #
# Refresh project list after creation
projects = db_utils.get_projects()  # returns list of (id, name)
project_dict = {name: pid for pid, name in projects}

if not project_dict:
    st.info("No projects available. Create a new project above.")
    st.stop()

selected_project = st.selectbox("Select a project", [""] + list(project_dict.keys()))
pid = project_dict.get(selected_project)

if pid is None or selected_project == "":
    st.info("Please select a project to view details.")
    st.stop()

# ------------------ Tabs ------------------ #
tab1, tab2, tab3, tab4 = st.tabs(["📌 Summary", "📦 Procurement", "🏭 Industrialization", "✅ Quality"])

# ------------------ Summary ------------------ #
with tab1:
    st.subheader("📌 Project Summary")
    try:
        df_summary = db_utils.get_project_data(pid)
        if df_summary.empty:
            st.info("No data available for this project yet.")
        else:
            st.dataframe(df_summary, use_container_width=True)
            # Download option
            buffer = BytesIO()
            df_summary.to_excel(buffer, index=False)
            st.download_button("📥 Download Summary", buffer.getvalue(), file_name="summary.xlsx")
    except Exception as e:
        st.error(f"Error fetching project data: {e}")

# ------------------ Procurement ------------------ #
with tab2:
    st.subheader("📦 Procurement Data")
    st.info("Upload or edit procurement data (StockCode & Description must match project list).")

    template = pd.DataFrame(columns=[
        "StockCode", "Description", "CurrentSupplier", "Price",
        "AC_Coverage", "Production_LT", "Next_Shortage_Date"
    ])
    buffer = BytesIO()
    template.to_excel(buffer, index=False)
    st.download_button("📥 Download Procurement Template", buffer.getvalue(), file_name="procurement_template.xlsx")

    uploaded = st.file_uploader("Upload Procurement Data", type=["xlsx"], key="proc_upload")
    if uploaded:
        st.success("Procurement upload feature not fully implemented yet.")

# ------------------ Industrialization ------------------ #
with tab3:
    st.subheader("🏭 Industrialization Data")
    st.info("Upload or edit industrialization data.")

    template = pd.DataFrame(columns=[
        "StockCode", "Description", "NewSupplier", "Price",
        "FAI_LT", "Production_LT", "FAI_Delivery_Date", "First_PO_Delivery_Date"
    ])
    buffer = BytesIO()
    template.to_excel(buffer, index=False)
    st.download_button("📥 Download Industrialization Template", buffer.getvalue(), file_name="industrialization_template.xlsx")

    uploaded = st.file_uploader("Upload Industrialization Data", type=["xlsx"], key="ind_upload")
    if uploaded:
        st.success("Industrialization upload feature not fully implemented yet.")

# ------------------ Quality ------------------ #
with tab4:
    st.subheader("✅ Quality Data")
    st.info("Upload or edit quality data.")

    template = pd.DataFrame(columns=[
        "StockCode", "Description", "FAI_Status", "FAI_Number",
        "Fitcheck_AC", "Fitcheck_Date", "Fitcheck_Status"
    ])
    buffer = BytesIO()
    template.to_excel(buffer, index=False)
    st.download_button("📥 Download Quality Template", buffer.getvalue(), file_name="quality_template.xlsx")

    uploaded = st.file_uploader("Upload Quality Data", type=["xlsx"], key="qual_upload")
    if uploaded:
        st.success("Quality upload feature not fully implemented yet.")
