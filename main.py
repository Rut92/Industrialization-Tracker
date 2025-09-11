import streamlit as st
import pandas as pd
from db_utils import init_db, add_project, get_projects, save_table, get_project_data

st.set_page_config(page_title="📊 Industrialization Tracker", layout="wide")

# Initialize DB
init_db()

# Sidebar - project selection/creation
st.sidebar.header("📁 Project Management")

projects = get_projects()
project_names = projects["name"].tolist() if not projects.empty else []

selected_project = st.sidebar.selectbox("Select Project", [""] + project_names)

new_project_name = st.sidebar.text_input("Create New Project")
if st.sidebar.button("➕ Create Project") and new_project_name.strip():
    project_id = add_project(new_project_name.strip())
    if new_project_name.strip() in project_names:
        st.sidebar.info(f"Project '{new_project_name}' already exists. Opening existing project.")
    else:
        st.sidebar.success(f"Project '{new_project_name}' created successfully!")
    selected_project = new_project_name.strip()

if not selected_project:
    st.warning("Please select or create a project to continue.")
    st.stop()

# Get project_id
projects = get_projects()
pid = projects.loc[projects["name"] == selected_project, "id"].values[0]

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Summary", "📦 Procurement", "🏭 Industrialization", "✅ Quality"])

# ================= TAB 1: SUMMARY =================
with tab1:
    st.subheader("📊 Project Summary")
    df_final = get_project_data(pid)

    if not df_final.empty:
        # Grouped headers
        grouped_headers = pd.MultiIndex.from_tuples([
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
            ("Industrialization", "1st Production PO Delivery Date"),
            ("Industrialization", "New Supplier"),
            ("Industrialization", "Overlap (Days)"),
            ("Quality", "FAIR Status"),
            ("Quality", "FAIR#"),
            ("Quality", "Fitcheck AC"),
            ("Quality", "Fitcheck Date"),
            ("Quality", "Fitcheck Status")
        ])

        df_final.columns = grouped_headers
        st.dataframe(df_final, use_container_width=True)

    else:
        st.info("No data yet. Add details in the Procurement, Industrialization, or Quality tabs.")

# ================= TAB 2: PROCUREMENT =================
with tab2:
    st.subheader("📦 Procurement Data")
    st.info("Upload or edit procurement data here.")
    current_supplier = st.text_input("Enter Current Supplier Name", "Current Supplier")

    uploaded_file = st.file_uploader("Upload Procurement Excel", type=["xlsx"])
    if uploaded_file:
        df_proc = pd.read_excel(uploaded_file)
        df_proc["project_id"] = pid
        df_proc["current_supplier"] = current_supplier
        save_table(df_proc, pid, "procurement")
        st.success("Procurement data uploaded successfully!")

    st.download_button("📥 Download Procurement Template",
                       pd.DataFrame(columns=["stockcode", "description", "price", "ac_coverage", "production_lt", "next_shortage_date"]).to_csv(index=False),
                       "procurement_template.csv", "text/csv")

# ================= TAB 3: INDUSTRIALIZATION =================
with tab3:
    st.subheader("🏭 Industrialization Data")
    st.info("Upload or edit industrialization data here.")
    new_supplier = st.text_input("Enter New Supplier Name", "New Supplier")

    uploaded_file = st.file_uploader("Upload Industrialization Excel", type=["xlsx"])
    if uploaded_file:
        df_ind = pd.read_excel(uploaded_file)
        df_ind["project_id"] = pid
        df_ind["new_supplier"] = new_supplier
        save_table(df_ind, pid, "industrialization")
        st.success("Industrialization data uploaded successfully!")

    st.download_button("📥 Download Industrialization Template",
                       pd.DataFrame(columns=["stockcode", "description", "price", "fai_lt", "production_lt", "fai_delivery_date", "first_po_delivery_date"]).to_csv(index=False),
                       "industrialization_template.csv", "text/csv")

# ================= TAB 4: QUALITY =================
with tab4:
    st.subheader("✅ Quality Data")
    st.info("Upload or edit quality data here.")

    uploaded_file = st.file_uploader("Upload Quality Excel", type=["xlsx"])
    if uploaded_file:
        df_qual = pd.read_excel(uploaded_file)
        df_qual["project_id"] = pid
        save_table(df_qual, pid, "quality")
        st.success("Quality data uploaded successfully!")

    st.download_button("📥 Download Quality Template",
                       pd.DataFrame(columns=["stockcode", "description", "fair_status", "fair_number", "fitcheck_ac", "fitcheck_date", "fitcheck_status"]).to_csv(index=False),
                       "quality_template.csv", "text/csv")
