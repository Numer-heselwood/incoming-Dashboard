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
USERS = {"admin": hash_pw("admin123")}

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

    # ✅ FORCE DATE PARSING (UK SAFE)
    if IN_COLS["ticket_date"] in incoming.columns:
        incoming[IN_COLS["ticket_date"]] = pd.to_datetime(incoming[IN_COLS["ticket_date"]], dayfirst=True, errors="coerce")

    if OUT_COLS["ticket_date"] in outgoing.columns:
        outgoing[OUT_COLS["ticket_date"]] = pd.to_datetime(outgoing[OUT_COLS["ticket_date"]], dayfirst=True, errors="coerce")

    return incoming, outgoing

# ==================================================
# INCOMING VIEW
# ==================================================
def incoming_view(incoming):
    st.title("📥 Incoming")

    st.sidebar.header("Filters (Incoming)")

    waste_col = col_exists(incoming, IN_COLS["waste_type"])
    supplier_col = col_exists(incoming, IN_COLS["supplier"])
    date_col = col_exists(incoming, IN_COLS["ticket_date"])

    selected_waste = st.sidebar.multiselect(
        "Waste Type",
        sorted(incoming[waste_col].dropna().astype(str).unique()) if waste_col else []
    )

    selected_supplier = st.sidebar.multiselect(
        "Supplier",
        sorted(incoming[supplier_col].dropna().astype(str).unique()) if supplier_col else []
    )

    # ✅ BETTER DATE PICKER
    if date_col:
        min_date = incoming[date_col].min()
        max_date = incoming[date_col].max()

        date_range = st.sidebar.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
    else:
        date_range = None

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

    # SAFE CALC
    if IN_COLS["cost"] in fi.columns and IN_COLS["weight"] in fi.columns:
        cost = pd.to_numeric(fi[IN_COLS["cost"]], errors="coerce")
        weight = pd.to_numeric(fi[IN_COLS["weight"]], errors="coerce")
        fi["Cost / Tonne"] = (cost / weight).round(2)

    # ✅ UK DATE FORMAT DISPLAY
    if date_col in fi.columns:
        fi[date_col] = fi[date_col].dt.strftime("%d/%m/%Y")

    display_cols = [
        IN_COLS["ticket_id"],
        IN_COLS["ticket_date"],
        IN_COLS["waste_type"],
        IN_COLS["weight"],
        IN_COLS["first_weight"],
        IN_COLS["second_weight"],
        "Cost / Tonne",
        IN_COLS["cost"],
        IN_COLS["supplier"],
        IN_COLS["paid_date"],
        IN_COLS["mpn_date"],
        IN_COLS["comments"]
    ]
    display_cols = [c for c in display_cols if c in fi.columns]

    # SEARCH
    st.subheader("🎯 Ticket Lookup")
    ticket = st.text_input("Enter Ticket ID")

    if ticket:
        try:
            t = int(ticket)
            df = incoming[incoming[IN_COLS["ticket_id"]] == t].copy()

            if df.empty:
                st.warning("No records found")
            else:
                st.dataframe(df[display_cols], use_container_width=True)
        except:
            st.error("Enter a valid number")

    st.subheader("📊 Filtered Data")
    st.dataframe(fi[display_cols], use_container_width=True)

# ==================================================
# OUTGOING VIEW
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

        date_range = st.sidebar.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
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
        OUT_COLS["ticket_id"],
        OUT_COLS["ticket_date"],
        OUT_COLS["waste_type"],
        OUT_COLS["weight"],
        OUT_COLS["first_weight"],
        OUT_COLS["second_weight"],
        OUT_COLS["price_mt"],
        OUT_COLS["total_price"],
        OUT_COLS["customer"],
        OUT_COLS["comments"]
    ]
    display_cols = [c for c in display_cols if c in fo.columns]

    st.subheader("🎯 Ticket Lookup")
    ticket = st.text_input("Enter Ticket ID", key="out_ticket")

    if ticket:
        try:
            t = int(ticket)
            df = outgoing[outgoing[OUT_COLS["ticket_id"]] == t]

            if df.empty:
                st.warning("No records found")
            else:
                st.dataframe(df[display_cols], use_container_width=True)
        except:
            st.error("Enter a valid number")

    st.subheader("📊 Filtered Data")
    st.dataframe(fo[display_cols], use_container_width=True)

# ==================================================
# MAIN
# ==================================================
def dashboard():
    incoming, outgoing = load_data()

    view = st.radio("Select View", ["Incoming", "Outgoing"], horizontal=True)

    st.sidebar.empty()

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