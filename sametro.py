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
      with st.expander("👀 Preview Cleaned Raw Data"):
        st.dataframe(df.head())

      # Main transformed data view
      st.subheader("✨ Transformed & Mapped Data Preview")
      st.dataframe(transformed_df, use_container_width=True)

      # Download button for the processed data
      csv_data = transformed_df.to_csv(index=False).encode("utf-8")
      st.download_button(
          label="📥 Download Cleaned & Mapped Data as CSV",
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
      with st.expander("View all available columns in your file"):
        st.write(df.columns.tolist())

  except Exception as e:
    st.error(f"Error reading or processing the file: {e}")
else:
  st.info("👈 Upload a file in the sidebar to get started.")





