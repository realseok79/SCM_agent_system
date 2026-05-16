import streamlit as st
import pandas as pd
import json

st.title("SCM Agent System Dashboard")

st.sidebar.header("Settings")
if st.sidebar.button("Run Pipeline"):
    st.write("Running pipeline...")

st.subheader("Order List")
try:
    with open("outputs/order_list.json", "r") as f:
        data = json.load(f)
        st.write(data)
except FileNotFoundError:
    st.write("No orders found yet.")
