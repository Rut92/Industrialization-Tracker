import streamlit as st
import pandas as pd
import io
from db_utils import (
    init_db, add_project, get_projects,
    update_project_name, get_project_data,
    save_project_data, detect_header_and_read
)

# ------------------ Template Generator ------------------
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
        "60", 150, "",   # Current supplier data
        "90", "55", 120, # New supplier data
        "", "Not Submitted", "Not Scheduled", "", "", ""
    ]]

    df = pd.DataFrame(example, columns=headers)

    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Template")
    towrite.seek(0)
    return towrite


# ------------------ Main App ------------------
st.set_page_config(page_title="📊 Industrialization Tracker", layout="wide")
init_db()

st.title("📊 Industrialization Tracker")

# Sidebar
st.sidebar.header("Project Management")
projects = get_projects()
project_names = [p[1] for p in projects]

selected = st.sidebar.selectbox("Select Project", ["-- New Project --"] + project_names)

if selected == "-- New Project --":
    new_name = st.sidebar.text_input("New Project Name")
    uploaded = st.sidebar.file_uploader("Upload Excel Template", type=["xlsx"])
    st.sidebar.download_button(
        "Download Template Excel",
        data=make_template_bytes(),
        file_name="ind_tracker_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    if uploaded and new_name:
        df = detect_header_and_read(uploaded)
        add_project(new_name, df)
        st.sidebar.success(f"Project '{new_name}' created. Reload the page.")
        st.stop()

else:
    pid = [p[0] for p in projects if p[1] == selected][0]
    tab1, tab2 = st.tabs(["📑 Final Table", "✏️ Edit Data"])

    # -------- Tab 1: Final Table --------
    with tab1:
        st.header(f"Project: {selected} - Final Table")
        df_final = get_project_data(pid)

        if df_final.empty:
            st.info("No rows found for this project.")
        else:
            # Supplier names
            current_supplier = st.session_state.get("current_supplier", "Current Supplier")
            new_supplier = st.session_state.get("new_supplier", "New Supplier")

            # Build display DF
            df_display = pd.DataFrame()
            df_display[("[A] Stockcode")] = df_final["stockcode"]
            df_display[("[B] Description")] = df_final["description"]
            df_display[("[C] AC Coverage")] = df_final["ac_coverage"]
            df_display[("[D] Production LT")] = df_final["current_production_lt"]
            df_display[("[E] Price")] = df_final["current_price"]
            df_display[("[F] Next Shortage Date")] = df_final["next_shortage_date"]
            df_display[("[G] FAI LT")] = df_final["fai_lt"]
            df_display[("[H] Production LT")] = df_final["new_supplier_production_lt"]
            df_display[("[I] Price")] = df_final["new_price"]
            df_display[("[J] FAI Delivery Date")] = df_final["fai_delivery_date"]
            df_display[("[K] FAI Status")] = df_final["fai_status"]
            df_display[("[L] Fitcheck Status")] = df_final["fitcheck_status"]
            df_display[("[M] Fitcheck A/C")] = df_final["fitcheck_ac"]
            df_display[("[N] 1st Production PO Delivery Date")] = df_final["first_production_po_delivery_date"]

            # Overlap calculation
            overlap = []
            for shortage, po_date in zip(df_final["next_shortage_date"], df_final["first_production_po_delivery_date"]):
                try:
                    if shortage and po_date:
                        shortage_dt = pd.to_datetime(shortage)
                        po_dt = pd.to_datetime(po_date)
                        overlap.append((shortage_dt - po_dt).days)
                    else:
                        overlap.append("")
                except Exception:
                    overlap.append("")
            df_display[("[O] Overlap (Days)")] = overlap

            # MultiIndex headers
            cols = [
                ("General", "[A] Stockcode"),
                ("General", "[B] Description"),
                ("General", "[C] AC Coverage"),
                (current_supplier, "[D] Production LT"),
                (current_supplier, "[E] Price"),
                (current_supplier, "[F] Next Shortage Date"),
                (new_supplier, "[G] FAI LT"),
                (new_supplier, "[H] Production LT"),
                (new_supplier, "[I] Price"),
                (new_supplier, "[J] FAI Delivery Date"),
                (new_supplier, "[K] FAI Status"),
                (new_supplier, "[L] Fitcheck Status"),
                (new_supplier, "[M] Fitcheck A/C"),
                (new_supplier, "[N] 1st Production PO Delivery Date"),
                (new_supplier, "[O] Overlap (Days)"),
            ]
            df_display.columns = pd.MultiIndex.from_tuples(cols)

            st.dataframe(df_display, width="stretch")

    # -------- Tab 2: Editable Table --------
    with tab2:
        st.header(f"Project: {selected} - Edit Data")

        # Supplier names
        st.subheader("Supplier Names")
        current_supplier = st.text_input("Current Supplier Name", value=st.session_state.get("current_supplier", "Current Supplier"))
        new_supplier = st.text_input("New Supplier Name", value=st.session_state.get("new_supplier", "New Supplier"))
        st.session_state["current_supplier"] = current_supplier
        st.session_state["new_supplier"] = new_supplier

        st.subheader("Edit Table")

        editable_cols = [
            "next_shortage_date", "fai_delivery_date", "fai_status",
            "fitcheck_status", "fitcheck_ac", "first_production_po_delivery_date"
        ]

        edited = st.data_editor(
            df_final,
            width="stretch",
            hide_index=True,
            column_config={
                "fai_status": st.column_config.SelectboxColumn("FAI Status", options=["Not Submitted", "Under Review", "Failed", "Passed"]),
                "fitcheck_status": st.column_config.SelectboxColumn("Fitcheck Status", options=["Not Scheduled", "Scheduled", "Failed", "Passed"]),
            },
            disabled=[c for c in df_final.columns if c not in editable_cols],
        )

        if st.button("💾 Save Changes"):
            save_project_data(pid, edited)
            st.success("Changes saved. Refresh Tab 1 to see updates.")
