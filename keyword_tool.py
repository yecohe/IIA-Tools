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

            st.write("### Search Details")
            st.write(f"**Keywords List:** {keywords_query}")
            st.write(f"**Language:** {language}")
            st.write(f"**Include 'inurl':** {'Yes' if include_inurl else 'No'}")
            process_keywords(client, keywords_query, lang=language, inurl=include_inurl, limit=100)
            st.info("The URLs are being processed and added to the file.")
else:
    st.warning("Please upload the credentials file to proceed with keyword search.")
