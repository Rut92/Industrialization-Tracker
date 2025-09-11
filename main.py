import streamlit as st
import pandas as pd
import io
from db_utils import (
    init_db, add_project, get_projects,
    update_project_name, get_project_data, save_project_data,
    detect_header_and_read
)

# ------------------ Init ------------------
init_db()

st.set_page_config(page_title="Industrialization Tracker", layout="wide")

# ------------------ Helper: Excel Template ------------------
def make_template_bytes():
    headers = [
        "[A] StockCode", "[B] Description", "[C] AC Coverage",
        "[D] Current Production LT", "[E] Current Price", "[F] Next Shortage Date",
        "[G] FAI LT", "[H] New Supplier Production LT", "[I] New Price",
        "[J] FAI Delivery Date", "[K] FAI Status", "[L] Fitcheck Status",
        "[M] Fitcheck A/C", "[N] 1st Production PO Delivery Date", "[O] Overlap (Days)"
    ]
    example = [[
        "ABC123", "Widget", "180",
        "60", 150, "",
        "90", "55", 120,
        "", "Not Submitted", "Not Scheduled", "", "", ""
    ]]
    df = pd.DataFrame(example, columns=headers)

    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Template")
    towrite.seek(0)
    return towrite

# ------------------ Sidebar ------------------
with st.sidebar:
    st.header("📂 Project Management")

    # Create new project
    new_name = st.text_input("New Project Name")
    uploaded_file = st.file_uploader("Upload Initial Excel", type=["xlsx"])
    if st.button("Create Project") and new_name and uploaded_file:
        df = detect_header_and_read(uploaded_file)
        add_project(new_name, df)
        st.success(f"Project '{new_name}' created!")

    # Download template
    st.download_button(
        label="📥 Download Template Excel",
        data=make_template_bytes(),
        file_name="industrialization_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Select project
    projects = get_projects()
    pid = None
    selected = None
    if projects:
        project_options = {name: pid for pid, name in projects}
        selected = st.selectbox("Select Project", list(project_options.keys()))
        pid = project_options[selected]

# ------------------ Main Tabs ------------------
if pid:
    tab1, tab2 = st.tabs(["📊 Final Table", "✏️ Edit Data"])

    # ---- Tab 1: Final Table ----
    with tab1:
        st.header(f"Project: {selected} - Final Table")
        df_final = get_project_data(pid)
        if df_final.empty:
            st.info("No rows found for this project.")
        else:
            # Rename columns with alphabet prefixes
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

            st.dataframe(df_display, use_container_width=True)

    # ---- Tab 2: Edit Data ----
    with tab2:
        st.header(f"Project: {selected} - Edit Data")

        # Supplier names
        col1, col2 = st.columns(2)
        with col1:
            current_supplier = st.text_input("Current Supplier Name", value="Current Supplier")
        with col2:
            new_supplier = st.text_input("New Supplier Name", value="New Supplier")

        df_edit = get_project_data(pid)

        # Editable dataframe
        edited = st.data_editor(
            df_edit,
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
            },
            num_rows="dynamic",
            use_container_width=True
        )

        # Calculate Overlap (Days)
        if "next_shortage_date" in edited and "first_production_po_delivery_date" in edited:
            try:
                edited["overlap_days"] = pd.to_datetime(
                    edited["next_shortage_date"], errors="coerce"
                ) - pd.to_datetime(
                    edited["first_production_po_delivery_date"], errors="coerce"
                )
                edited["overlap_days"] = edited["overlap_days"].dt.days
            except Exception:
                edited["overlap_days"] = ""

        if st.button("💾 Save Changes"):
            save_project_data(pid, edited)
            st.success("Project data saved successfully!")
