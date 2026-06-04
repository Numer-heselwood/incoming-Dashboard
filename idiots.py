import streamlit as st
import pandas as pd
import hashlib

# ==================================================
# CONFIG
# ==================================================
st.set_page_config(page_title="♻ Material Dashboard", layout="wide")

FILE_PATH = "Daily Report_WHL NUMER New.xlsm"

INCOMING_SHEET = "Incoming - Feb. Onwards+unpaid"
OUTGOING_SHEET = "Outgoing - Feb'25 onwards"

# ==================================================
# HELPERS
# ==================================================
def col_exists(df, col):
    return col if col in df.columns else None

def hash_pw(p): 
    return hashlib.sha256(p.encode()).hexdigest()

# ==================================================
# COLUMN MAPS
# ==================================================
IN_COLS = {
    "ticket_id": "Ticket ID",
    "ticket_date": "Ticket Date",
    "paid_date": "Paid Date",
    "mpn_date": "MPN Document Date",
    "waste_type": "Waste Type ID",
    "weight": "Net WeightMT",
    "first_weight": "First Weight",
    "second_weight": "Second Weight",
    "cost": "Cost",
    "cost_per_tonne": "Cost Per Tonne",
    "supplier": "Supplier Name",
    "comments": "Comments"
}

OUT_COLS = {
    "ticket_id": "Ticket ID",
    "ticket_date": "Ticket Date",
    "waste_type": "Waste Type ID",
    "weight": "Net Weight MT",
    "first_weight": "First Weight",
    "second_weight": "Second Weight",
    "price_mt": "Price/MT",
    "total_price": "Total Price",
    "customer": "Customer Name",
    "comments": "Comments"
}

# ==================================================
# LOGIN
# ==================================================
USERS = {"admin": hash_pw("admin123"),"Numer": hash_pw("God")}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.title("🔐 Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u in USERS and USERS[u] == hash_pw(p):
            st.session_state.logged_in = True
        else:
            st.error("Invalid login")

# ==================================================
# LOAD DATA
# ==================================================
@st.cache_data
def load_data():
    incoming = pd.read_excel(FILE_PATH, sheet_name=INCOMING_SHEET, engine="openpyxl")
    outgoing = pd.read_excel(FILE_PATH, sheet_name=OUTGOING_SHEET, engine="openpyxl")

    incoming.columns = incoming.columns.str.strip()
    outgoing.columns = outgoing.columns.str.strip()

    # Dates UK format
    for col in [IN_COLS["ticket_date"], IN_COLS["paid_date"], IN_COLS["mpn_date"]]:
        if col in incoming.columns:
            incoming[col] = pd.to_datetime(incoming[col], dayfirst=True, errors="coerce")

    if OUT_COLS["ticket_date"] in outgoing.columns:
        outgoing[OUT_COLS["ticket_date"]] = pd.to_datetime(
            outgoing[OUT_COLS["ticket_date"]], dayfirst=True, errors="coerce"
        )

    return incoming, outgoing

# ==================================================
# INCOMING
# ==================================================
def incoming_view(incoming):
    st.title("📥 Incoming")

    st.sidebar.header("Filters (Incoming)")

    waste_col = col_exists(incoming, IN_COLS["waste_type"])
    supplier_col = col_exists(incoming, IN_COLS["supplier"])
    date_col = col_exists(incoming, IN_COLS["ticket_date"])
    paid_col = col_exists(incoming, IN_COLS["paid_date"])

    selected_waste = st.sidebar.multiselect(
        "Waste Type",
        sorted(incoming[waste_col].dropna().astype(str).unique()) if waste_col else []
    )

    selected_supplier = st.sidebar.multiselect(
        "Supplier",
        sorted(incoming[supplier_col].dropna().astype(str).unique()) if supplier_col else []
    )

    if date_col:
        min_date = incoming[date_col].min()
        max_date = incoming[date_col].max()

        date_range = st.sidebar.date_input("Date Range", value=(min_date, max_date))
    else:
        date_range = None

    paid_filter = st.sidebar.radio("Payment Status", ["All", "Paid", "Unpaid"])

    fi = incoming.copy()

    if selected_waste:
        fi = fi[fi[waste_col].astype(str).isin(selected_waste)]

    if selected_supplier:
        fi = fi[fi[supplier_col].astype(str).isin(selected_supplier)]

    if date_range and len(date_range) == 2:
        fi = fi[
            (fi[date_col] >= pd.to_datetime(date_range[0])) &
            (fi[date_col] <= pd.to_datetime(date_range[1]))
        ]

    if paid_col:
        if paid_filter == "Paid":
            fi = fi[fi[paid_col].notna()]
        elif paid_filter == "Unpaid":
            fi = fi[fi[paid_col].isna()]

    for col in [date_col, paid_col, IN_COLS["mpn_date"]]:
        if col in fi.columns:
            fi[col] = fi[col].dt.strftime("%d/%m/%Y")

    display_cols = [
        IN_COLS["ticket_id"], IN_COLS["ticket_date"], IN_COLS["waste_type"],
        IN_COLS["weight"], IN_COLS["first_weight"], IN_COLS["second_weight"],
        IN_COLS["cost_per_tonne"], IN_COLS["cost"], IN_COLS["supplier"],
        IN_COLS["paid_date"], IN_COLS["mpn_date"], IN_COLS["comments"]
    ]
    display_cols = [c for c in display_cols if c in fi.columns]

    # SEARCH
    st.subheader("🎯 Ticket Lookup")
    ticket = st.text_input("Enter Ticket ID")

    if ticket:
        df = incoming.copy()
        df[IN_COLS["ticket_id"]] = df[IN_COLS["ticket_id"]].astype(str).str.replace(".0","").str.strip()
        df = df[df[IN_COLS["ticket_id"]] == ticket.strip()]

        if df.empty:
            st.warning("No records found")
        else:
            st.dataframe(df[display_cols], use_container_width=True)

    st.subheader("📊 Filtered Data")
    st.dataframe(fi[display_cols], use_container_width=True)

    col1, col2 = st.columns(2)

    if IN_COLS["weight"] in fi.columns:
        col1.metric("Total Net Weight", f"{pd.to_numeric(fi[IN_COLS['weight']], errors='coerce').sum():,.2f} MT")

    if IN_COLS["cost"] in fi.columns:
        col2.metric("Total Cost", f"£{pd.to_numeric(fi[IN_COLS['cost']], errors='coerce').sum():,.2f}")

# ==================================================
# OUTGOING (FIXED SEARCH ADDED BACK)
# ==================================================
def outgoing_view(outgoing):
    st.title("📤 Outgoing")

    st.sidebar.header("Filters (Outgoing)")

    waste_col = col_exists(outgoing, OUT_COLS["waste_type"])
    customer_col = col_exists(outgoing, OUT_COLS["customer"])
    date_col = col_exists(outgoing, OUT_COLS["ticket_date"])

    selected_waste = st.sidebar.multiselect(
        "Waste Type",
        sorted(outgoing[waste_col].dropna().astype(str).unique()) if waste_col else []
    )

    selected_customer = st.sidebar.multiselect(
        "Customer",
        sorted(outgoing[customer_col].dropna().astype(str).unique()) if customer_col else []
    )

    if date_col:
        min_date = outgoing[date_col].min()
        max_date = outgoing[date_col].max()
        date_range = st.sidebar.date_input("Date Range", value=(min_date, max_date))
    else:
        date_range = None

    fo = outgoing.copy()

    if selected_waste:
        fo = fo[fo[waste_col].astype(str).isin(selected_waste)]

    if selected_customer:
        fo = fo[fo[customer_col].astype(str).isin(selected_customer)]

    if date_range and len(date_range) == 2:
        fo = fo[
            (fo[date_col] >= pd.to_datetime(date_range[0])) &
            (fo[date_col] <= pd.to_datetime(date_range[1]))
        ]

    if date_col in fo.columns:
        fo[date_col] = fo[date_col].dt.strftime("%d/%m/%Y")

    display_cols = [
        OUT_COLS["ticket_id"], OUT_COLS["ticket_date"], OUT_COLS["waste_type"],
        OUT_COLS["weight"], OUT_COLS["first_weight"], OUT_COLS["second_weight"],
        OUT_COLS["price_mt"], OUT_COLS["total_price"], OUT_COLS["customer"],
        OUT_COLS["comments"]
    ]
    display_cols = [c for c in display_cols if c in fo.columns]

    # ✅ SEARCH ADDED BACK
    st.subheader("🎯 Ticket Lookup")
    ticket = st.text_input("Enter Ticket ID", key="out_ticket")

    if ticket:
        df = outgoing.copy()
        df[OUT_COLS["ticket_id"]] = df[OUT_COLS["ticket_id"]].astype(str).str.replace(".0","").str.strip()
        df = df[df[OUT_COLS["ticket_id"]] == ticket.strip()]

        if df.empty:
            st.warning("No records found")
        else:
            st.dataframe(df[display_cols], use_container_width=True)

    st.subheader("📊 Filtered Data")
    st.dataframe(fo[display_cols], use_container_width=True)

    col1, col2 = st.columns(2)

    if OUT_COLS["weight"] in fo.columns:
        col1.metric("Total Net Weight", f"{pd.to_numeric(fo[OUT_COLS['weight']], errors='coerce').sum():,.2f} MT")

    if OUT_COLS["total_price"] in fo.columns:
        col2.metric("Total Sale Price", f"£{pd.to_numeric(fo[OUT_COLS['total_price']], errors='coerce').sum():,.2f}")

# ==================================================
# MAIN
# ==================================================
def dashboard():
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()

    incoming, outgoing = load_data()

    view = st.radio("Select View", ["Incoming", "Outgoing"], horizontal=True)

    if view == "Incoming":
        incoming_view(incoming)
    else:
        outgoing_view(outgoing)

# ==================================================
# RUN
# ==================================================
if st.session_state.logged_in:
    dashboard()
else:
    login()