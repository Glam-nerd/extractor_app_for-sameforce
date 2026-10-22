import io
import os
import numpy as np
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import streamlit as st

st.set_page_config(
    page_title="Analytics Data Preprocessor & Mapper", page_icon="📊", layout="wide"
)

st.title("R&D Analytics Helper")
st.write("My custom app for preprocessing CreditHive data for analysis under time constraint")
st.divider()

# --- SIDEBAR: CONFIGURATION & UPLOAD ---
with st.sidebar:
    st.header("⚙️ Configuration")
    uploaded_file = st.file_uploader(
        "Upload your data file (CSV or Excel)", type=["csv", "xlsx", "xls"]
    )
    
    st.divider()
    st.subheader("☁️ Cloud Archive")
    gdrive_enabled = st.checkbox("Enable Google Drive Backup")
    gdrive_file_name = st.text_input(
        "Raw File Name in Drive", value="raw_uploaded_data.csv"
    )
    gdrive_folder_id = st.text_input(
        "Google Drive Folder ID (Optional)",
        value="",
        help="Leave blank to save in the Service Account's root directory.",
    )

if uploaded_file is not None:
    try:
        # Read CSV or Excel depending on the file extension
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.success(
            f"Successfully loaded **{uploaded_file.name}**! ({df.shape[0]} rows, {df.shape[1]} columns)"
        )

        # --- STEP 1: GOOGLE DRIVE BACKUP (OPTIONAL) ---
        if gdrive_enabled:
            with st.expander("🚀 Google Drive Backup Action", expanded=True):
                if st.button("Upload Raw Data to Google Drive"):
                    try:
                        credentials_dict = dict(st.secrets["gcp_service_account"])
                        creds = service_account.Credentials.from_service_account_info(
                            credentials_dict, scopes=["https://www.googleapis.com/auth/drive"]
                        )

                        service = build("drive", "v3", credentials=creds)

                        raw_csv_string = df.to_csv(index=False)
                        fh = io.BytesIO(raw_csv_string.encode("utf-8"))
                        media = MediaIoBaseUpload(fh, mimetype="text/csv", resumable=True)

                        file_metadata = {"name": gdrive_file_name}
                        if gdrive_folder_id.strip():
                            file_metadata["parents"] = [gdrive_folder_id.strip()]

                        file = (
                            service.files()
                            .create(body=file_metadata, media_body=media, fields="id")
                            .execute()
                        )
                        st.success(
                            f"✅ Raw data successfully backed up to Google Drive! File ID: `{file.get('id')}`"
                        )
                    except KeyError:
                        st.error(
                            "Missing `gcp_service_account` secret configuration in Streamlit secrets."
                        )
                    except Exception as e:
                        st.error(f"Failed to upload raw data to Google Drive: {e}")
            st.divider()

        # --- STEP 2: CLEAN COLUMNS ---
        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace("-", "_")
        )

        # --- STEP 3: DEFINE COLUMN MAPPING (BASE + ENGINEERED AT THE END) ---
        base_column_mapping = {
            "agent_username": "agent_id",
            "agent_full_name": "agent_name",
            "saleorder-device_id": "saleorder-device_id",
            "sale_order_id": "sale_order_id",
            "order_status": "order_status",
            "order_started_on": "order_date",
            "device_id": "device_id",
            "device": "device_name",
            "upfront_amount": "upfront_amount",
            "upfront_amount_paid": "upfront_amount_paid",
            "fully_upfront_amount_paid_date": "fully_upfront_amount_paid_date",
            "month": "month",
            "quarter": "order_quarter",
            "semi_annual": "semi_annual",
            "year": "order_year",
            "repayment_mode": "repayment_mode",
            "total_tenure": "total_tenure",
            "package_name(plan_name)": "package_name(plan_name)",
            "package_type(plan_type)": "package_type(plan_type)",
            "credit_price": "credit_price",      
            "discount_amount": "discount_amount",      
            "latest_received_on_date": "latest_received_on_date",
            "next_installment_date": "next_installment_date",
            "store_name": "store_name",          
            "store_locality": "store_locality",               
            "store_address": "store_address",                                 
            "store_status": "store_status",                         
            "store_manager_full_name": "store_manager_full_name",
            "customer_full_name": "customer_name",
            "gender": "gender",          
            "date_of_birth": "date_of_birth",
            "marital_status": "marital_status",          
            "highest_education": "highest_education",           
            "total_dependents": "total_dependents",        
            "employment_type": "employment_type",         
            "employed_since": "employed_since",
            "monthly_income": "monthly_income",
            "customer_locality": "customer_locality",          
            "customer_city": "customer_city",
            "latitude": "latitude",
            "longitude": "longitude",    
            "paid_installments": "paid_installments",       
            "unpaid_installments": "unpaid_installments",        
            "total_overdue_amount": "total_overdue_amount",      
            "total_installment_paid_amount": "total_installment_paid_amount",       
            "total_balance_amount": "total_balance_amount"
        }

        # Newly engineered features explicitly placed at the end
        engineered_column_mapping = {
            "total_tenure_in_days": "total_tenure_in_days",
            "total_repayment_amount": "total_repayment_amount",
            "end_of_cycle_date": "end_of_cycle_date",
            "active_delinquency_count": "active_delinquency_count",
            "default_risk_tier": "default_risk_tier",
            "default_status": "default_status"
        }

        # Combine dictionaries preserving insertion order (base first, engineered last)
        column_mapping = {**base_column_mapping, **engineered_column_mapping}

        # Check missing base columns against original input columns
        missing_cols = [orig for orig in base_column_mapping.keys() if orig not in df.columns]

        if len(missing_cols) == len(base_column_mapping):
            st.error("❌ None of the expected columns of interest were found in your file. Please check your headers.")
        elif missing_cols:
            st.warning(f"⚠️ Note: The following expected columns were not found and were skipped: `{missing_cols}`")
        else:
            st.success("✨ All expected columns were successfully found!")

        st.divider()

        # --- STEP 4: DATE PROCESSING & FILTERING ---
        possible_date_cols = ["order_started_on", "order_started_date", "order_sr_date"]
        date_col = next((col for col in possible_date_cols if col in df.columns), None)

        if date_col:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df["year"] = df[date_col].dt.year
            df["quarter"] = "Q" + df[date_col].dt.quarter.astype(str)
            df["semi_annual"] = (
                "Half" + df[date_col].dt.month.le(6).map({True: "1", False: "2"})
            )
            df["month"] = df[date_col].dt.month_name()
            
            if "fully_upfront_amount_paid_date" in df.columns:
                df["fully_upfront_amount_paid_date"] = pd.to_datetime(df["fully_upfront_amount_paid_date"], errors="coerce")
            if "next_installment_date" in df.columns:
                df["next_installment_date"] = pd.to_datetime(df["next_installment_date"], errors="coerce")

            st.success(f"Successfully processed dates from column: `{date_col}`")
            st.divider()

            st.subheader("🔍 Filter Data")
            col1, col2 = st.columns(2)

            with col1:
                available_years = sorted(df["year"].dropna().unique())
                selected_years = st.multiselect("Filter by Year", options=available_years, default=available_years)

            with col2:
                available_quarters = sorted(df["quarter"].dropna().unique())
                selected_quarters = st.multiselect("Filter by Quarter", options=available_quarters, default=available_quarters)

            filtered_df = df[
                df["year"].isin(selected_years) & 
                df["quarter"].isin(selected_quarters)
            ].copy()

            st.info(f"Showing **{len(filtered_df)}** of **{len(df)}** rows after filtering.")
            st.divider()
        else:
            st.error(f"⚠️ None of the expected date columns found! Checked: {possible_date_cols}.")
            filtered_df = df.copy()

        # --- STEP 5: NEWLY ENGINEERED FEATURES ---
        if "repayment_mode" in filtered_df.columns and "total_tenure" in filtered_df.columns:
            def tenure_to_days(row):
                if row['repayment_mode'] == 'D':
                    return row['total_tenure']
                elif row['repayment_mode'] == 'W':
                    return row['total_tenure'] * 7
                elif row['repayment_mode'] == 'M':
                    return row['total_tenure'] * 30
                else:
                    return np.nan

            filtered_df['total_tenure_in_days'] = filtered_df.apply(tenure_to_days, axis=1)

        if "total_installment_paid_amount" in filtered_df.columns and "upfront_amount_paid" in filtered_df.columns:
            filtered_df["total_repayment_amount"] = filtered_df["total_installment_paid_amount"] + filtered_df["upfront_amount_paid"]

        if "fully_upfront_amount_paid_date" in filtered_df.columns and "total_tenure_in_days" in filtered_df.columns:
            filtered_df["end_of_cycle_date"] = filtered_df["fully_upfront_amount_paid_date"] + pd.to_timedelta(filtered_df["total_tenure_in_days"], unit="D")
            
            reference_date = pd.Timestamp.today().normalize()
            
            past_due_mask = filtered_df['next_installment_date'] < reference_date if 'next_installment_date' in filtered_df.columns else False
            is_term_expired = filtered_df['end_of_cycle_date'] < reference_date
            has_overdue_balance = filtered_df['total_overdue_amount'] > 0 if 'total_overdue_amount' in filtered_df.columns else False
            is_delinquent = has_overdue_balance & past_due_mask

            if 'saleorder-device_id' in filtered_df.columns:
                filtered_df['active_delinquency_count'] = is_delinquent.groupby(filtered_df['saleorder-device_id']).transform('sum')
            else:
                filtered_df['active_delinquency_count'] = 0

            conditions = [
                filtered_df['active_delinquency_count'] == 0, 
                (filtered_df['active_delinquency_count'].between(1, 2)) & (~is_term_expired)
            ]
            choices = ['Low Risk', 'Medium Risk']

            filtered_df['default_risk_tier'] = np.select(conditions, choices, default='High Risk / Default')
            filtered_df['default_status'] = np.where(
                filtered_df['end_of_cycle_date'] < reference_date, 'Default', 'Non-Default'
            )

        text_cols_to_capitalize = [
            "agent_full_name", "store_name", "store_manager_full_name", 
            "store_locality", "store_address", "customer_full_name", 
            "customer_locality", "customer_city"
        ]
        
        for col in text_cols_to_capitalize:
            if col in filtered_df.columns:
                filtered_df[col] = filtered_df[col].astype(str).str.title()

        # --- STEP 6: MAPPING, PREVIEW & DOWNLOAD ---
        ordered_sources = [
            col for col in column_mapping.keys() if col in filtered_df.columns
        ]
    
        if ordered_sources:
            transformed_df = filtered_df[ordered_sources].rename(columns=column_mapping)
    
            with st.expander("Preview Cleaned Raw Data"):
                st.dataframe(filtered_df.head())
    
            st.subheader("✨ Transformed Data Preview. Ready for Export")
            st.dataframe(transformed_df, use_container_width=True)
            st.divider()
    
            st.subheader("📥 Local Download")
            csv_data = transformed_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Extracted & Cleaned Data as CSV",
                data=csv_data,
                file_name="extracted_and_mapped_data.csv",
                mime="text/csv",
            )

    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")

else:
    st.info("👈 Please upload a CSV or Excel file in the sidebar to get started.")