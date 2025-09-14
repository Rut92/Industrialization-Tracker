import os
import streamlit as st
import pandas as pd
from io import BytesIO
import db_utils
import bcrypt

# Optional: reduce watcher noise in some environments
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"

st.set_page_config(page_title="📊 Industrialization Tracker", layout="wide")
db_utils.init_db()

st.title("📊 Industrialization Tracker")

# ---------------- Authentication ----------------
if "user" not in st.session_state:
    st.session_state["user"] = None
if "role" not in st.session_state:
    st.session_state["role"] = None

with st.sidebar.expander("🔑 Login"):
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login", key="login_btn"):
        creds = db_utils.get_user_credentials(email)
        if creds:
            role, stored_hash = creds
            if bcrypt.checkpw(password.encode(), stored_hash.encode()):
                st.session_state["user"] = email
                st.session_state["role"] = role
                st.success(f"Logged in as {role.title()}")
            else:
                st.error("Invalid email or password")
        else:
            st.error("Invalid email or password")

if not st.session_state["user"]:
    st.warning("Please log in to use the app.")
    st.stop()

# Sidebar: Logout + admin reload users
if st.sidebar.button("🚪 Logout"):
    st.session_state["user"] = None
    st.session_state["role"] = None
    st.rerun()

if st.session_state["role"] == "admin":
    if st.sidebar.button("🔄 Reload Users from Excel"):
        db_utils.reload_users_from_excel()
        st.success("User list reloaded from Excel")

role = st.session_state["role"]
current_user = st.session_state["user"]

# ---------------- Helper: Filter ----------------
def filter_box(df: pd.DataFrame, label: str, key: str):
    term = st.text_input(label, key=key, placeholder="Type to filter…")
    if term:
        mask = df.apply(lambda r: r.astype(str).str.contains(term, case=False, na=False).any(), axis=1)
        return df[mask]
    return df

# ---------------- Project creation (Admin-only) ----------------
if role == "admin":
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

# ---------------- Select project ----------------
projects = db_utils.get_projects()
if projects.empty:
    st.info("No projects yet." if role == "admin" else "No projects yet. Ask an Admin to create one.")
    st.stop()

project_map = {name: pid for pid, name in projects.values}
selected_name = st.selectbox("Select Project", list(project_map.keys()))
pid = project_map[selected_name]

# ---------------- Tabs (plus Admin tab) ----------------
tabs = ["📌 Summary", "📦 Procurement", "🏭 Industrialization", "✅ Quality"]
if role == "admin":
    tabs.append("🛠 Admin")
tab1, tab2, tab3, tab4, *rest = st.tabs(tabs)
tab_admin = rest[0] if rest else None

# ---------------- Summary ----------------
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

        # Filter box for summary
        flat_for_filter = df_display.copy()
        flat_for_filter.columns = [f"{a} {b}" for a, b in df_display.columns]
        flat_for_filter = filter_box(flat_for_filter, "🔎 Filter Summary", key="filter_summary")
        # Map back to MultiIndex for display
        if len(flat_for_filter) != len(df_display):
            # rebuild multiindex
            multi_cols = pd.MultiIndex.from_tuples(tuples)
            df_display = pd.DataFrame(flat_for_filter.values, columns=multi_cols, index=flat_for_filter.index)

        st.dataframe(df_display, width="stretch")

# ---------------- Procurement ----------------
with tab2:
    st.subheader("📦 Procurement")
    # Upload (everyone sees; only saved if role permitted)
    f = st.file_uploader("Upload Procurement Data", type=["xlsx"], key="proc")
    if f and role in ["admin", "procurement"]:
        df_upload = pd.read_excel(f)
        db_utils.save_table(df_upload, pid, "procurement", changed_by=current_user)
        st.success("Procurement uploaded.")
    elif f and role not in ["admin", "procurement"]:
        st.info("You can view but cannot save changes (insufficient permissions).")

    # Table for editing/viewing
    base = db_utils.get_project_data(pid)
    df_proc = base[["stockcode", "description", "current_supplier", "ac_coverage", "next_shortage_date"]] \
        .rename(columns={
            "stockcode": "StockCode",
            "description": "Description",
            "current_supplier": "Current_Supplier",
            "ac_coverage": "AC_Coverage",
            "next_shortage_date": "Next_Shortage_Date",
        })

    df_proc = filter_box(df_proc, "🔎 Filter Procurement", key="filter_proc")

    if role in ["admin", "procurement"]:
        edited = st.data_editor(df_proc, num_rows="dynamic", width="stretch")
        if st.button("Save Procurement Changes"):
            db_utils.save_table(edited, pid, "procurement", changed_by=current_user)
            st.success("Procurement changes saved.")
        if st.button("↩️ Undo Procurement Save"):
            db_utils.undo_last_save(pid, "procurement")
            st.warning("Procurement reverted to last save.")
    else:
        st.dataframe(df_proc, width="stretch")

    # Attachments (per stockcode)
    st.markdown("**Attachments**")
    stock_for_attach = st.selectbox("Choose StockCode for attachment", df_proc["StockCode"].dropna().unique() if not df_proc.empty else [])
    attach = st.file_uploader("Upload attachment (PDF/Excel/Image/etc.)", key="attach_proc")
    if attach and stock_for_attach and role in ["admin", "procurement"]:
        db_utils.save_attachment(pid, stock_for_attach, attach.name, attach.read(), current_user)
        st.success("Attachment uploaded.")
    if stock_for_attach:
        att_df = db_utils.get_attachments(pid, stock_for_attach)
        if att_df.empty:
            st.caption("No attachments yet for this item.")
        else:
            for _, r in att_df.iterrows():
                fname = r["file_name"]; aid = int(r["id"])
                # fetch blob when clicked (inline for simplicity)
                if st.button(f"📎 Download: {fname}", key=f"dlp_{aid}"):
                    name, blob = db_utils.get_attachment_blob(aid)
                    if blob:
                        st.download_button("Click to download", data=blob, file_name=name, key=f"dlpb_{aid}")

# ---------------- Industrialization ----------------
with tab3:
    st.subheader("🏭 Industrialization")
    f = st.file_uploader("Upload Industrialization Data", type=["xlsx"], key="ind")
    if f and role in ["admin", "industrialization"]:
        df_upload = pd.read_excel(f)
        db_utils.save_table(df_upload, pid, "industrialization", changed_by=current_user)
        st.success("Industrialization uploaded.")
    elif f and role not in ["admin", "industrialization"]:
        st.info("You can view but cannot save changes (insufficient permissions).")

    base = db_utils.get_project_data(pid)
    df_ind = base[["stockcode", "description", "new_supplier", "fai_delivery_date", "first_po_delivery_date"]] \
        .rename(columns={
            "stockcode": "StockCode",
            "description": "Description",
            "new_supplier": "New_Supplier",
            "fai_delivery_date": "FAI_Delivery_Date",
            "first_po_delivery_date": "First_PO_Delivery_Date",
        })

    df_ind = filter_box(df_ind, "🔎 Filter Industrialization", key="filter_ind")

    if role in ["admin", "industrialization"]:
        edited = st.data_editor(df_ind, num_rows="dynamic", width="stretch")
        if st.button("Save Industrialization Changes"):
            db_utils.save_table(edited, pid, "industrialization", changed_by=current_user)
            st.success("Industrialization changes saved.")
        if st.button("↩️ Undo Industrialization Save"):
            db_utils.undo_last_save(pid, "industrialization")
            st.warning("Industrialization reverted to last save.")
    else:
        st.dataframe(df_ind, width="stretch")

    # Attachments
    st.markdown("**Attachments**")
    stock_for_attach = st.selectbox("Choose StockCode for attachment", df_ind["StockCode"].dropna().unique() if not df_ind.empty else [], key="ind_att_sel")
    attach = st.file_uploader("Upload attachment (PDF/Excel/Image/etc.)", key="attach_ind")
    if attach and stock_for_attach and role in ["admin", "industrialization"]:
        db_utils.save_attachment(pid, stock_for_attach, attach.name, attach.read(), current_user)
        st.success("Attachment uploaded.")
    if stock_for_attach:
        att_df = db_utils.get_attachments(pid, stock_for_attach)
        if att_df.empty:
            st.caption("No attachments yet for this item.")
        else:
            for _, r in att_df.iterrows():
                fname = r["file_name"]; aid = int(r["id"])
                if st.button(f"📎 Download: {fname}", key=f"dli_{aid}"):
                    name, blob = db_utils.get_attachment_blob(aid)
                    if blob:
                        st.download_button("Click to download", data=blob, file_name=name, key=f"dlib_{aid}")

# ---------------- Quality ----------------
with tab4:
    st.subheader("✅ Quality")
    f = st.file_uploader("Upload Quality Data", type=["xlsx"], key="qual")
    if f and role in ["admin", "quality"]:
        df_upload = pd.read_excel(f)
        db_utils.save_table(df_upload, pid, "quality", changed_by=current_user)
        st.success("Quality uploaded.")
    elif f and role not in ["admin", "quality"]:
        st.info("You can view but cannot save changes (insufficient permissions).")

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

    df_qual = filter_box(df_qual, "🔎 Filter Quality", key="filter_qual")

    if role in ["admin", "quality"]:
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
            db_utils.save_table(edited, pid, "quality", changed_by=current_user)
            st.success("Quality changes saved.")
        if st.button("↩️ Undo Quality Save"):
            db_utils.undo_last_save(pid, "quality")
            st.warning("Quality reverted to last save.")
    else:
        st.dataframe(df_qual, width="stretch")

    # Attachments
    st.markdown("**Attachments**")
    stock_for_attach = st.selectbox("Choose StockCode for attachment", df_qual["StockCode"].dropna().unique() if not df_qual.empty else [], key="qual_att_sel")
    attach = st.file_uploader("Upload attachment (PDF/Excel/Image/etc.)", key="attach_qual")
    if attach and stock_for_attach and role in ["admin", "quality"]:
        db_utils.save_attachment(pid, stock_for_attach, attach.name, attach.read(), current_user)
        st.success("Attachment uploaded.")
    if stock_for_attach:
        att_df = db_utils.get_attachments(pid, stock_for_attach)
        if att_df.empty:
            st.caption("No attachments yet for this item.")
        else:
            for _, r in att_df.iterrows():
                fname = r["file_name"]; aid = int(r["id"])
                if st.button(f"📎 Download: {fname}", key=f"dlq_{aid}"):
                    name, blob = db_utils.get_attachment_blob(aid)
                    if blob:
                        st.download_button("Click to download", data=blob, file_name=name, key=f"dlqb_{aid}")

# ---------------- Admin tab (user management) ----------------
if tab_admin is not None:
    with tab_admin:
        st.subheader("🛠 Admin — User Management")

        st.markdown("**Upload users.xlsx** (columns: Email, Role, Password)")
        fusers = st.file_uploader("Upload users.xlsx", type=["xlsx"], key="users_up")
        if fusers:
            try:
                df_users = pd.read_excel(fusers)
                db_utils.load_users_from_excel(df_users)
                st.success("Users loaded.")
            except Exception as e:
                st.error(f"Failed to load users: {e}")

        st.markdown("**Current Users**")
        users_df = db_utils.list_users()
        st.dataframe(users_df, width="stretch")

        st.markdown("**Reset a user's password**")
        colu1, colu2 = st.columns([2, 1])
        with colu1:
            sel_email = st.selectbox("Select user", users_df["email"].tolist() if not users_df.empty else [])
            new_pw = st.text_input("New Password", type="password")
        with colu2:
            if st.button("Reset Password"):
                if sel_email and new_pw:
                    db_utils.set_user_password(sel_email, new_pw)
                    st.success("Password reset.")
                else:
                    st.error("Select a user and enter a new password.")
