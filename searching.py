import requests
from bs4 import BeautifulSoup
import pycld2 as cld2
import re
#from googletrans import Translator
from collections import Counter
from datetime import datetime
import pytz
import streamlit as st
from urllib.parse import urlparse
import time
import random
import requests_cache


# Install cache for HTTP requests
requests_cache.install_cache('http_cache', expire_after=3600)


# Error handler function to streamline error handling
def error_handler(function, item, error_message):
    st.error(f"Error processing {function} for '{item}': {error_message}")
    return "Error", "Error"
    

def google_search(query, num_results=100, language="en"):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.183 Safari/537.36"
    }
    results = []
    start = 0  # Google uses `start` parameter for pagination

    while len(results) < num_results:
        search_url = f"https://www.google.com/search?q={query}&hl={language}&lr=lang_{language}&num=10&start={start}"
        try:
            # Make the HTTP request
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()

            # Parse the response with BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract links from search results
            result_divs = soup.find_all("div", class_="tF2Cxc")
            for div in result_divs:
                link_tag = div.find("a")
                if link_tag and link_tag["href"]:
                    results.append(link_tag["href"])
                    if len(results) >= num_results:  # Stop if we've reached the desired number
                        break

            # Update `start` for the next page
            start += 10  # Google paginates by increments of 10

            # Stop if no results are found on the current page
            if not result_divs:
                st.warning(f"Not enough results found for the query: {query}")
                break

            # Pause before the next request
            delay = random.uniform(2, 10) 
            time.sleep(delay)

        except requests.exceptions.RequestException as e:
            error_handler("google search", query, e)
            break  # Stop the loop if there's an error

    if results:
        st.info(f"Fetched {len(results)} results for the query: {query}")
    else:
        st.error(f"No results found for the query: {query}")
    return results



# Function to fetch title from a URL
def get_title(url):
    title = "No title available"
    try:
        # Add scheme if missing
        if not re.match(r'^https?://', url):
            url = 'https://' + url
        response = requests.get(url, timeout=5)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        # Try to get the title
        title = soup.title.string if soup.title else "No title available"
        title = re.sub(r'[\r\n]+', ' ', title.strip()) if title else "No title available"
    except requests.exceptions.RequestException as e:
        # Handle connection errors
        title = "Error"
        error_handler("get title", url, e)
    return title


# Function to fetch description from a URL
def get_description(url):
    description = "No description available"
    try:
        # Add scheme if missing
        if not re.match(r'^https?://', url):
            url = 'https://' + url
        response = requests.get(url, timeout=5)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        # Try to get the description
        description_tag = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        description = description_tag['content'] if description_tag else ""
        description = re.sub(r'[\r\n]+', ' ', description.strip()) if description else ""
    except requests.exceptions.RequestException as e:
        # Handle connection errors
        description = "Error"
        error_handler("get description", url, e)
    return description


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
        error_handler(detect_language, title, e)
        return ["unknown"]

# Helper function to combine title and description text
def combine_text(title, description):
    return (title or "").lower() + " " + (description or "").lower()

def translate_to_english(title, description):
    try:
        translator = Translator()
        # Translate the title
        title_translated_result = translator.translate(title, src='auto', dest='en')
        title_translated = title_translated_result.text if title_translated_result else title
        # Translate the description
        description_translated_result = translator.translate(description, src='auto', dest='en')
        description_translated = description_translated_result.text if description_translated_result else description
        return title_translated, description_translated
    except AttributeError as e:
        # Handle NoneType or missing attributes
        return f"Error translating title '{title}': {str(e)}"
    except Exception as e:
        # Catch all other exceptions
        return f"Error translating title '{title}': {str(e)}"


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
    #search_results = search(query, num_results, lang=language)
    search_results = google_search(query, num_results, language)
    classified_urls = []
    for result in search_results:
        parsed_url = urlparse(result)
        if homepage_only:
            if parsed_url.path not in ("", "/") or parsed_url.query or parsed_url.fragment:
                continue
            source = f"{query}"
        else:
            # Strip URL to domain or subdomain
            stripped_url = urlunparse((parsed_url.scheme, parsed_url.netloc, "", "", "", ""))
            source = f"{query} - root" if parsed_url.path in ("", "/") and not parsed_url.query and not parsed_url.fragment else f"{query} - page"
            result = stripped_url  # Replace result with stripped URL
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
def process_keywords(client, sheet_id, keywords, lang="en", inurl=False, limit=100, homepage=False):
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
        delay = random.uniform(30, 60.0)
        time.sleep(delay)
        try:
            # Perform searches
            homepage_urls = search_and_filter_urls(keyword, num_results=limit, language=lang, homepage_only=homepage)
            inurl_urls = []
            if inurl:
                inurl_urls = search_and_filter_urls(f"inurl:{keyword}", num_results=limit, language=lang, homepage_only=homepage)
            all_urls = homepage_urls + inurl_urls

            for url, source in all_urls:
                timestamp = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime("%Y-%m-%d %H:%M:%S")
                source = f"google search for '{source}'"
                try:
                    title = get_title(url)
                    description = get_description(url)
                    languages = detect_language(title, description)
                    score, details, good_count, bad_count = calculate_score(title, description, url, languages, good_keywords, bad_keywords)
                    row_data = [url, title, description, score, details, source, ", ".join(languages), good_count, bad_count, timestamp]

                    if score in ["A", "B"]:
                        rows_to_sure.append(row_data)
                    else:
                        rows_to_not_sure.append(row_data)

                except Exception as e:
                    st.error(f"Error processing URL '{url}': {e}")
                    error_row = [url, "Error", "Error", "", "Error", source, "", "", "", timestamp]
                    rows_to_not_sure.append(error_row)
                    
            # Update Google Sheets after processing the keyword
            update_google_sheets(rows_to_sure, rows_to_not_sure, sure_sheet, not_sure_sheet)
            st.success(f"Finished processing keyword: {keyword}")
        
        except Exception as e:
            st.error(f"Error processing keyword '{keyword}': {e}")


# Main function to process keywords and URLs
def process_urls(client, sheet_id, urls, source_name):
    keywords_sheet = client.open_by_key(st.secrets["keywords_id"]).worksheet("Keywords")
    sure_sheet = client.open_by_key(sheet_id).worksheet("Sure")
    not_sure_sheet = client.open_by_key(sheet_id).worksheet("Not Sure")
    good_keywords = [kw.lower() for kw in keywords_sheet.col_values(1)[1:]]  # Lowercase good keywords
    bad_keywords = [kw.lower() for kw in keywords_sheet.col_values(3)[1:]]  # Lowercase bad keywords
    
    rows_to_sure = []
    rows_to_not_sure = []

    for url in urls:
        timestamp = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime("%Y-%m-%d %H:%M:%S")
        source = source_name
        try:
            title = get_title(url)
            description = get_description(url)
            languages = detect_language(title, description)
            score, details, good_count, bad_count = calculate_score(title, description, url, languages, good_keywords, bad_keywords)
            row_data = [url, title, description, score, details, source, ", ".join(languages), good_count, bad_count, timestamp]

            if score in ["A", "B"]:
                rows_to_sure.append(row_data)
            else:
                rows_to_not_sure.append(row_data)

        except Exception as e:
            st.error(f"Error processing URL '{url}': {e}")
            error_row = [url, "Error", "Error", "", "Error", source, "", "", "", timestamp]
            rows_to_not_sure.append(error_row)
            
    # Update Google Sheets after processing the keyword
    update_google_sheets(rows_to_sure, rows_to_not_sure, sure_sheet, not_sure_sheet)

