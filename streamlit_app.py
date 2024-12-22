import random
import gspread
from google.oauth2 import service_account
from datetime import datetime
import pytz
import time
import requests
import re
from collections import Counter
import streamlit as st
import json
from search import process_keywords


# Error handler function to streamline error handling
def error_handler(url, error_message):
    st.error(f"Error processing '{url}': {error_message}")
    return "Error", "Error"

# Page configuration
st.set_page_config(page_title="Internet Archive Tool", layout="wide")

# Sidebar configuration for credentials
with st.sidebar:
    st.title("Upload Credentials File")
    credentials_file = st.file_uploader("Please upload your OAuth 2.0 JSON credentials file", type="json")

    # Check if the credentials file is uploaded
    if credentials_file is not None:
        try:
            # Define the scope for Google API
            scope = [
                "https://spreadsheets.google.com/feeds", 
                "https://www.googleapis.com/auth/spreadsheets", 
                "https://www.googleapis.com/auth/drive"
            ]

            # Read and process the credentials file
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(credentials_file.read().decode('utf-8')),  
                scopes=scope
            )
            client = gspread.authorize(credentials)
            
            # Open the Google Sheet by ID
            keywords_sheet = client.open_by_key(st.secrets["keywords_id"]).worksheet("Keywords")
            sure_sheet = client.open_by_key(st.secrets["filter_id"]).worksheet("Sure")
            not_sure_sheet = client.open_by_key(st.secrets["filter_id"]).worksheet("Not Sure")
            good_keywords = [kw.lower() for kw in keywords_sheet.col_values(1)[1:]]  # Lowercase good keywords
            bad_keywords = [kw.lower() for kw in keywords_sheet.col_values(3)[1:]]  # Lowercase bad keywords
            
            st.success("Credentials file uploaded and authenticated successfully!")

        except Exception as e:
            st.error(f"Error processing credentials file: {e}")
    else:
        st.warning("Please upload the credentials file to proceed.")

# Main interface for keyword processing (only accessible if credentials are uploaded)
if credentials_file is not None:
    st.title("Internet Archive - Keywords Search Tool")

    # Description
    st.write(
        "Use this tool to add URLs to the internet archive based on your keyword searches. "
        "Fill in the details below to customize your search."
    )

    # Inputs for Keywords Search
    with st.form("keywords_search_form"):
        st.subheader("Keywords Search")

        # Keywords input
        keywords_query = st.text_area(
            "Keywords List (separate by commas)",
            help="Enter the keywords you want to search for. Use commas to separate multiple keywords."
        )

        # Language input
        language = st.text_input(
            "Language", 
            value="en", 
            help="Enter the language for the search."
        )

        # Include inurl checkbox
        include_inurl = st.checkbox(
            "Include 'inurl' in the search",
            value=False,
            help="Check this box if you want to include 'inurl' in the search results."
        )

        # Submit button
        submit_button = st.form_submit_button("Search")

    # Handle form submission
    if submit_button:
        # Validate inputs
        if not keywords_query:
            st.error("Please provide at least one keyword.")
        else:
            keywords_query = keywords_query.split(",")  # Split by commas
            keywords_query = [kw.strip() for kw in keywords_query]  # Remove extra spaces around words
            process_keywords(keywords_query, lang=language, inurl=include_inurl, limit=100)
            # Process and display inputs
            st.write("### Search Details")
            st.write(f"**Keywords List:** {keywords_query}")
            st.write(f"**Language:** {language}")
            st.write(f"**Include 'inurl':** {'Yes' if include_inurl else 'No'}")
            st.success("Keywords successfully added to the archive queue!")

            # Simulate adding to the archive (Replace with actual backend logic)
            st.info("The URLs are being processed and added to the file.")
else:
    st.warning("Please upload the credentials file to proceed with keyword search.")
