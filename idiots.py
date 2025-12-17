import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import hashlib

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="♻ Material Management Dashboard",
    layout="wide"
)

# ==================================================
# LOGIN SETUP
# ==================================================
def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

USERS = {
    "admin": hash_pw("admin123"),
    "god": hash_pw("god123")
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

def login_screen():
    st.title("🔐 Material Management Dashboard Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login", use_container_width=True):
        if username in USERS and USERS[username] == hash_pw(password):
            st.session_state.logged_in = True
            st.session_state.username = username
        else:
            st.error("❌ Invalid username or password")

def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""

# ==================================================
# DASHBOARD
# ==================================================
def dashboard():
    st.sidebar.button("🔓 Logout", on_click=logout)
    st.markdown("<h1 style='text-align:center;'>♻ Material Management Dashboard</h1>", unsafe_allow_html=True)
    st.divider()

    # ----------------------
    # LOAD DATA
    # ----------------------
    FILE_PATH = "Material incoming dashboard.xlsx"
    try:
        incoming = pd.read_excel(FILE_PATH, sheet_name="INCOMING MASTER")
        outgoing = pd.read_excel(FILE_PATH, sheet_name="OUTGOING MASTER")
    except Exception as e:
        st.error(f"❌ Failed to load Excel: {e}")
        st.stop()

    incoming.columns = incoming.columns.str.strip()
    outgoing.columns = outgoing.columns.str.strip()
    incoming["Ticket Date"] = pd.to_datetime(incoming["Ticket Date"], errors="coerce")
    outgoing["Ticket Date"] = pd.to_datetime(outgoing["Ticket Date"], errors="coerce")
    incoming = incoming.dropna(subset=["Ticket Date"])
    outgoing = outgoing.dropna(subset=["Ticket Date"])

    # ----------------------
    # FILTERS
    # ----------------------
    with st.sidebar:
        st.header("🔎 Dashboard Filters")
        min_date = incoming["Ticket Date"].min().date()
        max_date = incoming["Ticket Date"].max().date()
        date_range = st.date_input("Date Range", (min_date, max_date))
        customer = st.selectbox("Customer", ["All"] + sorted(incoming["Customer Name"].dropna().unique()))
        waste_types = incoming["Waste Type ID"].astype(str).str.strip().unique().tolist()
        waste_type = st.multiselect("Waste Type", options=["All"] + sorted(waste_types), default=["All"])
        if "All" in waste_type:
            waste_type = waste_types
        price_filter = st.radio("Price Filter", ["All", "Priced", "Not Priced"])

    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])

    # ----------------------
    # APPLY FILTERS
    # ----------------------
    fi = incoming[(incoming["Ticket Date"].between(start_date, end_date)) &
                  (incoming["Waste Type ID"].astype(str).str.strip().isin(waste_type))]
    fo = outgoing[(outgoing["Ticket Date"].between(start_date, end_date)) &
                  (outgoing["Waste Type ID"].astype(str).str.strip().isin(waste_type))]
    if customer != "All":
        fi = fi[fi["Customer Name"] == customer]
        fo = fo[fo["Customer Name"] == customer]
    if price_filter == "Priced":
        fi = fi[fi["Cost"] > 0]
    elif price_filter == "Not Priced":
        fi = fi[(fi["Cost"].isna()) | (fi["Cost"] == 0)]

    # ----------------------
    # KPIs
    # ----------------------
    incoming_tn = fi["Net Weight (tn)"].sum()
    outgoing_tn = fo["Net Weight (tn)"].sum()
    total_cost = fi["Cost"].sum()
    weighted_avg = total_cost / incoming_tn if incoming_tn > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("⬅️ Incoming (tn)", f"{incoming_tn:,.2f}")
    c2.metric("➡️ Outgoing (tn)", f"{outgoing_tn:,.2f}")
    c3.metric("💰 Total Cost (£)", f"{total_cost:,.2f}")
    c4.metric("⚖️ Weighted Avg £ / tonne", f"{weighted_avg:,.2f}")
    st.divider()

    # ----------------------
    # TABS
    # ----------------------
    tab_overview, tab_data, tab_download, tab_supplier = st.tabs(
        ["📊 Overview", "📋 Data Tables", "⬇ Download", "🏭 Supplier Trend"]
    )

    # ----------------------
    # OVERVIEW TAB
    # ----------------------
    with tab_overview:
        with st.expander("📦 Net Weight by Waste Type", expanded=False):
            w_in = fi.groupby("Waste Type ID")["Net Weight (tn)"].sum().reset_index()
            w_in["Type"] = "Incoming"
            w_out = fo.groupby("Waste Type ID")["Net Weight (tn)"].sum().reset_index()
            w_out["Type"] = "Outgoing"
            combined = pd.concat([w_in, w_out])
            if not combined.empty:
                st.plotly_chart(px.bar(combined, x="Waste Type ID", y="Net Weight (tn)", color="Type", barmode="group"),
                                use_container_width=True)
            else:
                st.info("No data available.")

        with st.expander("🥧 Material Grade Distribution", expanded=False):
            if "Grade" in fi.columns and not fi.empty:
                grade_df = fi.groupby("Grade")["Net Weight (tn)"].sum().reset_index()
                st.plotly_chart(px.pie(grade_df, names="Grade", values="Net Weight (tn)"), use_container_width=True)

        with st.expander("📈 Incoming vs Outgoing Trend", expanded=False):
            t_in = fi.groupby("Ticket Date")["Net Weight (tn)"].sum().reset_index()
            t_in["Type"] = "Incoming"
            t_out = fo.groupby("Ticket Date")["Net Weight (tn)"].sum().reset_index()
            t_out["Type"] = "Outgoing"
            trend = pd.concat([t_in, t_out])
            if not trend.empty:
                st.plotly_chart(px.line(trend, x="Ticket Date", y="Net Weight (tn)", color="Type", markers=True),
                                use_container_width=True)

        with st.expander("💰 Cost per Tonne Trend", expanded=False):
            daily_cost = fi.groupby("Ticket Date")["Cost"].sum().reset_index()
            daily_weight = fi.groupby("Ticket Date")["Net Weight (tn)"].sum().reset_index()
            cpt = pd.merge(daily_cost, daily_weight, on="Ticket Date")
            cpt["Cost per Tonne"] = cpt["Cost"] / cpt["Net Weight (tn)"]
            if not cpt.empty:
                st.plotly_chart(px.line(cpt, x="Ticket Date", y="Cost per Tonne", markers=True),
                                use_container_width=True)

    # ----------------------
    # DATA TAB
    # ----------------------
    with tab_data:
        st.subheader("Incoming Data")
        st.dataframe(fi, use_container_width=True)
        st.subheader("Outgoing Data")
        st.dataframe(fo, use_container_width=True)

    # ----------------------
    # DOWNLOAD TAB
    # ----------------------
    with tab_download:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            fi.to_excel(writer, index=False, sheet_name="Incoming")
            fo.to_excel(writer, index=False, sheet_name="Outgoing")
        st.download_button("📥 Download Excel Report", buffer.getvalue(),
                           file_name="Material_Report.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ----------------------
    # SUPPLIER TREND TAB
    # ----------------------
    with tab_supplier:
        st.header("🏭 Top Suppliers (Incoming)")
        supplier_col = "Customer Name"
        if supplier_col not in fi.columns or fi.empty:
            st.info("⚠️ No data available for the selected filters or supplier")
        else:
            supplier_summary = fi.groupby(supplier_col)["Net Weight (tn)"].sum().reset_index()
            supplier_summary = supplier_summary.sort_values("Net Weight (tn)", ascending=False).head(5)
            max_weight = supplier_summary["Net Weight (tn)"].max()

            # Display Top 5 suppliers with bar indicators
            for idx, row in supplier_summary.iterrows():
                col1, col2, col3 = st.columns([2, 5, 1])
                col1.write(row[supplier_col])
                bar_len = int((row["Net Weight (tn)"] / max_weight) * 300)
                col2.markdown(f"<div style='background-color:#2ca02c; width:{bar_len}px; height:20px;'>&nbsp;</div>", unsafe_allow_html=True)
                col3.write(f"{row['Net Weight (tn)']:.2f} tn")

            st.markdown("---")
            st.subheader("📅 Monthly Breakdown by Supplier")
            selected_supplier = st.selectbox("Select Supplier", options=list(supplier_summary[supplier_col]))
            monthly_data = fi[fi[supplier_col] == selected_supplier].copy()
            monthly_data['Month'] = monthly_data['Ticket Date'].dt.to_period('M').astype(str)
            monthly_summary = monthly_data.groupby('Month')['Net Weight (tn)'].sum().reset_index()
            monthly_max = monthly_summary['Net Weight (tn)'].max()
            for idx, row in monthly_summary.iterrows():
                col1, col2, col3 = st.columns([2, 5, 1])
                col1.write(row['Month'])
                bar_len = int((row['Net Weight (tn)'] / monthly_max) * 300)
                col2.markdown(f"<div style='background-color:#1f77b4; width:{bar_len}px; height:20px;'>&nbsp;</div>", unsafe_allow_html=True)
                col3.write(f"{row['Net Weight (tn)']:.2f} tn")

# ==================================================
# APP ENTRY
# ==================================================
if st.session_state.logged_in:
    dashboard()
else:
    login_screen()
