import streamlit as st
import pandas as pd
from db_utils import init_db, add_project, get_projects, save_table, get_project_data

st.set_page_config(page_title="Industrialization Tracker", layout="wide")
init_db()

st.title("📊 Industrialization Tracker")

# --- Project creation ---
with st.sidebar:
    st.header("Project Management")
    new_project_name = st.text_input("Enter new project name")
    if st.button("Create Project"):
        if new_project_name.strip():
            pid = add_project(new_project_name.strip())
            st.success(f"Project '{new_project_name}' created or opened successfully!")
            st.session_state["current_project"] = pid

    projects = get_projects()
    if not projects.empty:
        selected_project = st.selectbox("Select Project", projects["name"].tolist())
        if selected_project:
            pid = projects.loc[projects["name"] == selected_project, "id"].values[0]
            st.session_state["current_project"] = pid

if "current_project" not in st.session_state:
    st.warning("Please create or select a project to continue.")
    st.stop()

pid = st.session_state["current_project"]

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Procurement", "Industrialization", "Quality"])

# --- Procurement ---
with tab2:
    st.subheader("Procurement Data")
    current_supplier = st.text_input("Enter Current Supplier", value="Current Supplier")
    uploaded_file = st.file_uploader("Upload Procurement Excel", type=["xlsx"], key="proc_upload")
    if uploaded_file:
        df_proc = pd.read_excel(uploaded_file)
        df_proc["project_id"] = pid
        df_proc["current_supplier"] = current_supplier
        save_table(df_proc, pid, "procurement")
        st.success("Procurement data uploaded successfully!")
        st.experimental_rerun()

    st.info("Template columns: stockcode, description, Price, AC Coverage, Production LT, Next Shortage Date")

# --- Industrialization ---
with tab3:
    st.subheader("Industrialization Data")
    new_supplier = st.text_input("Enter New Supplier", value="New Supplier")
    uploaded_file = st.file_uploader("Upload Industrialization Excel", type=["xlsx"], key="ind_upload")
    if uploaded_file:
        df_ind = pd.read_excel(uploaded_file)
        df_ind["project_id"] = pid
        df_ind["new_supplier"] = new_supplier
        save_table(df_ind, pid, "industrialization")
        st.success("Industrialization data uploaded successfully!")
        st.experimental_rerun()

    st.info("Template columns: stockcode, description, Price, FAI LT, Production LT, FAI Delivery Date, 1st Production PO delivery Date")

# --- Quality ---
with tab4:
    st.subheader("Quality Data")
    uploaded_file = st.file_uploader("Upload Quality Excel", type=["xlsx"], key="qual_upload")
    if uploaded_file:
        df_qual = pd.read_excel(uploaded_file)
        df_qual["project_id"] = pid
        save_table(df_qual, pid, "quality")
        st.success("Quality data uploaded successfully!")
        st.experimental_rerun()

    st.info("Template columns: stockcode, description, FAIR Status, FAIR#, Fitcheck AC, Fitcheck Date, Fitcheck Status")

# --- Summary ---
with tab1:
    st.subheader("Summary Table")
    df_final = get_project_data(pid)

    if not df_final.empty:
        # Grouped headers
        multi_columns = pd.MultiIndex.from_tuples([
            ("", "Stockcode"),
            ("", "Description"),
            ("Procurement", "Price"),
            ("Procurement", "AC Coverage"),
            ("Procurement", "Production LT"),
            ("Procurement", "Next Shortage Date"),
            ("Procurement", "Current Supplier"),
            ("Industrialization", "Price"),
            ("Industrialization", "FAI LT"),
            ("Industrialization", "Production LT"),
            ("Industrialization", "FAI Delivery Date"),
            ("Industrialization", "1st Production PO delivery Date"),
            ("Industrialization", "New Supplier"),
            ("Quality", "FAI Status"),
            ("Quality", "FAI Number"),
            ("Quality", "Fitcheck AC"),
            ("Quality", "Fitcheck Date"),
            ("Quality", "Fitcheck Status"),
            ("Industrialization", "Overlap (Days)")
        ])

        df_final = df_final.reindex(columns=[c[1] for c in multi_columns], fill_value="")
        df_final.columns = multi_columns

        st.dataframe(df_final, width="stretch")
    else:
        st.info("No data available yet for this project.")
