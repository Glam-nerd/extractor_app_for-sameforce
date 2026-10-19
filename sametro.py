import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import streamlit as st
import pandas as pd

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
  gdrive_enabled = st.checkbox("Enable direct upload to Google Drive")
  gdrive_file_name = st.text_input(
      "Google Drive File Name", value="cleaned_extracted_data.csv"
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

    # Continue sidebar controls once the file is loaded
    with st.sidebar:
      st.success(
          f"Loaded **{uploaded_file.name}**! ({df.shape[0]} rows,"
          f" {df.shape[1]} cols)"
      )
      st.divider()

    # replace any space in-between column headers with underscores
      df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )

    # extract only the following columns from the data
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
      with st.expander("Preview Cleaned Raw Data"):
        st.dataframe(df.head())

      # Main transformed data view
      st.subheader("✨ Transformed & Mapped Data Preview")
      st.dataframe(transformed_df, use_container_width=True)
      st.divider()
      col1, col2 = st.columns(2)

      # Download button for the processed data (local)
      with col1:
        st.subheader("📥 Local Download")
        csv_data = transformed_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Cleaned & Mapped Data as CSV",
            data=csv_data,
            file_name="extracted_and_mapped_data.csv",
            mime="text/csv",
        )
        # Option B: Google Drive Upload Button
      with col2:
        st.subheader("☁️ Google Drive Save")
        if gdrive_enabled:
          if st.button("🚀 Upload to Google Drive"):
            try:
              # Load credentials securely from Streamlit secrets
              credentials_dict = dict(st.secrets["gcp_service_account"])
              creds = service_account.Credentials.from_service_account_info(
                  credentials_dict,
                  scopes=["https://www.googleapis.com/auth/drive"],
              )

              # Build Drive API client
              service = build("drive", "v3", credentials=creds)

              # Convert dataframe to CSV byte stream
              csv_string = transformed_df.to_csv(index=False)
              fh = io.BytesIO(csv_string.encode("utf-8"))
              media = MediaIoBaseUpload(
                  fh, mimetype="text/csv", resumable=True
              )

              file_metadata = {"name": gdrive_file_name}
              if gdrive_folder_id.strip():
                file_metadata["parents"] = [gdrive_folder_id.strip()]

              # Execute upload
              file = (
                  service.files()
                  .create(body=file_metadata, media_body=media, fields="id")
                  .execute()
              )

              st.success(
                  "Successfully uploaded to Google Drive! File ID:"
                  f" `{file.get('id')}`"
              )

            except KeyError:
              st.error(
                  "Missing `gcp_service_account` secret configuration in"
                  " Streamlit secrets."
              )
            except Exception as e:
              st.error(f"Failed to upload to Google Drive: {e}")
        else:
          st.info(
              "Check 'Enable direct upload to Google Drive' in the sidebar to"
              " configure cloud saving."
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
      with st.expander("View all available columns in your file"):
        st.write(df.columns.tolist())

  except Exception as e:
    st.error(f"Error reading or processing the file: {e}")
else:
  st.info("👈 Upload a file in the sidebar to get started.")





