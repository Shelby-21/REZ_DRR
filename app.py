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

    st.subheader("Aggregated Preview")

    tab1, tab2 = st.tabs([
        "Unit",
        "Sales"
    ])

    with tab1:
        st.dataframe(unit_df.head())

    with tab2:
        st.dataframe(sales_df.head())
