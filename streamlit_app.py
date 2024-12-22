import gspread
from google.oauth2 import service_account
import streamlit as st
from apps import keywords_search, wikidata_tool, automatic_filter

# Global title
st.title("Israeli Internet Archive")

# Sidebar: Upload Credentials File
with st.sidebar:
    st.subheader("Upload Credentials File")
    credentials_file = st.file_uploader("Please upload your OAuth 2.0 JSON credentials file", type="json")

# Authentication
authenticated = authenticate_user(credentials_file)

# Menu Logic
if authenticated:
    st.sidebar.subheader("Menu")
    apps = {
        "Keywords Search Tool": keywords_search.run,
        "Wikidata Tool": wikidata_tool.run,
        "Automatic Filter Tool": automatic_filter.run,
    }
    choice = st.sidebar.radio("Select an app", list(apps.keys()))
    apps[choice]()  # Render the selected app
else:
    st.warning("Please upload the credentials file to access the tools.")


















