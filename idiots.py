import streamlit as st

# ==================================================
# MUST BE FIRST STREAMLIT COMMAND
# ==================================================
st.set_page_config(
    page_title="♻ Material Management Dashboard",
    layout="wide"
)

# ==================================================
# IMPORTS
# ==================================================
import pandas as pd
import plotly.express as px
from io import BytesIO
import hashlib

# ==================================================
# LOGIN (SAFE – NO BCRYPT)
# ==================================================
def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

USERS = {
    "admin": hash_pw("admin123"),
    "god": hash_pw("god123")
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login_screen():
    st.title("🔐 Material Management Dashboard Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):
        if username in USERS and USERS[username] == hash_pw(password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.experimental_rerun()
        else:
            st.error("❌ Invalid username or password")

def logout():
    st.session_state.logged_in = False
    st.experimental_rerun()

# ==================================================
# DASHBOARD
# ==================================================
def dashboard():

    st.sidebar.button("🔓 Logout", on_click=logout)

    st.markdown(
        "<h1 style='text-align:center;'>♻ Material Management Dashboard</h1>",
        unsafe_allow_html=True
    )
    st.divider()

    # --------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------
    FILE_PATH = "Material incoming dashboard.xlsx"

    try:
        incoming = pd.read_excel(FILE_PATH, sheet_name="INCOMING MASTER")
        outgoing = pd.read_excel(FILE_PATH, sheet_name="OUTGOING MASTER")
    except Exception as e:
        st.error(f"❌ Failed to load Excel file: {e}")
        st.stop()

    incoming.columns = incoming.columns.str.strip()
    outgoing.columns = outgoing.columns.str.strip()

    incoming["Ticket Date"] = pd.to_datetime(incoming["Ticket Date"], errors="coerce")
    outgoing["Ticket Date"] = pd.to_datetime(outgoing["Ticket Date"], errors="coerce")

    incoming = incoming.dropna(subset=["Ticket Date"])
    outgoing = outgoing.dropna(subset=["Ticket Date"])

    # --------------------------------------------------
    # FILTERS
    # --------------------------------------------------
    with st.sidebar:
        st.header("🔎 Dashboard Filters")

        min_date = incoming["Ticket Date"].min().date()
        max_date = incoming["Ticket Date"].max().date()

        date_range = st.date_input(
            "Date Range",
            value=(min_date, max_date)
        )

        customer = st.selectbox(
            "Customer",
            ["All"] + sorted(incoming["Customer Name"].dropna().unique())
        )

        # 🔥 Waste Type with "All"
        waste_type_options = (
            incoming["Waste Type ID"]
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )

        waste_type = st.multiselect(
            "Waste Type",
            options=["All"] + sorted(waste_type_options),
            default=["All"]
        )

        # If "All" selected → use all waste types
        if "All" in waste_type:
            waste_type = waste_type_options

        price_filter = st.radio(
            "Price Filter",
            ["All", "Priced", "Not Priced"]
        )

    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])

    # --------------------------------------------------
    # APPLY FILTERS
    # --------------------------------------------------
    fi = incoming[
        (incoming["Ticket Date"].between(start_date, end_date)) &
        (incoming["Waste Type ID"].astype(str).str.strip().isin(waste_type))
    ]

    fo = outgoing[
        (outgoing["Ticket Date"].between(start_date, end_date)) &
        (outgoing["Waste Type ID"].astype(str).str.strip().isin(waste_type))
    ]

    if customer != "All":
        fi = fi[fi["Customer Name"] == customer]
        fo = fo[fo["Customer Name"] == customer]

    if price_filter == "Priced":
        fi = fi[fi["Cost"] > 0]
    elif price_filter == "Not Priced":
        fi = fi[(fi["Cost"].isna()) | (fi["Cost"] == 0)]

    # --------------------------------------------------
    # KPI CALCULATIONS
    # --------------------------------------------------
    incoming_tn = fi["Net Weight (tn)"].sum()
    outgoing_tn = fo["Net Weight (tn)"].sum()
    total_cost = fi["Cost"].sum()

    weighted_avg = total_cost / incoming_tn if incoming_tn > 0 else 0

    # --------------------------------------------------
    # KPI DISPLAY
    # --------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("⬅️ Incoming (tn)", f"{incoming_tn:,.2f}")
    c2.metric("➡️ Outgoing (tn)", f"{outgoing_tn:,.2f}")
    c3.metric("💰 Total Cost (£)", f"{total_cost:,.2f}")
    c4.metric("⚖️ Weighted Avg £ / tonne", f"{weighted_avg:,.2f}")

    st.divider()

    # --------------------------------------------------
    # TABS
    # --------------------------------------------------
    tab_overview, tab_data, tab_download = st.tabs(
        ["📊 Overview", "📋 Data Tables", "⬇ Download"]
    )

    # --------------------------------------------------
    # OVERVIEW TAB (WITH EXPANDERS)
    # --------------------------------------------------
    with tab_overview:

        with st.expander("📦 Net Weight by Waste Type", expanded=False):
            waste_in = fi.groupby("Waste Type ID")["Net Weight (tn)"].sum().reset_index()
            waste_in["Type"] = "Incoming"
            waste_out = fo.groupby("Waste Type ID")["Net Weight (tn)"].sum().reset_index()
            waste_out["Type"] = "Outgoing"

            combined = pd.concat([waste_in, waste_out])

            if not combined.empty:
                fig1 = px.bar(
                    combined,
                    x="Waste Type ID",
                    y="Net Weight (tn)",
                    color="Type",
                    barmode="group"
                )
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("No data available.")

        with st.expander("🥧 Material Grade Distribution", expanded=False):
            if "Grade" in fi.columns and not fi.empty:
                grade_df = fi.groupby("Grade")["Net Weight (tn)"].sum().reset_index()
                fig2 = px.pie(
                    grade_df,
                    names="Grade",
                    values="Net Weight (tn)"
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No grade data available.")

        with st.expander("📈 Incoming vs Outgoing Trend", expanded=False):
            in_trend = fi.groupby("Ticket Date")["Net Weight (tn)"].sum().reset_index()
            in_trend["Type"] = "Incoming"
            out_trend = fo.groupby("Ticket Date")["Net Weight (tn)"].sum().reset_index()
            out_trend["Type"] = "Outgoing"

            trend = pd.concat([in_trend, out_trend])

            if not trend.empty:
                fig3 = px.line(
                    trend,
                    x="Ticket Date",
                    y="Net Weight (tn)",
                    color="Type",
                    markers=True
                )
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No trend data available.")

        with st.expander("💰 Cost per Tonne Trend", expanded=False):
            daily_cost = fi.groupby("Ticket Date")["Cost"].sum().reset_index()
            daily_weight = fi.groupby("Ticket Date")["Net Weight (tn)"].sum().reset_index()

            cpt = pd.merge(daily_cost, daily_weight, on="Ticket Date")
            cpt["Cost per Tonne"] = cpt["Cost"] / cpt["Net Weight (tn)"]

            if not cpt.empty:
                fig4 = px.line(
                    cpt,
                    x="Ticket Date",
                    y="Cost per Tonne",
                    markers=True
                )
                st.plotly_chart(fig4, use_container_width=True)
            else:
                st.info("No cost data available.")

    # --------------------------------------------------
    # DATA TAB
    # --------------------------------------------------
    with tab_data:
        st.subheader("Incoming Data")
        st.dataframe(fi, use_container_width=True)
        st.subheader("Outgoing Data")
        st.dataframe(fo, use_container_width=True)

    # --------------------------------------------------
    # DOWNLOAD TAB
    # --------------------------------------------------
    with tab_download:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            fi.to_excel(writer, index=False, sheet_name="Incoming")
            fo.to_excel(writer, index=False, sheet_name="Outgoing")

        st.download_button(
            "📥 Download Excel Report",
            buffer.getvalue(),
            file_name="Material_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.caption("♻ Material Management Dashboard, made without breaking the monitor ")

# ==================================================
# APP ENTRY POINT
# ==================================================
if st.session_state.logged_in:
    dashboard()
else:
    login_screen()
