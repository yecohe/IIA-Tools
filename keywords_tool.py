import streamlit as st
from searching import process_keywords

def run(client):
    # Main interface for keyword processing (only accessible if credentials are uploaded)
    st.subheader("Keywords Search Tool")
    st.write("This tool searches google for keywords. The results are here: https://docs.google.com/spreadsheets/d/1qqupnQ5nSVRRF04giVNzq8NaSdaiTVrgXc2ISH5Ib3Q/")

    # Language options and descriptions
    language_options = {
        "English (en)": "en",
        "Hebrew (he)": "he",
        "Arabic (ar)": "ar",
        "French (fr)": "fr",
        "German (de)": "de",
        "Italian (it)": "it",
        "Portuguese (Brazil) (pt-BR)": "pt-BR"
    }
    
    # Inputs for Keywords Search
    with st.form("keywords_search_form"):
        st.subheader("Keywords Search")

        # Keywords input
        keywords_query = st.text_area(
            "Keywords List (separate by commas)",
            help="Enter the keywords you want to search for. Use commas to separate multiple keywords."
        )

        # Language dropdown
        selected_language = st.selectbox(
            "Select Language for Search",
            options=list(language_options.keys()),
            help="Choose the language for the keyword search."
        )
        language = language_options[selected_language]  # Get the language code

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

            st.write("### Search Details")
            st.write(f"**Keywords List:** {keywords_query}")
            st.write(f"**Language:** {language}")
            st.write(f"**Include 'inurl':** {'Yes' if include_inurl else 'No'}")
            sheet_id = client.open_by_key(st.secrets["google_id"]).worksheet("Keywords")
            process_keywords(client, sheet_id, keywords_query, lang=language, inurl=include_inurl, limit=100)
            st.info("The URLs are being processed and added to the file.")
