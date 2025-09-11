import streamlit as st
import pandas as pd
from db_utils import (
    init_db, add_project, get_projects, update_project_name,
    add_project_data, get_project_data, detect_header_and_read
)

st.set_page_config(page_title="📊 Industrialization Tracker", layout="wide")

# Initialize DB
init_db()

# Sidebar – Project Management
st.sidebar.header("Project Management")
with st.sidebar:
    project_name = st.text_input("New Project Name")
    uploaded_file = st.file_uploader("Upload Excel for new project", type=["xlsx"])
    if st.button("➕ Create Project"):
        if project_name:
            pid = add_project(project_name)
            if uploaded_file:
                df = detect_header_and_read(uploaded_file)
                add_project_data(pid, df)
            st.success(f"Project '{project_name}' created!")

    projects = get_projects()
    if not projects.empty:
        selected = st.selectbox("Select Project", projects["name"])
        pid = projects.loc[projects["name"] == selected, "id"].values[0]
        new_name = st.text_input("Rename Project", selected)
        if st.button("✏️ Update Name"):
            update_project_name(pid, new_name)
            st.rerun()
    else:
        st.info("No projects yet. Create one above.")
        st.stop()

# Tabs
tab1, tab2 = st.tabs(["📑 Final Table", "✍️ Edit Data"])

# ---- Tab 1: Final Table ----
with tab1:
    st.header(f"Project: {selected} - Final Table")
    df_final = get_project_data(pid)
    if df_final.empty:
        st.info("No rows found for this project.")
    else:
        # Column renaming
        col_map = {
            "stockcode": "[A] StockCode",
            "description": "[B] Description",
            "ac_coverage": "[C] AC Coverage",
            "current_production_lt": "[D] Current Production LT",
            "current_price": "[E] Current Price",
            "next_shortage_date": "[F] Next Shortage Date",
            "fai_lt": "[G] FAI LT",
            "new_supplier_production_lt": "[H] New Supplier Production LT",
            "new_price": "[I] New Price",
            "fai_delivery_date": "[J] FAI Delivery Date",
            "fai_status": "[K] FAI Status",
            "fitcheck_status": "[L] Fitcheck Status",
            "fitcheck_ac": "[M] Fitcheck A/C",
            "first_production_po_delivery_date": "[N] 1st Production PO Delivery Date",
            "overlap_days": "[O] Overlap (Days)"
        }
        df_display = df_final.rename(columns=col_map)

        # Supplier names
        current_supplier = st.session_state.get("current_supplier", "Current Supplier")
        new_supplier = st.session_state.get("new_supplier", "New Supplier")

        # MultiIndex headers
        multi_cols = pd.MultiIndex.from_tuples([
            ("", "[A] StockCode"),
            ("", "[B] Description"),
            (current_supplier, "[C] AC Coverage"),
            (current_supplier, "[D] Current Production LT"),
            (current_supplier, "[E] Current Price"),
            (current_supplier, "[F] Next Shortage Date"),
            (new_supplier, "[G] FAI LT"),
            (new_supplier, "[H] New Supplier Production LT"),
            (new_supplier, "[I] New Price"),
            (new_supplier, "[J] FAI Delivery Date"),
            (new_supplier, "[K] FAI Status"),
            (new_supplier, "[L] Fitcheck Status"),
            (new_supplier, "[M] Fitcheck A/C"),
            (new_supplier, "[N] 1st Production PO Delivery Date"),
            (new_supplier, "[O] Overlap (Days)"),
        ])
        df_display.columns = multi_cols

        st.dataframe(df_display, use_container_width=True)

# ---- Tab 2: Editable Data ----
with tab2:
    st.header("Edit Project Data")

    # Supplier name inputs
    col1, col2 = st.columns(2)
    with col1:
        st.session_state["current_supplier"] = st.text_input(
            "Enter Current Supplier Name", st.session_state.get("current_supplier", "Current Supplier")
        )
    with col2:
        st.session_state["new_supplier"] = st.text_input(
            "Enter New Supplier Name", st.session_state.get("new_supplier", "New Supplier")
        )

    df_edit = get_project_data(pid)
    if df_edit.empty:
        st.info("No data to edit.")
    else:
        edited_df = st.data_editor(
            df_edit,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "fai_status": st.column_config.SelectboxColumn(
                    "FAI Status",
                    options=["Not Submitted", "Under Review", "Failed", "Passed"],
                    default="Not Submitted"
                ),
                "fitcheck_status": st.column_config.SelectboxColumn(
                    "Fitcheck Status",
                    options=["Not Scheduled", "Scheduled", "Failed", "Passed"],
                    default="Not Scheduled"
                ),
            }
        )

        if st.button("💾 Save Changes"):
            add_project_data(pid, edited_df, replace=True)
            st.success("Changes saved.")
            st.rerun()
