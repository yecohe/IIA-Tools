import streamlit as st
import pandas as pd
from searching import process_urls

def run(client):
    # Main interface for URL filtering
    st.write(
        "This tool processes a list of URLs for automatic filtering. The results are saved [here](https://docs.google.com/spreadsheets/d/1FH2IBeA4HePPBt6PopWTN3QXemxXc5EKcEH3_C5UP4c/)."
    )

    # Inputs for URL Filtering
    with st.form("url_filter_form"):

        # Option to insert URLs manually
        urls_input = st.text_area("Insert a list of URLs (one per line):")

        # Option to upload a file
        uploaded_file = st.file_uploader("Or upload a file (CSV / TXT / Excel):", type=["csv", "txt", "xlsx"])

        # Name for the source
        source_name = st.text_input("List Name:", placeholder="E.g., 'My URL List'")

        # Submit button
        submit_button = st.form_submit_button("Filter")

    # Handle form submission
    if submit_button:
        # Validate inputs
        urls = []

        if uploaded_file:
            # Process uploaded file
            file_type = uploaded_file.name.split('.')[-1].lower()
            try:
                if file_type == "csv":
                    urls = uploaded_file.read().decode("utf-8").splitlines()
                elif file_type == "txt":
                    urls = uploaded_file.read().decode("utf-8").splitlines()
                elif file_type == "xlsx":
                    df = pd.read_excel(uploaded_file, engine='openpyxl')
                    urls = df.iloc[:, 0].dropna().tolist()  # Assuming URLs are in the first column
                else:
                    st.error("Unsupported file type. Please upload a CSV, TXT, or Excel file.")
            except Exception as e:
                st.error(f"Error reading file: {e}")
        elif urls_input.strip():
            # Process manual input
            urls = urls_input.strip().splitlines()
        else:
            st.error("Please provide URLs either by input or file upload.")

        # Validate source name
        if not source_name:
            st.error("Please provide a name for the list.")
        elif not urls:
            st.error("No valid URLs provided.")
        else:
            # Process URLs
            sheet_id = st.secrets["filter_id"]
            st.success(f"The URLs from '{source_name}' are being processed...")
            process_urls(client, sheet_id, urls, source_name)
