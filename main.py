import streamlit as st
import pandas as pd
import io
from db_utils import (
    init_db, add_project, get_projects, add_project_data,
    get_project_data, detect_header_and_read
)

# ---- Initialize DB ----
init_db()
st.set_page_config(page_title="📊 Industrialization Tracker", layout="wide")
st.title("📊 Industrialization Tracker")

# ---- Sidebar: Projects ----
st.sidebar.header("📁 Projects")
projects = get_projects()

if projects.empty:
    st.warning("No projects found. Please create a project first.")
else:
    project_names = projects["name"].tolist()
    project_ids = projects["id"].tolist()

    # Add new project
    with st.sidebar.expander("➕ Add New Project"):
        new_project_name = st.text_input("Project Name")
        if st.button("Create Project"):
            if new_project_name.strip():
                add_project(new_project_name.strip())
                st.success(f"Project '{new_project_name}' created!")
                st.experimental_rerun()
            else:
                st.error("Project name cannot be empty.")

    # Select project
    selected_project = st.sidebar.selectbox("Select Project", project_names)

    if selected_project:
        pid = project_ids[project_names.index(selected_project)]
        tab1, tab2 = st.tabs(["📑 Final Table", "✏️ Edit Data"])

        # ---- Tab 1: Final Table ----
        with tab1:
            st.header(f"Final Table - {selected_project}")
            df_final = get_project_data(pid)

            if df_final.empty:
                st.info("No data available yet. Go to 'Edit Data' tab to add entries.")
            else:
                # Auto-calc overlap_days
                df_final["overlap_days"] = pd.to_datetime(
                    df_final["next_shortage_date"], errors="coerce"
                ) - pd.to_datetime(
                    df_final["first_production_po_delivery_date"], errors="coerce"
                )
                df_final["overlap_days"] = df_final["overlap_days"].dt.days

                column_order = [
                    "stockcode", "description", "ac_coverage",
                    "current_production_lt", "current_price", "next_shortage_date",
                    "fai_lt", "new_supplier_production_lt", "new_price",
                    "fai_delivery_date", "fai_status", "fitcheck_status",
                    "fitcheck_ac", "first_production_po_delivery_date", "overlap_days"
                ]
                df_display = df_final[column_order]

                # Add [A], [B], etc.
                col_labels = {col: f"[{chr(65+i)}] {col.replace('_',' ').title()}" 
                              for i, col in enumerate(df_display.columns)}
                df_display = df_display.rename(columns=col_labels)

                st.dataframe(df_display, use_container_width=True)

        # ---- Tab 2: Edit Data ----
        with tab2:
            st.header("Edit Project Data")

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

            # --- Template Download ---
            template_cols = [
                "stockcode", "description", "ac_coverage",
                "current_production_lt", "current_price", "next_shortage_date",
                "fai_lt", "new_supplier_production_lt", "new_price",
                "fai_delivery_date", "fai_status", "fitcheck_status",
                "fitcheck_ac", "first_production_po_delivery_date"
            ]
            template_df = pd.DataFrame(columns=template_cols)
            towrite = io.BytesIO()
            template_df.to_excel(towrite, index=False, engine="openpyxl")
            towrite.seek(0)
            st.download_button(
                label="📥 Download Template Excel",
                data=towrite,
                file_name="project_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # --- File Upload ---
            uploaded_file = st.file_uploader("Upload Filled Excel File", type=["xlsx"])
            if uploaded_file:
                uploaded_df = detect_header_and_read(uploaded_file)
                if not uploaded_df.empty:
                    add_project_data(pid, uploaded_df, replace=True)
                    st.success("Data uploaded and table updated!")
                    st.experimental_rerun()

            # --- Editable Data ---
            df_edit = get_project_data(pid)
            if df_edit.empty:
                st.info("No data to edit. Upload a file or enter data manually.")
            else:
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
                            default=None
                        ),
                        "fitcheck_status": st.column_config.SelectboxColumn(
                            "Fitcheck Status",
                            options=["Not Scheduled", "Scheduled", "Failed", "Passed"],
                            default=None
                        ),
                    }
                )

                if st.button("💾 Save Changes"):
                    if not edited_df.empty:
                        edited_df["overlap_days"] = pd.to_datetime(
                            edited_df["next_shortage_date"], errors="coerce"
                        ) - pd.to_datetime(
                            edited_df["first_production_po_delivery_date"], errors="coerce"
                        )
                        edited_df["overlap_days"] = edited_df["overlap_days"].dt.days

                    add_project_data(pid, edited_df, replace=True)
                    st.success("Changes saved.")
                    st.experimental_rerun()
