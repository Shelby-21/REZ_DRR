import streamlit as st
import pandas as pd
import io

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

    st.subheader("Uploaded Data Preview")

    tab1, tab2, tab3, tab4 = st.tabs([
        "WoW Unit",
        "WoW Sales",
        "GV",
        "Inventory"
    ])

    with tab1:
        st.dataframe(unit_df.head())

    with tab2:
        st.dataframe(sales_df.head())

    with tab3:
        st.dataframe(gv_df.head())

    with tab4:
        st.dataframe(inv_df.head())
