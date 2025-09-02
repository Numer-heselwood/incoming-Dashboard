import pandas as pd
import plotly.express as px
import streamlit as st
from io import BytesIO

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
# USERS
# ------------------------
users = {"admin": "password123", "user1": "mypassword"}

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
        if username in users and password == users[username]:
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
    # Centered Dashboard Title
    st.markdown("<h1 style='text-align: center;'>♻ Material Management Dashboard</h1>", unsafe_allow_html=True)
    st.divider()
    
    # Logout button
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

    # Sidebar Filters (without showing username)
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

        # Net Weight by Waste Type
        st.subheader("📦 Net Weight by Waste Type")
        if not filtered_incoming.empty or not filtered_outgoing.empty:
            waste_in = filtered_incoming.groupby("Waste Type ID")["Net Weight (tn)"].sum().reset_index()
            waste_in["Type"] = "Incoming"
            waste_out = filtered_outgoing.groupby("Waste Type ID")["Net Weight (tn)"].sum().reset_index()
            waste_out["Type"] = "Outgoing"
            waste_combined = pd.concat([waste_in, waste_out])
            fig1 = px.bar(
                waste_combined,
                x="Waste Type ID",
                y="Net Weight (tn)",
                color="Type",
                barmode="group",
                color_discrete_map=plotly_colors,
                title="Net Weight by Waste Type"
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("⚠️ No data available for Waste Type breakdown")

        # Pie Charts for Grades
        if "Grade" in filtered_incoming.columns or "Grade" in filtered_outgoing.columns:
            col_in, col_out = st.columns(2)
            with col_in:
                st.subheader("🥧 Incoming Material Grade")
                if not filtered_incoming.empty:
                    pie_data_in = filtered_incoming.groupby("Grade")["Net Weight (tn)"].sum().reset_index()
                    fig_pie_in = px.pie(
                        pie_data_in,
                        names="Grade",
                        values="Net Weight (tn)",
                        color="Grade",
                        color_discrete_map={"Ferrous": "#FF7F0E", "Non-Ferrous": "#1F77B4"},
                        title="Incoming Material Grade Distribution"
                    )
                    st.plotly_chart(fig_pie_in, use_container_width=True)
                else:
                    st.info("⚠️ No Incoming Grade data")
            with col_out:
                st.subheader("🥧 Outgoing Material Grade")
                if not filtered_outgoing.empty:
                    pie_data_out = filtered_outgoing.groupby("Grade")["Net Weight (tn)"].sum().reset_index()
                    fig_pie_out = px.pie(
                        pie_data_out,
                        names="Grade",
                        values="Net Weight (tn)",
                        color="Grade",
                        color_discrete_map={"Ferrous": "#FF7F0E", "Non-Ferrous": "#1F77B4"},
                        title="Outgoing Material Grade Distribution"
                    )
                    st.plotly_chart(fig_pie_out, use_container_width=True)
                else:
                    st.info("⚠️ No Outgoing Grade data")

        # Incoming vs Outgoing Trend
        st.subheader("📊 Incoming vs Outgoing Trend")
        if not filtered_incoming.empty or not filtered_outgoing.empty:
            daily_in = filtered_incoming.groupby("Ticket Date")["Net Weight (tn)"].sum().reset_index()
            daily_in["Type"] = "Incoming"
            daily_out = filtered_outgoing.groupby("Ticket Date")["Net Weight (tn)"].sum().reset_index()
            daily_out["Type"] = "Outgoing"
            trend_df = pd.concat([daily_in, daily_out])
            fig2 = px.line(
                trend_df,
                x="Ticket Date",
                y="Net Weight (tn)",
                color="Type",
                markers=True,
                color_discrete_map=plotly_colors,
                title="Incoming vs Outgoing Trend"
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("⚠️ No trend data")

        # Cost per Tonne Trend
        st.subheader("💰 Cost per Tonne Trend")
        if not filtered_incoming.empty and "Cost" in filtered_incoming.columns:
            daily_cost = filtered_incoming.groupby("Ticket Date")["Cost"].sum().reset_index()
            daily_weight = filtered_incoming.groupby("Ticket Date")["Net Weight (tn)"].sum().reset_index()
            daily_cpt = pd.merge(daily_cost, daily_weight, on="Ticket Date")
            daily_cpt["Cost per Tonne"] = daily_cpt["Cost"] / daily_cpt["Net Weight (tn)"]
            fig3 = px.line(
                daily_cpt,
                x="Ticket Date",
                y="Cost per Tonne",
                markers=True,
                line_shape="spline",
                title="Weighted Cost per Tonne Trend"
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("⚠️ No cost data")

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
