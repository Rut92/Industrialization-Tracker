import streamlit as st
import pandas as pd
from db_utils import get_project_data, save_project_data, try_float

st.set_page_config(page_title="Project Data", layout="wide")
st.title("📋 Project Data Table")

query_params = st.experimental_get_query_params()
if "project_id" not in query_params:
    st.error("No project selected. Go back to the main page.")
    st.stop()

project_id = int(query_params["project_id"][0])
df = get_project_data(project_id)

if df.empty:
    st.info("No rows found for this project.")
else:
    display_df = df.copy()
    display_df["current_price"] = display_df["current_price"].apply(lambda x: f"${x:,.2f}")
    display_df["new_price"] = display_df["new_price"].apply(lambda x: f"${x:,.2f}")

    tuples = [
        ("General", "StockCode"),
        ("General", "Description"),
        ("Current Supplier", "AC Coverage (POs)"),
        ("Current Supplier", "Production LT"),
        ("Current Supplier", "Price"),
        ("New Supplier", "FAI LT"),
        ("New Supplier", "Production LT"),
        ("New Supplier", "Price"),
    ]
    display_df.columns = pd.MultiIndex.from_tuples(tuples)
    st.dataframe(display_df, width="stretch")

    st.subheader("Edit Table Values")
    edited = st.data_editor(df, num_rows="dynamic")

    if st.button("Save edits"):
        save_project_data(project_id, edited)
        st.success("Saved changes.")

    total_old = edited["current_price"].sum()
    total_new = edited["new_price"].sum()
    st.metric("Total Current Supplier Cost", f"${total_old:,.2f}")
    st.metric("Total New Supplier Cost", f"${total_new:,.2f}")
    st.metric("Estimated Savings", f"${(total_old - total_new):,.2f}")
