import streamlit as st
import pandas as pd
from io import BytesIO
import db_utils

st.set_page_config(page_title="📊 Industrialization Tracker", layout="wide")
db_utils.init_db()

st.title("📊 Industrialization Tracker")

# ---------- Project creation ----------
with st.expander("➕ Create New Project"):
    templates = {
        "Procurement": ["StockCode", "Description", "Current_Supplier", "AC_Coverage", "Next_Shortage_Date"],
        "Industrialization": ["StockCode", "Description", "New_Supplier", "FAI_Delivery_Date", "First_PO_Delivery_Date"],
        "Quality": ["StockCode", "Description", "FAI_Status", "FAI_Number", "Fitcheck_AC", "Fitcheck_Date", "Fitcheck_Status"],
    }
    for name, cols in templates.items():
        buf = BytesIO()
        pd.DataFrame(columns=cols).to_excel(buf, index=False)
        st.download_button(f"📥 Download {name} Template", buf.getvalue(), file_name=f"{name.lower()}_template.xlsx")

    new_project_name = st.text_input("Project Name")
    uploaded_file = st.file_uploader("Upload Stock Codes & Descriptions", type=["xlsx"])

    if st.button("Create Project"):
        if new_project_name.strip():
            stockcodes_df = None
            if uploaded_file:
                stockcodes_df = pd.read_excel(uploaded_file)
            db_utils.add_project(new_project_name.strip(), stockcodes_df)
            st.success(f"Project '{new_project_name}' created.")
        else:
            st.error("Enter a project name.")

# ---------- Select project ----------
projects = db_utils.get_projects()
if projects.empty:
    st.info("No projects yet.")
    st.stop()

project_map = {name: pid for pid, name in projects.values}
selected_name = st.selectbox("Select Project", list(project_map.keys()))
pid = project_map[selected_name]

tab1, tab2, tab3, tab4 = st.tabs(["📌 Summary", "📦 Procurement", "🏭 Industrialization", "✅ Quality"])

# ---------- Summary ----------
with tab1:
    st.subheader("📌 Project Summary")
    if st.button("🔄 Refresh Summary"):
        st.session_state["refresh_summary"] = True

    if "refresh_summary" not in st.session_state or st.session_state["refresh_summary"]:
        df_sum = db_utils.get_project_data(pid)
        st.session_state["refresh_summary"] = False
    else:
        df_sum = db_utils.get_project_data(pid)

    if df_sum.empty:
        st.info("No data yet.")
    else:
        tuples = [
            ("General", "[A] StockCode"),
            ("General", "[B] Description"),
            ("Procurement", "[C] Current Supplier"),
            ("Procurement", "[D] AC Coverage"),
            ("Procurement", "[E] Next Shortage Date"),
            ("Industrialization", "[F] New Supplier"),
            ("Industrialization", "[G] FAI Delivery Date"),
            ("Industrialization", "[H] 1st Production PO Delivery Date"),
            ("Industrialization", "[I] Overlap (Days)"),
            ("Quality", "[J] FAI Status"),
            ("Quality", "[K] FAI Number"),
            ("Quality", "[L] Fitcheck AC"),
            ("Quality", "[M] Fitcheck Date"),
            ("Quality", "[N] Fitcheck Status"),
        ]
        df_display = df_sum.copy()
        df_display.columns = pd.MultiIndex.from_tuples(tuples)
        st.dataframe(df_display, width="stretch")

# ---------- Procurement ----------
with tab2:
    st.subheader("📦 Procurement")
    f = st.file_uploader("Upload Procurement Data", type=["xlsx"], key="proc")
    if f:
        df_upload = pd.read_excel(f)
        db_utils.save_table(df_upload, pid, "procurement")
        st.success("Procurement uploaded.")

    base = db_utils.get_project_data(pid)
    df_proc = base[["stockcode", "description", "current_supplier", "ac_coverage", "next_shortage_date"]] \
        .rename(columns={
            "stockcode": "StockCode",
            "description": "Description",
            "current_supplier": "Current_Supplier",
            "ac_coverage": "AC_Coverage",
            "next_shortage_date": "Next_Shortage_Date",
        })

    edited = st.data_editor(df_proc, num_rows="dynamic", width="stretch")
    if st.button("Save Procurement Changes"):
        db_utils.save_table(edited, pid, "procurement")
        st.success("Procurement changes saved.")
    if st.button("↩️ Undo Procurement Save"):
        db_utils.undo_last_save(pid, "procurement")
        st.warning("Procurement reverted to last save.")

# ---------- Industrialization ----------
with tab3:
    st.subheader("🏭 Industrialization")
    f = st.file_uploader("Upload Industrialization Data", type=["xlsx"], key="ind")
    if f:
        df_upload = pd.read_excel(f)
        db_utils.save_table(df_upload, pid, "industrialization")
        st.success("Industrialization uploaded.")

    base = db_utils.get_project_data(pid)
    df_ind = base[["stockcode", "description", "new_supplier", "fai_delivery_date", "first_po_delivery_date"]] \
        .rename(columns={
            "stockcode": "StockCode",
            "description": "Description",
            "new_supplier": "New_Supplier",
            "fai_delivery_date": "FAI_Delivery_Date",
            "first_po_delivery_date": "First_PO_Delivery_Date",
        })

    edited = st.data_editor(df_ind, num_rows="dynamic", width="stretch")
    if st.button("Save Industrialization Changes"):
        db_utils.save_table(edited, pid, "industrialization")
        st.success("Industrialization changes saved.")
    if st.button("↩️ Undo Industrialization Save"):
        db_utils.undo_last_save(pid, "industrialization")
        st.warning("Industrialization reverted to last save.")

# ---------- Quality ----------
with tab4:
    st.subheader("✅ Quality")
    f = st.file_uploader("Upload Quality Data", type=["xlsx"], key="qual")
    if f:
        df_upload = pd.read_excel(f)
        db_utils.save_table(df_upload, pid, "quality")
        st.success("Quality uploaded.")

    base = db_utils.get_project_data(pid)
    df_qual = base[["stockcode", "description", "fai_status", "fai_number", "fitcheck_ac", "fitcheck_date", "fitcheck_status"]] \
        .rename(columns={
            "stockcode": "StockCode",
            "description": "Description",
            "fai_status": "FAI_Status",
            "fai_number": "FAI_Number",
            "fitcheck_ac": "Fitcheck_AC",
            "fitcheck_date": "Fitcheck_Date",
            "fitcheck_status": "Fitcheck_Status",
        })

    edited = st.data_editor(
        df_qual,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "FAI_Status": st.column_config.SelectboxColumn(
                "FAI Status",
                options=["Not Submitted", "Under Review", "Rejected", "Approved"],
                default="Not Submitted",
            ),
            "Fitcheck_Status": st.column_config.SelectboxColumn(
                "Fitcheck Status",
                options=["", "Scheduled", "Approved", "Rejected"],
                default="",
            ),
            "Fitcheck_Date": st.column_config.DateColumn("Fitcheck Date"),
        }
    )
    if st.button("Save Quality Changes"):
        db_utils.save_table(edited, pid, "quality")
        st.success("Quality changes saved.")
    if st.button("↩️ Undo Quality Save"):
        db_utils.undo_last_save(pid, "quality")
        st.warning("Quality reverted to last save.")
