import streamlit as st
import pandas as pd
from db_utils import get_project_data

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
    # Format prices
    if "proc_price" in df.columns:
        df["proc_price"] = df["proc_price"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "")
    if "ind_price" in df.columns:
        df["ind_price"] = df["ind_price"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "")

    # MultiIndex headers
    tuples = [
        ("General", "StockCode"),
        ("General", "Description"),

        ("Procurement", "Current Supplier"),
        ("Procurement", "Price"),
        ("Procurement", "AC Coverage"),
        ("Procurement", "Production LT"),
        ("Procurement", "Next Shortage Date"),

        ("Industrialization", "New Supplier"),
        ("Industrialization", "Price"),
        ("Industrialization", "FAI LT"),
        ("Industrialization", "Production LT"),
        ("Industrialization", "FAI Delivery Date"),
        ("Industrialization", "1st Production PO Delivery Date"),
        ("Industrialization", "Overlap Days"),

        ("Quality", "FAI Status"),
        ("Quality", "FAI Number"),
        ("Quality", "Fitcheck AC"),
        ("Quality", "Fitcheck Date"),
        ("Quality", "Fitcheck Status"),
    ]
    df.columns = pd.MultiIndex.from_tuples(tuples)

    # Display summary table
    st.dataframe(df, width="stretch")

    # Totals
    if "Procurement" in df.columns.get_level_values(0):
        total_old = pd.to_numeric(df[("Procurement", "Price")].str.replace("$", "").str.replace(",", ""), errors="coerce").sum()
    else:
        total_old = 0

    if "Industrialization" in df.columns.get_level_values(0):
        total_new = pd.to_numeric(df[("Industrialization", "Price")].str.replace("$", "").str.replace(",", ""), errors="coerce").sum()
    else:
        total_new = 0

    st.metric("Total Procurement Cost", f"${total_old:,.2f}")
    st.metric("Total Industrialization Cost", f"${total_new:,.2f}")
    st.metric("Estimated Savings", f"${(total_old - total_new):,.2f}")
