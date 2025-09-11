import streamlit as st
import pandas as pd
import io
from datetime import datetime
from db_utils import (
    init_db, add_project, get_projects,
    update_project_name, get_project_data,
    save_project_data, try_float, detect_header_and_read
)

st.set_page_config(page_title="Industrialization Tracker", layout="wide")
st.title("📊 Industrialization Tracker")

init_db()

# ------------------ Sidebar: Create New Project ------------------
st.sidebar.header("➕ Create New Project")
new_project_name = st.sidebar.text_input("Project Name")
uploaded_file = st.sidebar.file_uploader("Upload Excel (template below)", type=["xlsx"])

def make_template_bytes():
    headers = [
        "StockCode", "Description",
        "AC Coverage (Confirmed POs)", "Production LT", "Price",
        "FAI LT", "Production LT", "Price"
    ]
    example = [["ABC123", "Widget", "180", "60", 150, "90", "55", 120]]
    df = pd.DataFrame(example, columns=headers)
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    towrite.seek(0)
    return towrite

st.sidebar.download_button(
    label="Download Template Excel",
    data=make_template_bytes(),
    file_name="ind_tracker_template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

if st.sidebar.button("Add Project"):
    if not new_project_name:
        st.sidebar.error("Enter a project name.")
    elif not uploaded_file:
        st.sidebar.error("Upload an Excel file.")
    else:
        try:
            df_raw = detect_header_and_read(uploaded_file)
            required = [
                "stockcode", "description", "ac_coverage",
                "current_production_lt", "current_price",
                "fai_lt", "new_supplier_production_lt", "new_price"
            ]
            missing = [c for c in required if c not in df_raw.columns]
            if missing:
                st.sidebar.error("Missing columns after mapping: " + ", ".join(missing))
            else:
                for col in ["current_price", "new_price"]:
                    df_raw[col] = pd.to_numeric(df_raw[col].apply(try_float), errors="coerce").fillna(0)

                # Add new columns with defaults
                df_raw["next_shortage_date"] = ""
                df_raw["fai_delivery_date"] = ""
                df_raw["fai_status"] = "Not Submitted"
                df_raw["fitcheck_status"] = "Not Scheduled"
                df_raw["fitcheck_ac"] = ""
                df_raw["first_production_po_delivery_date"] = ""
                df_raw["overlap_days"] = ""

                add_project(new_project_name, df_raw)
                st.sidebar.success(f"Project '{new_project_name}' added.")
        except Exception as e:
            st.sidebar.error(f"Failed to process file: {e}")

# ------------------ Sidebar: Project Index ------------------
st.sidebar.header("📂 Project Index")
projects = get_projects()
if not projects:
    st.sidebar.info("No projects yet.")
else:
    project_map = {name: pid for pid, name in projects}
    selected = st.sidebar.selectbox("Open project", list(project_map.keys()))
    pid = project_map[selected]

    # Supplier names
    current_supplier_name = st.sidebar.text_input("Current Supplier Name", value="Current Supplier")
    new_supplier_name = st.sidebar.text_input("New Supplier Name", value="New Supplier")

    tab1, tab2 = st.tabs(["Final Table", "Edit Table"])

    # ------------------ Tab 1: Final Table ------------------
    with tab1:
        st.header(f"Project: {selected} - Final Table")
        df_final = get_project_data(pid)
        if df_final.empty:
            st.info("No rows found for this project.")
        else:
            df_final = df_final.reset_index(drop=True)

            # Calculate Overlap (Days)
            def calc_overlap(row):
                try:
                    if row["next_shortage_date"] and row["first_production_po_delivery_date"]:
                        d1 = pd.to_datetime(row["next_shortage_date"])
                        d2 = pd.to_datetime(row["first_production_po_delivery_date"])
                        return (d1 - d2).days
                except:
                    return ""
                return ""
            df_final["overlap_days"] = df_final.apply(calc_overlap, axis=1)

            # Rename columns with indices [A], [B], etc.
            column_labels = [
                ("General", "[A] StockCode"),
                ("General", "[B] Description"),
                (current_supplier_name, "[C] AC Coverage (POs)"),
                (current_supplier_name, "[D] Production LT"),
                (current_supplier_name, "[E] Price"),
                (current_supplier_name, "[F] Next Shortage Date"),
                (new_supplier_name, "[G] FAI LT"),
                (new_supplier_name, "[H] Production LT"),
                (new_supplier_name, "[I] Price"),
                (new_supplier_name, "[J] FAI Delivery Date"),
                (new_supplier_name, "[K] FAI Status"),
                (new_supplier_name, "[L] Fitcheck Status"),
                (new_supplier_name, "[M] Fitcheck A/C"),
                (new_supplier_name, "[N] 1st Production PO Delivery Date"),
                (new_supplier_name, "[O] Overlap (Days)")
            ]
            df_display = df_final[
                [
                    "stockcode", "description", "ac_coverage", "current_production_lt", "current_price",
                    "next_shortage_date", "fai_lt", "new_supplier_production_lt", "new_price",
                    "fai_delivery_date", "fai_status", "fitcheck_status", "fitcheck_ac",
                    "first_production_po_delivery_date", "overlap_days"
                ]
            ].copy()
            df_display.columns = pd.MultiIndex.from_tuples(column_labels)

            st.dataframe(df_display, width="stretch")

    # ------------------ Tab 2: Editable Table ------------------
    with tab2:
        st.header(f"Project: {selected} - Editable Table")
        df_edit = get_project_data(pid)
        if df_edit.empty:
            st.info("No rows found for this project.")
        else:
            df_edit = df_edit.reset_index(drop=True)

            # Editable table with dropdowns
            edited = st.data_editor(
                df_edit,
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

            if st.button("Save edits", key="save_edits"):
                save_project_data(pid, edited)
                st.success("Saved changes.")
