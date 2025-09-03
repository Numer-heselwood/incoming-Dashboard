import pandas as pd
import plotly.express as px
import streamlit as st
from io import BytesIO
import bcrypt
import os

# ------------------------
# PAGE CONFIG
# ------------------------
st.set_page_config(page_title="♻ Material Management Dashboard", layout="wide")

# ------------------------
# SESSION STATE SETUP
# ------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "login_error" not in st.session_state:
    st.session_state.login_error = False

# ------------------------
# USERS (bcrypt hashed passwords)
# ------------------------
# Generate hashes once using:
# bcrypt.hashpw("password".encode(), bcrypt.gensalt()).decode()
# and paste the result into this dict (or load from environment variables)

users = {
    "admin": b"$2b$12$k7KlV0r3y9oD2K6A7xEYWuDJyzU6kE7QxDnNEupfS.X2aBFF2UGEC",  # WHL@2025
    "god": b"$2b$12$h2BaYifT0czBz1hlM8q25OPR1l7uQb0tqAhvH/jc5LDE2o5MQl6d6",   # numer
}

def check_password(username, password):
    """Verify username and password using bcrypt."""
    if username in users:
        stored_hash = users[username]
        return bcrypt.checkpw(password.encode(), stored_hash)
    return False

# ------------------------
# LOGOUT FUNCTION
# ------------------------
def do_logout():
    st.session_state.update({
        "logged_in": False,
        "username": "",
        "input_username": "",
        "input_password": ""
    })

# ------------------------
# LOGIN SCREEN
# ------------------------
def login_screen():
    st.title("🔐 Material Management Dashboard Login")
    
    username = st.text_input("Username", key="input_username")
    password = st.text_input("Password", type="password", key="input_password")
    
    if st.button("Login"):
        if check_password(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.login_error = False
        else:
            st.session_state.login_error = True

    if st.session_state.login_error:
        st.error("❌ Invalid username or password")

# ------------------------
# DASHBOARD SCREEN
# ------------------------
def dashboard():
    st.markdown("<h1 style='text-align: center;'>♻ Material Management Dashboard</h1>", unsafe_allow_html=True)
    st.divider()
    st.sidebar.button("🔓 Logout", on_click=do_logout)

    # Load Excel Data
    excel_file_path = "Material incoming dashboard.xlsx"
    incoming_df = pd.read_excel(excel_file_path, sheet_name="INCOMING MASTER")
    outgoing_df = pd.read_excel(excel_file_path, sheet_name="OUTGOING MASTER")
    
    incoming_df.columns = incoming_df.columns.str.strip()
    outgoing_df.columns = outgoing_df.columns.str.strip()
    
    incoming_df["Ticket Date"] = pd.to_datetime(incoming_df["Ticket Date"])
    outgoing_df["Ticket Date"] = pd.to_datetime(outgoing_df["Ticket Date"])
    
    incoming_df["Cost per Tonne"] = incoming_df.apply(
        lambda row: row["Cost"] / row["Net Weight (tn)"] if row["Net Weight (tn)"] > 0 else 0,
        axis=1
    )

    # Sidebar Filters
    st.sidebar.header("🔎 Dashboard Filters")
    
    with st.sidebar.expander("📅 Date Filters", expanded=True):
        date_range = st.date_input(
            "Select Date Range",
            value=[incoming_df["Ticket Date"].min().date(), incoming_df["Ticket Date"].max().date()],
            min_value=incoming_df["Ticket Date"].min().date(),
            max_value=incoming_df["Ticket Date"].max().date()
        )
    
    with st.sidebar.expander("👤 Customer & Waste Type", expanded=True):
        customer = st.selectbox("Select Customer", options=["All"] + list(incoming_df["Customer Name"].unique()))
        waste_type_options = incoming_df["Waste Type ID"].astype(str).str.strip().unique()
        waste_type = st.multiselect("Select Waste Type", options=["All"] + list(waste_type_options), default=["All"])
        if "All" in waste_type:
            waste_type = waste_type_options

    # Filter Data
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    
    filtered_incoming = incoming_df[
        (incoming_df["Ticket Date"].between(start_date, end_date)) &
        (incoming_df["Waste Type ID"].astype(str).str.strip().isin(waste_type))
    ]
    
    filtered_outgoing = outgoing_df[
        (outgoing_df["Ticket Date"].between(start_date, end_date)) &
        (outgoing_df["Waste Type ID"].astype(str).str.strip().isin(waste_type))
    ]
    
    if customer != "All":
        filtered_incoming = filtered_incoming[filtered_incoming["Customer Name"] == customer]
        filtered_outgoing = filtered_outgoing[filtered_outgoing["Customer Name"] == customer]

    # KPIs
    incoming_total = filtered_incoming["Net Weight (tn)"].sum()
    outgoing_total = filtered_outgoing["Net Weight (tn)"].sum()
    total_cost = filtered_incoming["Cost"].sum() if "Cost" in filtered_incoming.columns else 0
    avg_cost_tn = total_cost / incoming_total if incoming_total > 0 else 0
    plotly_colors = {"Incoming": "#2ca02c", "Outgoing": "#1f77b4"}

    # Tabs
    tab_main, tab_data, tab_download = st.tabs(["📊 Overview", "📋 Data Tables", "⬇ Download Report"])

    # ---- MAIN TAB ----
    with tab_main:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("⬅️ Incoming (tn)", f"{incoming_total:,.2f}")
        col2.metric("➡️ Outgoing (tn)", f"{outgoing_total:,.2f}")
        col3.metric("💰 Total Cost (£)", f"{total_cost:,.2f}")
        col4.metric("📊 Cost per Tonne (£)", f"{avg_cost_tn:,.2f}")
        st.divider()

        # (Charts remain unchanged...)
        # ...

    # ---- DATA TABLES TAB ----
    with tab_data:
        tab1, tab2 = st.tabs(["📥 Incoming", "📤 Outgoing"])
        with tab1:
            st.dataframe(filtered_incoming, use_container_width=True)
        with tab2:
            st.dataframe(filtered_outgoing, use_container_width=True)

    # ---- DOWNLOAD TAB ----
    with tab_download:
        st.subheader("⬇ Download Filtered Report")
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            filtered_incoming.to_excel(writer, index=False, sheet_name="Incoming")
            filtered_outgoing.to_excel(writer, index=False, sheet_name="Outgoing")
        st.download_button(
            label="📥 Download Excel Report",
            data=output.getvalue(),
            file_name=f"Waste_Report_{start_date.date()}_{end_date.date()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.divider()
    st.markdown(
        "<div style='text-align:center; padding: 10px; color: gray; font-size: 0.9em;'>"
        "♻ Material Management Dashboard | Built without breaking the monitor 😆"
        "</div>",
        unsafe_allow_html=True
    )

# ------------------------
# APP LOGIC
# ------------------------
if not st.session_state.logged_in:
    login_screen()
else:
    dashboard()
