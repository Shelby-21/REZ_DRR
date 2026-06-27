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

    # Convert Week Ending into datetime
    gv_df["Week ending"] = pd.to_datetime(
        gv_df["Week ending"],
        dayfirst=True,
        errors="coerce"
    )

    # Remove rows with invalid dates
    gv_df = gv_df.dropna(subset=["Week ending"])

    # Sort by Week Ending
    gv_df = gv_df.sort_values("Week ending")

    # Get the latest two unique weeks
    latest_weeks = (
        gv_df["Week ending"]
        .drop_duplicates()
        .sort_values()
        .tail(2)
        .tolist()
    )

    if len(latest_weeks) != 2:
        raise ValueError("GV file must contain at least two unique Week Ending dates.")

    previous_week = latest_weeks[0]
    current_week = latest_weeks[1]

    # Create a readable week label
    gv_df["Week Type"] = gv_df["Week ending"].apply(
        lambda x: "Previous Week" if x == previous_week else
                  "Current Week" if x == current_week else
                  None
    )

    # Keep only Previous & Current Week
    gv_df = gv_df[
        gv_df["Week Type"].notna()
    ]

    # ============================================
    # Pivot MP GV
    # ============================================

    mp_gv = gv_df.pivot_table(
        index=ASIN_COLUMN,
        columns="Week Type",
        values="MP GV",
        aggfunc="sum"
    ).reset_index()

    mp_gv.columns.name = None

    mp_gv.rename(columns={
        "Previous Week": "Previous_MP_GV",
        "Current Week": "Current_MP_GV"
    }, inplace=True)

    # ============================================
    # Pivot P3P GV
    # ============================================

    p3p_gv = gv_df.pivot_table(
        index=ASIN_COLUMN,
        columns="Week Type",
        values="P3P GV",
        aggfunc="sum"
    ).reset_index()

    p3p_gv.columns.name = None

    p3p_gv.rename(columns={
        "Previous Week": "Previous_P3P_GV",
        "Current Week": "Current_P3P_GV"
    }, inplace=True)

    # ============================================
    # Merge both Pivot Tables
    # ============================================

    gv_df = mp_gv.merge(
        p3p_gv,
        on=ASIN_COLUMN,
        how="outer"
    )

    return gv_df

# ============================================
# Merge All Data
# ============================================

def merge_all_data(unit_df, sales_df, gv_df, inv_df):

    # Unit File is our master truth baseline
    master_df = unit_df.copy()

    # Left Join Sales
    master_df = master_df.merge(
        sales_df,
        on=ASIN_COLUMN,
        how="left",
        suffixes=("_Unit", "_Sales")
    )

    # Left Join Inventory
    master_df = master_df.merge(
        inv_df,
        on=ASIN_COLUMN,
        how="left"
    )

    # Left Join the pivoted GV
    master_df = master_df.merge(
        gv_df,
        on=ASIN_COLUMN,
        how="left"
    )

    # Force your exact column structure and structural order
    final_columns = [
        ASIN_COLUMN,
        "Wk24_Unit", "Wk25_Unit",
        "Wk24_Sales", "Wk25_Sales",
        "onhand_qty",
        "Previous_MP_GV", "Current_MP_GV",
        "Previous_P3P_GV", "Current_P3P_GV"
    ]

    # Generate safety column fallbacks if any file missed matching rows entirely
    for col in final_columns:
        if col not in master_df.columns:
            master_df[col] = 0

    # Clean subset selection & format fill
    master_df = master_df[final_columns]
    master_df = master_df.fillna(0)

    return master_df

# ============================================
# Calculate DRR
# ============================================

def calculate_drr(master_df):

    # Current Week DRR
    master_df["Current_DRR"] = (
        master_df["Wk25_Unit"] / 7
    )

    # Previous Week DRR
    master_df["Previous_DRR"] = (
        master_df["Wk24_Unit"] / 7
    )

    # DRR % Change
    master_df["DRR_%_Change"] = (
        (
            master_df["Current_DRR"]
            - master_df["Previous_DRR"]
        )
        /
        master_df["Previous_DRR"]
    ) * 100

    return master_df

# ============================================
# Calculate ASP
# ============================================

def calculate_asp(master_df):

    # Force conversion to numeric to prevent division zeroes
    for col in ["Wk24_Sales", "Wk24_Unit", "Wk25_Sales", "Wk25_Unit"]:
        master_df[col] = pd.to_numeric(master_df[col], errors='coerce').fillna(0)

    # Previous Week ASP
    master_df["Previous_ASP"] = master_df["Wk24_Sales"] / master_df["Wk24_Unit"].replace(0, pd.NA)

    # Current Week ASP
    master_df["Current_ASP"] = master_df["Wk25_Sales"] / master_df["Wk25_Unit"].replace(0, pd.NA)

    # ASP % Change
    master_df["ASP_%_Change"] = (
        (master_df["Current_ASP"] - master_df["Previous_ASP"])
        / master_df["Previous_ASP"].replace(0, pd.NA)
    ) * 100

    master_df["Previous_ASP"] = master_df["Previous_ASP"].fillna(0)
    master_df["Current_ASP"] = master_df["Current_ASP"].fillna(0)
    master_df["ASP_%_Change"] = master_df["ASP_%_Change"].fillna(0)

    return master_df

# ============================================
# Calculate Conversion
# ============================================

def calculate_conversion(master_df):

    # Previous Week Conversion
    master_df["Previous_Conversion"] = (
        master_df["Wk24_Unit"]
        .div(master_df["Previous_P3P_GV"])
    )

    # Current Week Conversion
    master_df["Current_Conversion"] = (
        master_df["Wk25_Unit"]
        .div(master_df["Current_P3P_GV"])
    )

    # Conversion % Change
    master_df["Conversion_%_Change"] = (
        (
            master_df["Current_Conversion"] -
            master_df["Previous_Conversion"]
        )
        .div(master_df["Previous_Conversion"])
        .replace([float("inf"), float("-inf")], pd.NA)
        * 100
    )

    return master_df

# ============================================
# Calculate Inventory Status
# ============================================

def calculate_inventory(master_df):
    
    # Force the column to be numeric first
    master_df["onhand_qty"] = pd.to_numeric(master_df["onhand_qty"], errors='coerce').fillna(0)
    
    # Now the comparison will work correctly as integers
    master_df["Inventory_Status"] = master_df["onhand_qty"].apply(
        lambda x: "Low Inventory"
        if x < 21 
        else ""
    )

    return master_df

# ============================================
# Calculate GV Change
# ============================================

def calculate_gv(master_df):

    # MP GV % Change
    master_df["MP_GV_%_Change"] = (
        (
            master_df["Current_MP_GV"] -
            master_df["Previous_MP_GV"]
        )
        .div(master_df["Previous_MP_GV"])
        .replace([float("inf"), float("-inf")], pd.NA)
        * 100
    )

    # P3P GV % Change
    master_df["P3P_GV_%_Change"] = (
        (
            master_df["Current_P3P_GV"] -
            master_df["Previous_P3P_GV"]
        )
        .div(master_df["Previous_P3P_GV"])
        .replace([float("inf"), float("-inf")], pd.NA)
        * 100
    )

    return master_df

# ============================================
# Decision Engine
# ============================================

def generate_remarks(master_df):

    # ASP Remarks
    master_df["ASP_Remarks"] = master_df["ASP_%_Change"].apply(
        lambda x: "ASP Increased | " if pd.notna(x) and x > 0 else ""
    )

    # GV Remarks
    master_df["GV_Remarks"] = master_df["P3P_GV_%_Change"].apply(
        lambda x: "GV Decreased | " if pd.notna(x) and x < 0 else ""
    )

    # Conversion Remarks
    master_df["Conversion_Remarks"] = master_df["Conversion_%_Change"].apply(
        lambda x: "Conversion Decreased | " if pd.notna(x) and x < 0 else ""
    )

    # Inventory Remarks
    master_df["Inventory_Remarks"] = master_df["Inventory_Status"].apply(
        lambda x: "Low Inventory | " if x == "Low Inventory" else ""
    )

    # Manual Intervention
    master_df["Manual_Intervention_Required"] = ""

    missing_data = (
        master_df["Previous_P3P_GV"].isna() |
        master_df["Current_P3P_GV"].isna() |
        master_df["onhand_qty"].isna()
    )

    master_df.loc[
        missing_data,
        "Manual_Intervention_Required"
    ] = "Supporting data missing"

    # Final Remarks
    master_df["Final_Remarks"] = (
        master_df["ASP_Remarks"] +
        master_df["GV_Remarks"] +
        master_df["Conversion_Remarks"] +
        master_df["Inventory_Remarks"]
    )

    # Remove trailing separator
    master_df["Final_Remarks"] = master_df["Final_Remarks"].str.rstrip(" |")

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

        with st.spinner("Merging All Files..."):

            master_df = merge_all_data(
                unit_df,
                sales_df,
                gv_df,
                inv_df
            )

        with st.spinner("Calculating DRR..."):

            master_df = calculate_drr(master_df)

        with st.spinner("Calculating ASP..."):

            master_df = calculate_asp(master_df)

        with st.spinner("Calculating Conversion..."):

            master_df = calculate_conversion(master_df)

        with st.spinner("Checking Inventory..."):

            master_df = calculate_inventory(master_df)

        with st.spinner("Calculating GV..."):

            master_df = calculate_gv(master_df)

        with st.spinner("Generating Remarks..."):

            master_df = generate_remarks(master_df)

        st.subheader("Processed Data Preview")

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Unit",
            "Sales",
            "Inventory",
            "GV",
            "Master"
        ])

        with tab1:
            st.dataframe(unit_df.head())

        with tab2:
            st.dataframe(sales_df.head())

        with tab3:
            st.dataframe(inv_df.head())

        with tab4:
            st.dataframe(gv_df.head())

        with tab5:
            st.dataframe(master_df.sample(100))

        # ============================================
        # Download Output
        # ============================================

        output = io.BytesIO()

        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            # Export the exact master_df shown in the tab
            master_df.to_excel(
                writer,
                index=False,
                sheet_name="Master Data"
            )

        output.seek(0)

        st.download_button(
            label="📥 Download Master Data Output",
            data=output,
            file_name="Master_Data_Output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"An error occurred during execution: {e}")
