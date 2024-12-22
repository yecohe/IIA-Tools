import streamlit as st
import json
from google.oauth2 import service_account
import gspread
import keywords_tool
import wikidata_tool
import filter_tool


# Global title
st.title("Israeli Internet Archive")

# Sidebar: Upload Credentials File
with st.sidebar:
    st.subheader("Upload Credentials File")
    credentials_file = st.file_uploader("Please upload your OAuth 2.0 JSON credentials file", type="json")

# Initialize app options and flag
apps = {}
authenticated = False

# Handle credentials upload
if credentials_file is not None:
    try:
        # Define the scope for Google API
        scope = [
            "https://spreadsheets.google.com/feeds", 
            "https://www.googleapis.com/auth/spreadsheets", 
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Read credentials
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(credentials_file.read().decode("utf-8")), 
            scopes=scope
        )
        
        # Authenticate with Google Sheets
        client = gspread.authorize(credentials)
        st.sidebar.success("Credentials uploaded and authenticated successfully!")
        authenticated = True

    except Exception as e:
        st.sidebar.error(f"Error processing credentials: {e}")


# Menu Logic
if authenticated:
    st.sidebar.subheader("Menu")
    apps = {
        "Keywords Search Tool": keywords_tool.run(client),
        "Wikidata Tool": wikidata_tool.run,
        "Automatic Filter Tool": filter_tool.run,
    }
    choice = st.sidebar.radio("Select an app", list(apps.keys()))
    apps[choice]()  # Render the selected app
else:
    st.warning("Please upload the credentials file to access the tools.")


















