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
    
    # Define apps
    apps = {
        "Keywords Search Tool": keywords_tool.run(client) if callable(keywords_tool.run) else None,
        "Wikidata Tool": wikidata_tool.run(client) if callable(wikidata_tool.run) else None,
        "Automatic Filter Tool": filter_tool.run(client) if callable(filter_tool.run) else None,
    }
    apps = {k: v for k, v in apps.items() if v}  # Filter out invalid entries

    # Initialize session state for the selected app
    if "selected_app" not in st.session_state:
        st.session_state.selected_app = None

    # Create buttons for each app
    for app_name, app_function in apps.items():
        if st.sidebar.button(app_name):
            st.session_state.selected_app = app_name  # Set the selected app in session state

    # Display the selected app
    selected_app_name = st.session_state.selected_app
    if selected_app_name:
        app_function = apps[selected_app_name]
        if callable(app_function):
            st.title(selected_app_name)
            app_function()  # Render the selected app
        else:
            st.error(f"The app '{selected_app_name}' is not callable.")
    else:
        st.info("Please select an app to get started.")

else:
    st.warning("Please upload the credentials file to access the tools.")
















