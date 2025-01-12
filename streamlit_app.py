import streamlit as st
import json
from google.oauth2 import service_account
import gspread
import keywords_tool
import wikidata_tool
import filter_tool
import split_tool
from streamlit_option_menu import option_menu

# Initialize app options and authentication flag
apps = {}
authenticated = False
client = None
selected_app_name = None  # Initialize variable outside the conditional blocks

# Sidebar Logic
with st.sidebar:
    st.header("Israeli Internet Archive")

    # Conditional Rendering: Show upload UI if not authenticated
    if not authenticated:
        st.subheader("Upload Credentials File")
        credentials_file = st.file_uploader("Please upload your JSON credentials file", type="json")

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
                st.success("Credentials uploaded and authenticated successfully!")
                authenticated = True

            except Exception as e:
                st.error(f"Error processing credentials: {e}")
    else:
        # Show the menu after successful authentication
        selected_app_name = option_menu(
            "Select Tool",
            options=["Keywords Search Tool", "Automatic Filter Tool", "Split URL Tool", "Wikidata Tool"],
            icons=["search", "filter", "link", "database"],  # Customize icons
            menu_icon="tools",
            default_index=0,
            orientation="vertical"  # Sidebar menu
        )

# Define and execute app logic only if authenticated
if authenticated:
    # Define apps
    apps = {
        "Keywords Search Tool": keywords_tool.run if callable(keywords_tool.run) else None,        
        "Automatic Filter Tool": filter_tool.run if callable(filter_tool.run) else None,
        "Split URL Tool": split_tool.run if callable(split_tool.run) else None,
        "Wikidata Tool": wikidata_tool.run if callable(wikidata_tool.run) else None,
    }
    apps = {k: v for k, v in apps.items() if v}  # Filter out invalid entries

    # Render the selected app
    if selected_app_name:
        app_function = apps.get(selected_app_name)
        if callable(app_function):
            st.title(selected_app_name)
            app_function(client)  # Pas
