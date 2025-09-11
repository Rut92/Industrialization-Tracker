import streamlit as st
import pandas as pd
from db_utils import get_project_data

st.set_page_config(page_title="📋 Project Data", layout="wide")
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
    # Grouped headers
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

    st.dataframe(df, use_container_width=True)

    # Totals
    total_old = pd.to_numeric(df[("Procurement", "Price")], errors="coerce").sum()
    total_new = pd.to_numeric(df[("Industrialization", "Price")], errors="coerce").sum()
    st.metric("Total Procurement Cost", f"${total_old:,.2f}")
    st.metric("Total Industrialization Cost", f"${total_new:,.2f}")
    st.metric("Estimated Savings", f"${(total_old - total_new):,.2f}")
