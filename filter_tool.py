import streamlit as st
from searching import process_keywords

def run(client):
    # Main interface for keyword processing (only accessible if credentials are uploaded)
    st.subheader("Filter Tool")
    st.write("This tool gets a list of urls and check their info for automatic filtering. The results are here: https://docs.google.com/spreadsheets/d/1FH2IBeA4HePPBt6PopWTN3QXemxXc5EKcEH3_C5UP4c/")
  
    # Inputs for Keywords Search
    with st.form("keywords_search_form"):
        st.subheader("Keywords Search")


        # Submit button
        submit_button = st.form_submit_button("Search")

    # Handle form submission
    if submit_button:
        # Validate inputs
        if not keywords_query:
            st.error("Please provide at least one keyword.")
        else:

            
            sheet_id = client.open_by_key(st.secrets["filter_id"]).worksheet("Keywords")
            process_keywords(client, sheet_id, keywords_query, lang=language, inurl=include_inurl, limit=100)
            st.info("The URLs are being processed and added to the file.")
