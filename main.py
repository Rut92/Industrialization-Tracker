import streamlit as st
import pandas as pd
import io
from db_utils import init_db, add_project, get_projects, update_project_name, try_float, detect_header_and_read

st.set_page_config(page_title="Industrialization Tracker", layout="wide")
st.title("📊 Industrialization Tracker")

init_db()

# ---------------- Sidebar: Add Project ----------------
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
            # Flexible header detection
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
                # Clean numeric columns
                for col in ["current_price", "new_price"]:
                    df_raw[col] = pd.to_numeric(df_raw[col].apply(try_float), errors="coerce").fillna(0)
                add_project(new_project_name, df_raw)
                st.sidebar.success(f"Project '{new_project_name}' added.")
        except Exception as e:
            st.sidebar.error(f"Failed to process file: {e}")

# ---------------- Sidebar: Project Index ----------------
st.sidebar.header("📂 Project Index")
projects = get_projects()
if not projects:
    st.sidebar.info("No projects yet.")
else:
    project_map = {name: pid for pid, name in projects}
    selected = st.sidebar.selectbox("Open project", list(project_map.keys()))
    pid = project_map[selected]

    st.header(f"Project: {selected}")

    new_name = st.text_input("Rename project", value=selected)
    if st.button("Update name"):
        update_project_name(pid, new_name)
        st.success("Name updated. Refresh to see updated index.")

    st.markdown(f"""
    Go to [Project Data Page](./project_data?project_id={pid}) to view/edit the data table.
    """)
