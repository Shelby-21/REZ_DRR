import streamlit as st
import pandas as pd
import io
ASIN_COLUMN = "ASIN"

# ============================================
# Aggregate Data by ASIN
# ============================================

def aggregate_by_asin(df, value_columns, asin_column=ASIN_COLUMN):

    # Clean column names
    df.columns = df.columns.str.strip()

    # Clean ASIN values
    df[asin_column] = df[asin_column].astype(str).str.strip()

    # Keep only required columns
    required_columns = [asin_column] + value_columns

    df = df[required_columns]

    # Aggregate
    df = (
        df.groupby(asin_column, as_index=False)
        .sum()
    )

    return df

# ============================================
# Process Inventory File
# ============================================

def process_inventory(inv_df):

    # Clean column names
    inv_df.columns = inv_df.columns.str.strip()

    # Keep only FC Inventory
    inv_df = inv_df[
        inv_df["fc_df_flag"] == "FC"
    ]

    # Keep only Sellable Inventory
    inv_df = inv_df[
        inv_df["inventory_condition_code"] == "SELLABLE"
    ]

    # Aggregate Inventory
    inv_df = aggregate_by_asin(
        inv_df,
        ["onhand_qty"]
    )

    return inv_df

# ============================================
# Process GV File
# ============================================

def process_gv(gv_df):

    # Clean column names
    gv_df.columns = gv_df.columns.str.strip()

    # Clean ASIN values
    gv_df[ASIN_COLUMN] = gv_df[ASIN_COLUMN].astype(str).str.strip()

    return gv_df

st.set_page_config(
    page_title="DRR RCA Engine",
    page_icon="📊",
    layout="wide"
)

st.title("📊 DRR Root Cause Analysis Engine")
st.markdown("Upload the required files below.")

st.divider()

col1, col2 = st.columns(2)

with col1:
    unit_file = st.file_uploader(
        "Upload WoW Unit File",
        type=["xlsx"]
    )

    sales_file = st.file_uploader(
        "Upload WoW Sales File",
        type=["xlsx"]
    )

with col2:
    gv_file = st.file_uploader(
        "Upload GV File",
        type=["xlsx"]
    )

    inv_file = st.file_uploader(
        "Upload Inventory File",
        type=["xlsx"]
    )

st.divider()

process = st.button(
    "Run DRR RCA",
    use_container_width=True
)
if process:

    if None in [unit_file, sales_file, gv_file, inv_file]:
        st.error("Please upload all four required files.")
        st.stop()

    with st.spinner("Reading uploaded files..."):

        # -----------------------------
        # Read WoW Unit File
        # -----------------------------
        unit_df = pd.read_excel(unit_file)

        # -----------------------------
        # Read WoW Sales File
        # -----------------------------
        sales_df = pd.read_excel(sales_file)

        # -----------------------------
        # Read GV File
        # -----------------------------
        gv_df = pd.read_excel(gv_file)

        # -----------------------------
        # Read Inventory File
