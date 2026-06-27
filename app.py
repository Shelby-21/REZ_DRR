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

# ============================================
# Merge All Data
# ============================================

def merge_all_data(unit_df, sales_df, gv_df, inv_df):

    master_df = unit_df.copy()

    # Merge Sales
    master_df = master_df.merge(
        sales_df,
        on=ASIN_COLUMN,
        how="left",
        suffixes=("_Unit", "_Sales")
    )

    # Merge Inventory
    master_df = master_df.merge(
        inv_df,
        on=ASIN_COLUMN,
        how="left"
    )

    # Merge GV
    master_df = master_df.merge(
        gv_df,
        on=ASIN_COLUMN,
        how="left"
    )

    return master_df

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

    try:
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
            # -----------------------------
            inv_df = pd.read_excel(inv_file)

        st.success("All files loaded successfully!")

        with st.spinner("Aggregating Unit & Sales Files..."):

            # Weekly columns for Unit File
            unit_columns = [
                "Wk24",
                "Wk25"
            ]

            # Weekly columns for Sales File
            sales_columns = [
                "Wk24",
                "Wk25"
            ]

            unit_df = aggregate_by_asin(
                unit_df,
                unit_columns
            )

            sales_df = aggregate_by_asin(
                sales_df,
                sales_columns
            )

        with st.spinner("Processing Inventory File..."):

            inv_df = process_inventory(inv_df)

        with st.spinner("Processing GV File..."):

            gv_df = process_gv(gv_df)

        with st.spinner("Merging all files..."):

            master_df = merge_all_data(
                unit_df,
                sales_df,
                gv_df,
                inv_df
            )

        st.subheader("Master Data Preview")

        st.dataframe(master_df.head())

    except Exception as e:
        st.error(f"An error occurred during execution: {e}")
