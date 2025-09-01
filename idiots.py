import pandas as pd
import plotly.express as px
import streamlit as st
from io import BytesIO

# ---- PAGE CONFIG ----
st.set_page_config(page_title="♻ Material Management Dashboard", layout="wide")

# ---- READ EXCEL FILE ----
excel_file_path = "Material incoming dashboard.xlsx"

with st.spinner("Loading data..."):
    incoming_df = pd.read_excel(excel_file_path, sheet_name="INCOMING MASTER")
    outgoing_df = pd.read_excel(excel_file_path, sheet_name="OUTGOING MASTER")

    # Clean column names
    incoming_df.columns = incoming_df.columns.str.strip()
    outgoing_df.columns = outgoing_df.columns.str.strip()

    # Ensure 'Ticket Date' is datetime
    incoming_df["Ticket Date"] = pd.to_datetime(incoming_df["Ticket Date"])
    outgoing_df["Ticket Date"] = pd.to_datetime(outgoing_df["Ticket Date"])

# ---- DASHBOARD TITLE ----
st.markdown("<h1 style='text-align: center;'>♻ Material Management Dashboard</h1>", unsafe_allow_html=True)
st.divider()

# ---- SIDEBAR FILTERS ----
st.sidebar.header("🔎 Dashboard Filters")

# --- Date Range Filter ---
with st.sidebar.expander("📅 Date Filters", expanded=True):
    date_range = st.date_input(
        "Select Date Range",
        value=[incoming_df["Ticket Date"].min().date(), incoming_df["Ticket Date"].max().date()],
        min_value=incoming_df["Ticket Date"].min().date(),
        max_value=incoming_df["Ticket Date"].max().date()
    )

# --- Customer & Waste Type Filters ---
with st.sidebar.expander("👤 Customer & Waste Type", expanded=True):
    customer = st.selectbox("Select Customer", options=["All"] + list(incoming_df["Customer Name"].unique()))
    waste_type_options = incoming_df["Waste Type ID"].astype(str).str.strip().unique()
    waste_type = st.multiselect(
        "Select Waste Type",
        options=["All"] + list(waste_type_options),
        default=["All"]
    )

# ---- Adjust Waste Type Filter ----
if "All" in waste_type:
    waste_type = waste_type_options

# ---- FILTER DATA ----
with st.spinner("Applying filters..."):
    if date_range and len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    else:
        start_date, end_date = incoming_df["Ticket Date"].min(), incoming_df["Ticket Date"].max()

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

# ---- KPIs ----
incoming_total = filtered_incoming["Net Weight (tn)"].sum()
outgoing_total = filtered_outgoing["Net Weight (tn)"].sum()
total_cost = filtered_incoming["Cost"].sum() if "Cost" in filtered_incoming.columns else 0
avg_cost_tn = filtered_incoming["Cost Per Tonne"].mean() if "Cost Per Tonne" in filtered_incoming.columns else 0

# ---- Plotly Colors ----
plotly_colors = {"Incoming": "#2ca02c", "Outgoing": "#1f77b4"}

# ---- TABS ----
tab_main, tab_data, tab_download = st.tabs(["📊 Overview", "📋 Data Tables", "⬇ Download Report"])

# ---- Main Tab ----
with tab_main:
    # KPIs
    st.subheader("📊 Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("⬅️ Incoming (tn)", f"{incoming_total:,.2f}", help="Total incoming waste in tonnes")
    col2.metric("➡️ Outgoing (tn)", f"{outgoing_total:,.2f}", help="Total outgoing waste in tonnes")
    col3.metric("💰 Total Cost (£)", f"{total_cost:,.2f}", help="Total cost of incoming waste")
    col4.metric("📊 Cost per Tonne (£)", f"{avg_cost_tn:,.2f}", help="Average cost per tonne")

    st.divider()

    # Waste Type Breakdown
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
        fig1.update_traces(marker=dict(line=dict(width=0.7, color='DarkSlateGrey')))
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("⚠️ No data available for Waste Type breakdown")

   # ---- Pie Charts: Ferrous vs Non-Ferrous Side by Side ----
if (not filtered_incoming.empty and "Grade" in filtered_incoming.columns) or \
   (not filtered_outgoing.empty and "Grade" in filtered_outgoing.columns):

    col_in, col_out = st.columns(2)

    # Incoming Pie Chart
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
            st.info("⚠️ No data available for Incoming Grade")

    # Outgoing Pie Chart
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
            st.info("⚠️ No data available for Outgoing Grade")

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
        fig2.update_layout(xaxis_title="Date", yaxis_title="Net Weight (tn)")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("⚠️ No data available for trend")

    # Cost per Tonne Trend
    st.subheader("💰 Cost per Tonne Trend")
    if not filtered_incoming.empty and "Cost Per Tonne" in filtered_incoming.columns:
        daily_cpt = filtered_incoming.groupby("Ticket Date")["Cost Per Tonne"].mean().reset_index()

        fig3 = px.line(
            daily_cpt,
            x="Ticket Date",
            y="Cost Per Tonne",
            markers=True,
            line_shape="spline",
            title="Cost per Tonne Trend"
        )
        fig3.update_layout(xaxis_title="Date", yaxis_title="Cost Per Tonne")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("⚠️ No data available for cost trend")

# ---- Data Tables Tab ----
with tab_data:
    tab1, tab2 = st.tabs(["📥 Incoming", "📤 Outgoing"])
    with tab1:
        st.dataframe(filtered_incoming, use_container_width=True)
    with tab2:
        st.dataframe(filtered_outgoing, use_container_width=True)

# ---- Download Tab ----
with tab_download:
    st.subheader("⬇ Download Filtered Report")
    incoming_export = filtered_incoming.copy()
    outgoing_export = filtered_outgoing.copy()

    date_range_str = f"{start_date.date()}_{end_date.date()}"
    filename = f"Waste_Report_{date_range_str}.xlsx"

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        incoming_export.to_excel(writer, index=False, sheet_name="Incoming")
        outgoing_export.to_excel(writer, index=False, sheet_name="Outgoing")

    excel_data = output.getvalue()
    st.download_button(
        label="📥 Download Excel Report",
        data=excel_data,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.divider()

# ---- Footer ----
st.markdown(
    """
    <div style="text-align:center; padding: 10px; color: gray; font-size: 0.9em;">
        ♻ Material Management Dashboard | Built without breaking the monitor 😆
    </div>
    """,
    unsafe_allow_html=True
)
