import streamlit as st
import pandas as pd
from db_utils import (
    init_db,
    add_project,
    get_projects,
    update_project_name,
    add_project_data,
    get_project_data,
)

# Initialize database
init_db()

st.set_page_config(page_title="📊 Industrialization Tracker", layout="wide")

st.title("📊 Industrialization Tracker")

# Sidebar - Manage Projects
st.sidebar.header("📁 Projects")

projects = get_projects()
project_names = [p[1] for p in projects]
project_ids = [p[0] for p in projects]

# Add new project
with st.sidebar.expander("➕ Add New Project"):
    new_project_name = st.text_input("Project Name")
    if st.button("Create Project"):
        if new_project_name.strip():
            add_project(new_project_name.strip())
            st.success(f"Project '{new_project_name}' created!")
            st.rerun()
        else:
            st.error("Project name cannot be empty.")

# Select project
selected_project = st.sidebar.selectbox("Select Project", project_names)

if selected_project:
    pid = project_ids[project_names.index(selected_project)]

    # Tabs
    tab1, tab2 = st.tabs(["📑 Final Table", "✏️ Edit Data"])

    # ---- Tab 1: Final Table ----
    with tab1:
        st.header(f"Final Table - {selected_project}")

        df_final = get_project_data(pid)

        if df_final.empty:
            st.info("No data available yet. Go to 'Edit Data' tab to add entries.")
        else:
            # --- Auto-calc Overlap (Days) ---
            df_final["overlap_days"] = pd.to_datetime(
                df_final["next_shortage_date"], errors="coerce"
            ) - pd.to_datetime(
                df_final["first_production_po_delivery_date"], errors="coerce"
            )
            df_final["overlap_days"] = df_final["overlap_days"].dt.days

            # Column order
            column_order = [
                "stockcode", "description", "ac_coverage",
                "current_supplier", "production_lt", "price",
                "next_shortage_date",
                "new_supplier", "fai_lt", "price_new",
                "fai_delivery_date", "fai_status",
                "fitcheck_status", "fitcheck_ac",
                "first_production_po_delivery_date", "overlap_days"
            ]
            df_display = df_final[column_order]

            # Add column labels with [A], [B], etc.
            col_labels = {}
            alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            for i, col in enumerate(df_display.columns):
                col_labels[col] = f"[{alphabet[i]}] {col.replace('_', ' ').title()}"

            df_display = df_display.rename(columns=col_labels)

            # Styled grouped headers
            supplier1 = st.session_state.get("current_supplier", "Current Supplier")
            supplier2 = st.session_state.get("new_supplier", "New Supplier")

            column_groups = {
                "": ["[A] Stockcode", "[B] Description"],
                supplier1: [
                    "[C] Ac Coverage", "[D] Current Supplier",
                    "[E] Production Lt", "[F] Price",
                    "[G] Next Shortage Date"
                ],
                supplier2: [
                    "[H] New Supplier", "[I] Fai Lt", "[J] Price New",
                    "[K] Fai Delivery Date", "[L] Fai Status",
                    "[M] Fitcheck Status", "[N] Fitcheck Ac",
                    "[O] First Production Po Delivery Date", "[P] Overlap Days"
                ]
            }

            st.dataframe(df_display, use_container_width=True)

    # ---- Tab 2: Editable Data ----
    with tab2:
        st.header("Edit Project Data")

        # Supplier name inputs
        col1, col2 = st.columns(2)
        with col1:
            st.session_state["current_supplier"] = st.text_input(
                "Enter Current Supplier Name",
                st.session_state.get("current_supplier", "Current Supplier")
            )
        with col2:
            st.session_state["new_supplier"] = st.text_input(
                "Enter New Supplier Name",
                st.session_state.get("new_supplier", "New Supplier")
            )

        df_edit = get_project_data(pid)
        if df_edit.empty:
            st.info("No data to edit.")
        else:
            # 🔹 Hide overlap_days column from editor
            if "overlap_days" in df_edit.columns:
                df_edit = df_edit.drop(columns=["overlap_days"])

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
                # --- Auto-calc Overlap before saving ---
                if not edited_df.empty:
                    edited_df["overlap_days"] = pd.to_datetime(
                        edited_df["next_shortage_date"], errors="coerce"
                    ) - pd.to_datetime(
                        edited_df["first_production_po_delivery_date"], errors="coerce"
                    )
                    edited_df["overlap_days"] = edited_df["overlap_days"].dt.days

                add_project_data(pid, edited_df, replace=True)
                st.success("Changes saved.")
                st.rerun()
