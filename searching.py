import requests
from bs4 import BeautifulSoup
import pycld2 as cld2
import re
from googletrans import Translator
from collections import Counter
#from googlesearch import search
from datetime import datetime
import pytz
import streamlit as st
from urllib.parse import urlparse

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
            languages = ["hebrew"]
        else:
            languages = []

        # Use CLD2 for further language detection
        is_reliable, _, details = cld2.detect(combined_text)
        if is_reliable:
            detected_languages = [detail[0].lower() for detail in details if detail[0] != "Unknown"]
            languages.extend(detected_languages)
            languages = list(set(languages))  # Remove duplicates
            return languages
        else:
            return [lang.lower() for lang in languages] if languages else ["unknown"]
    except Exception as e:
        error_handler(title, e)
        return ["unknown"]

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
def calculate_score(title, description, url, languages, good_keywords, bad_keywords):
    if url.endswith(".il") or url.endswith(".il/"):
        return "A", "Hebrew / .il", 0, 0
    elif "hebrew" in languages:
        return "A", "Hebrew / .il", 0, 0
    else:
        if languages and languages[0] != 'english':
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
def search_and_filter_urls(query, num_results=100, language="en", homepage_only=False):
    search_results = search(query, num_results, lang=language)
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
def update_google_sheets(rows_to_sure, rows_to_not_sure, sure_sheet, not_sure_sheet):
    if rows_to_sure:
        sure_sheet.append_rows(rows_to_sure, value_input_option='RAW')
    if rows_to_not_sure:
        not_sure_sheet.append_rows(rows_to_not_sure, value_input_option='RAW')

# Function to add headers to sheets
def check_and_add_headers(sheet):
    headers = ["URL", "Title", "Description", "Tier", "Details", "Source","Languages", "Good Keywords", "Bad Keywords" , "Timestamp"]
    # Check if the sheet has any data (excluding the header row)
    if len(sheet.get_all_values()) <= 1:  # Only the header exists
        sheet.insert_row(headers, 1)

# Main function to process keywords and URLs
def process_keywords(client, sheet_id, keywords, lang="en", inurl=False, limit=100):
    query_sheet = client.open_by_key(sheet_id).worksheet("Keywords")
    keywords_sheet = client.open_by_key(st.secrets["keywords_id"]).worksheet("Keywords")
    sure_sheet = client.open_by_key(sheet_id).worksheet("Sure")
    not_sure_sheet = client.open_by_key(sheet_id).worksheet("Not Sure")
    good_keywords = [kw.lower() for kw in keywords_sheet.col_values(1)[1:]]  # Lowercase good keywords
    bad_keywords = [kw.lower() for kw in keywords_sheet.col_values(3)[1:]]  # Lowercase bad keywords
    
    for keyword in keywords:
        st.success(f"Processing keyword: {keyword}")
        check_and_add_headers(sure_sheet)
        check_and_add_headers(not_sure_sheet)
        rows_to_sure = []
        rows_to_not_sure = []
        
        try:
            # Perform searches
            homepage_urls = search_and_filter_urls(keyword, num_results=limit, language=lang, homepage_only=True)
            inurl_urls = []
            if inurl:
                inurl_urls = search_and_filter_urls(f"inurl:{keyword}", num_results=limit, language=lang, homepage_only=True)
            all_urls = homepage_urls + inurl_urls

            for url, source in all_urls:
                try:
                    title, description = get_title_and_description(url)
                    languages = detect_language(title, description)
                    score, details, good_count, bad_count = calculate_score(title, description, url, languages, good_keywords, bad_keywords)
                    timestamp = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime("%Y-%m-%d %H:%M:%S")
                    source = f"google search for '{source}'"
                    row_data = [url, title, description, score, details, source, ", ".join(languages), good_count, bad_count, timestamp]

                    if score in ["A", "B"]:
                        rows_to_sure.append(row_data)
                    else:
                        rows_to_not_sure.append(row_data)

                except Exception as e:
                    st.error(f"Error processing URL '{url}': {e}")
                    error_row = [url, "Error", "Error", source, "", "", "", "", "", ""]
                    rows_to_not_sure.append(error_row)
                    
            # Update Google Sheets after processing the keyword
            update_google_sheets(rows_to_sure, rows_to_not_sure, sure_sheet, not_sure_sheet)
            st.success(f"Finished processing keyword: {keyword}")
        
        except Exception as e:
            st.error(f"Error processing keyword '{keyword}': {e}")

# Main function to process keywords and URLs
def process_urls(client, sheet_id, urls, source_name, limit=100):
    query_sheet = client.open_by_key(sheet_id).worksheet("Keywords")
    keywords_sheet = client.open_by_key(st.secrets["keywords_id"]).worksheet("Keywords")
    sure_sheet = client.open_by_key(sheet_id).worksheet("Sure")
    not_sure_sheet = client.open_by_key(sheet_id).worksheet("Not Sure")
    good_keywords = [kw.lower() for kw in keywords_sheet.col_values(1)[1:]]  # Lowercase good keywords
    bad_keywords = [kw.lower() for kw in keywords_sheet.col_values(3)[1:]]  # Lowercase bad keywords
    
    check_and_add_headers(sure_sheet)
    check_and_add_headers(not_sure_sheet)
    rows_to_sure = []
    rows_to_not_sure = []

    for url in urls:
        try:
            title, description = get_title_and_description(url)
            languages = detect_language(title, description)
            score, details, good_count, bad_count = calculate_score(title, description, url, languages, good_keywords, bad_keywords)
            timestamp = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime("%Y-%m-%d %H:%M:%S")
            source = source_name
            row_data = [url, title, description, score, details, source, ", ".join(languages), good_count, bad_count, timestamp]

            if score in ["A", "B"]:
                rows_to_sure.append(row_data)
            else:
                rows_to_not_sure.append(row_data)

        except Exception as e:
            st.error(f"Error processing URL '{url}': {e}")
            error_row = [url, "Error", "Error", source, "", "", "", "", "", ""]
            rows_to_not_sure.append(error_row)
            
    # Update Google Sheets after processing the keyword
    update_google_sheets(rows_to_sure, rows_to_not_sure, sure_sheet, not_sure_sheet)
    st.success(f"Finished processing keyword: {keyword}")

