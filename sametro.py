import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()
def get_gdrive_credentials():
    # 1. Try loading from Streamlit Cloud secrets first
    try:
        if "gcp_service_account" in st.secrets:
            credentials_dict = dict(st.secrets["gcp_service_account"])
            return service_account.Credentials.from_service_account_info(
                credentials_dict, scopes=["https://www.googleapis.com/auth/drive"]
            )
    except Exception:
        pass

    # 2. Fall back to local .env file / environment variable path
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path and os.path.exists(credentials_path):
        return service_account.Credentials.from_service_account_file(
            credentials_path, scopes=["https://www.googleapis.com/auth/drive"]
        )
    
    raise FileNotFoundError(
        "Google Service Account credentials not found. Please configure st.secrets on Streamlit Cloud or your local .env file."
    )

st.set_page_config(
    page_title="Sameforce Data Extractor & Mapper", page_icon="📊", layout="wide"
)

st.title("Sametro Field Converter")
st.write("My custom app for converting downloaded CreditHive data into Sameforce standard format")
st.divider()


#let's uploadCreditHive data
with st.sidebar:
  st.header("⚙️ Configuration")
  uploaded_file = st.file_uploader(
      "Upload your data file (CSV or Excel)", type=["csv", "xlsx", "xls"]
  )
  # upload csv to my drive account
  gdrive_enabled = st.checkbox("Enable Google Drive Backup")
  gdrive_file_name = st.text_input(
      "Raw File Name in Drive", value="raw_uploaded_data.csv"
  )
  gdrive_folder_id = st.text_input(
      "Google Drive Folder ID (Optional)",
      value="",
      help="Leave blank to save in the Service Account's root directory.",
  )

# --- MAIN AREA LOGIC ---
if uploaded_file is not None:
  try:
    # Read CSV or Excel depending on the file extension
    if uploaded_file.name.endswith(".csv"):
      df = pd.read_csv(uploaded_file)
    else:
      df = pd.read_excel(uploaded_file)

    st.success(
        f"Successfully loaded **{uploaded_file.name}**! ({df.shape[0]} rows,"
        f" {df.shape[1]} columns)"
    )

    # --- STEP 1: UPLOAD RAW DATA TO GOOGLE DRIVE ---
    if gdrive_enabled:
      st.subheader("☁️ Cloud Archive Step: Raw Data Backup")
      if st.button("🚀 Upload Raw Data to Google Drive"):
        try:
          # Load credentials securely from Streamlit secrets
          credentials_dict = dict(st.secrets["gcp_service_account"])
          creds = service_account.Credentials.from_service_account_info(
              credentials_dict, scopes=["https://www.googleapis.com/auth/drive"]
          )

          service = build("drive", "v3", credentials=creds)

          # Convert original raw dataframe to CSV byte stream
          raw_csv_string = df.to_csv(index=False)
          fh = io.BytesIO(raw_csv_string.encode("utf-8"))
          media = MediaIoBaseUpload(fh, mimetype="text/csv", resumable=True)

          file_metadata = {"name": gdrive_file_name}
          if gdrive_folder_id.strip():
            file_metadata["parents"] = [gdrive_folder_id.strip()]

          # Execute upload of raw data
          file = (
              service.files()
              .create(body=file_metadata, media_body=media, fields="id")
              .execute()
          )
          st.success(
              "✅ Raw data successfully backed up to Google Drive! File ID:"
              f" `{file.get('id')}`"
          )
        except KeyError:
          st.error(
              "Missing `gcp_service_account` secret configuration in Streamlit"
              " secrets."
          )
        except Exception as e:
          st.error(f"Failed to upload raw data to Google Drive: {e}")
      st.divider()

    # --- STEP 2: DATA TRANSFORMATION & MAPPING ---
    # Clean columns: lowercase, replace spaces and hyphens with underscores
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )

    # Define exact columns of interest and their target rename mapping
    column_mapping = {
        "agent_username": "agent_id",
        "customer_full_name": "customer_name",
        "device_id": "device_id",
        "saleorder_device_id": "order_id",
        "device": "device_name",
        "order_started_on": "order_date",
        "agent_name": "agent_name",
    }

    ordered_sources = [
        col for col in column_mapping.keys() if col in df.columns
    ]

    if ordered_sources:
      # Extract and rename columns preserving the exact specified order
      transformed_df = df[ordered_sources].rename(columns=column_mapping)

      # Raw data preview toggle
      with st.expander("👀 Preview Cleaned Raw Data"):
        st.dataframe(df.head())

      # Main transformed data view
      st.subheader("✨ Transformed & Mapped Data Preview")
      st.dataframe(transformed_df, use_container_width=True)

      st.divider()

      # --- STEP 3: LOCAL DOWNLOAD FOR EXTRACTED DATA ---
      st.subheader("📥 Local Download")
      csv_data = transformed_df.to_csv(index=False).encode("utf-8")
      st.download_button(
          label="📥 Download Extracted & Cleaned Data as CSV",
          data=csv_data,
          file_name="extracted_and_mapped_data.csv",
          mime="text/csv",
      )

      # Check if any expected columns were missing
      missing_cols = [
          orig for orig in column_mapping.keys() if orig not in df.columns
      ]
      if missing_cols:
        st.warning(
            f"⚠️ Note: The following expected columns were not found in your"
            f" file and were skipped: `{missing_cols}`"
        )
    else:
      st.error(
          "❌ None of the expected columns of interest were found in your"
          " file. Please check your column headers."
      )

  except Exception as e:
    st.error(f"Error reading or processing the file: {e}")
else:
  st.info("👈 Upload a file in the sidebar to get started.")





