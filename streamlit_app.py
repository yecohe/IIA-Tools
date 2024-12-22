import random
from google.oauth2 import service_account
from datetime import datetime
import pytz
import time
import requests
from bs4 import BeautifulSoup
import pycld2 as cld2
import re
from googletrans import Translator
from urllib.parse import urlparse
from collections import Counter
import re
import streamlit as st
import json




# Error handler function to streamline error handling
def error_handler(url, error_message):
    print(f"Error processing '{url}': {error_message}")
    return "Error", "Error"

# Function to fetch title and description from a URL
def get_title_and_description(url):
    try:
        # Add scheme if missing
        if not re.match(r'^https?://', url):
            url = 'https://' + url
        response = requests.get(url, timeout=5)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # Get title
        title = soup.title.string if soup.title else None

        # Get description (from meta tag)
        description_tag = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        description = description_tag['content'] if description_tag else None

        # Convert NoneType to string
        title = str(title) if title is not None else ""
        description = str(description) if description is not None else ""

        # Remove line breaks
        title = re.sub(r'[\r\n]+', ' ', title)
        description = re.sub(r'[\r\n]+', ' ', description)

        return title, description
    except Exception as e:
        return error_handler(url, e)

# Function to detect language using CLD2
def detect_language(title, description):
    combined_text = combine_text(title, description)
    try:
        # Check for Hebrew letters in the text
        if re.search(r'[\u0590-\u05FF]', combined_text):
            languages = ["HEBREW"]
        else:
            languages = []

        # Use CLD2 for further language detection
        is_reliable, _, details = cld2.detect(combined_text)
        if is_reliable:
            detected_languages = [detail[0] for detail in details if detail[0] != "Unknown"]
            languages.extend(detected_languages)
            languages = list(set(languages))  # Remove duplicates
            return languages
        else:
            return languages if languages else ["Unknown"]
    except Exception as e:
        return error_handler(title, e)
        return ["Unknown"]

# Helper function to combine title and description text
def combine_text(title, description):
    return (title or "").lower() + " " + (description or "").lower()

def translate_to_english(title, description):
    try:
        translator = Translator()
        title_translated = translator.translate(title, src='auto', dest='en').text
        description_translated = translator.translate(description, src='auto', dest='en').text
        return title_translated, description_translated
    except Exception as e:
        return error_handler(title, e)
        return title, description

# Function to calculate score based on good and bad keywords
def calculate_score(title, description, url, languages):
    if url.endswith(".il") or url.endswith(".il/"):
        return "A", "Hebrew / .il", 0, 0
    elif "HEBREW" in languages:
        return "A", "Hebrew / .il", 0, 0
    else:
        if languages and languages[0] != 'ENGLISH':
            title, description = translate_to_english(title, description)
        combined_text = combine_text(title, description)

        # Count occurrences of each word in the combined text
        word_counts = Counter(combined_text.split())

        # Sum up counts for good and bad keywords
        good_count = sum(word_counts[word] for word in good_keywords if word in word_counts)
        bad_count = sum(word_counts[word] for word in bad_keywords if word in word_counts)

        if good_count > 0:
            score = "B"
            details = f"Good keywords"
        else:
            score = "C"
            details = f"No good keywords"

        return score, details, good_count, bad_count

# Function to search and filter URLs based on query
def search_and_filter_urls(query, page_size, language, homepage_only=False):
    search_results = search(query, num=page_size, lang=language)
    classified_urls = []

    for result in search_results:
        parsed_url = urlparse(result)
        if homepage_only:
            if parsed_url.path not in ("", "/") or parsed_url.query or parsed_url.fragment:
                continue
            source = f"{query}"
        else:
            source = f"{query} - root" if parsed_url.path in ("", "/") and not parsed_url.query and not parsed_url.fragment else f"{query} - page"

        classified_urls.append((result, source))

    return classified_urls

# Function to update Google Sheets after processing each keyword
def update_google_sheets(rows_to_sure, rows_to_not_sure):
    if rows_to_sure:
        sure_sheet.append_rows(rows_to_sure, value_input_option='RAW')
    if rows_to_not_sure:
        not_sure_sheet.append_rows(rows_to_not_sure, value_input_option='RAW')

# Function to add headers to sheets
def add_headers(sheet, headers):
    sheet.clear()
    sheet.insert_row(headers, 1)

# Main function to process keywords and URLs
def process_keywords(lang="yi"):
    keywords = query_sheet.col_values(1)
    headers = ["URL", "Tier", "Details", "Source", "Good Keywords", "Bad Keywords", "Title", "Description", "Languages", "Timestamp"]
    #add_headers(sure_sheet, headers)
    #add_headers(not_sure_sheet, headers)

    for keyword in keywords:
        print(f"Processing keyword: {keyword}")
        rows_to_sure = []
        rows_to_not_sure = []

        try:
            # Perform searches
            homepage_urls = search_and_filter_urls(keyword, page_size=10, language=lang, homepage_only=True)
            inurl_urls = search_and_filter_urls(f"inurl:{keyword}", page_size=10, language=lang, homepage_only=True)

            all_urls = homepage_urls + inurl_urls

            for url, source in all_urls:
                try:
                    title, description = get_title_and_description(url)
                    languages = detect_language(title, description)
                    score, details, good_count, bad_count = calculate_score(title, description, url, languages)

                    timestamp = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime("%Y-%m-%d %H:%M:%S")
                    row_data = [url, score, details, source, good_count, bad_count, title, description, ", ".join(languages), timestamp]

                    if score in ["A", "B"]:
                        rows_to_sure.append(row_data)
                    else:
                        rows_to_not_sure.append(row_data)

                except Exception as e:
                    print(f"Error processing URL '{url}': {e}")
                    error_row = [url, "Error", "Error", source, "", "", "", "", "", ""]
                    rows_to_not_sure.append(error_row)

        except Exception as e:
            print(f"Error processing keyword '{keyword}': {e}")

        # Update Google Sheets after processing the keyword
        update_google_sheets(rows_to_sure, rows_to_not_sure)
        print(f"Finished processing keyword: {keyword}")



# Page configuration
st.set_page_config(page_title="Internet Archive Tool", layout="centered")

# Ask for credentials file
st.title("Upload Credentials File")
credentials_file = st.file_uploader("Please upload your OAuth 2.0 JSON credentials file", type="json")

if credentials_file is not None:
    try:
        # Define the scope for Google API
        scope = [
            "https://spreadsheets.google.com/feeds", 
            "https://www.googleapis.com/auth/spreadsheets", 
            "https://www.googleapis.com/auth/drive"
        ]

        # Read and process the credentials file
        credentials = service_account.Credentials.from_json_keyfile_dict(
            json.loads(credentials_file.read()),
            scopes=scope
        )
        client = gspread.authorize(credentials)
        
        st.success("Credentials file uploaded and authenticated successfully!")

        # Title
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
            keywords_list = st.text_area(
                "Keywords List (separate by commas)",
                help="Enter the keywords you want to search for. Use commas to separate multiple keywords."
            )

            # Language input
            language = st.text_input(
                "Language", 
                value="English", 
                help="Enter the language for the search."
            )

            # Include inurl checkbox
            include_inurl = st.checkbox(
                "Include 'inurl' in the search",
                value=False,
                help="Check this box if you want to include 'inurl' in the search results."
            )

            # Submit button
            submit_button = st.form_submit_button("Add to Archive")

        # Handle form submission
        if submit_button:
            # Validate inputs
            if not keywords_list.strip():
                st.error("Please provide at least one keyword.")
            else:
                # Process and display inputs
                st.success("Keywords successfully added to the archive queue!")
                st.write("### Search Details")
                st.write(f"**Keywords List:** {keywords_list}")
                st.write(f"**Language:** {language}")
                st.write(f"**Include 'inurl':** {'Yes' if include_inurl else 'No'}")

                # Simulate adding to the archive (Replace with actual backend logic)
                st.info("The URLs are being processed and added to the archive.")
    except Exception as e:
        st.error(f"Error processing credentials file: {e}")
else:
    st.warning("Please upload the credentials file to proceed.")
