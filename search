import requests
from bs4 import BeautifulSoup
import pycld2 as cld2
import re
from googletrans import Translator
from collections import Counter
from googlesearch import search
from datetime import datetime
import pytz

# Fetch title and description from a URL
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

# Detect language of title and description
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

# Combine title and description into a single string for processing
def combine_text(title, description):
    return (title or "").lower() + " " + (description or "").lower()

# Translate content to English
def translate_to_english(title, description):
    try:
        translator = Translator()
        title_translated = translator.translate(title, src='auto', dest='en').text
        description_translated = translator.translate(description, src='auto', dest='en').text
        return title_translated, description_translated
    except Exception as e:
        return error_handler(title, e)

# Calculate keyword score
def calculate_score(title, description, url, languages, good_keywords, bad_keywords):
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

# Search and filter URLs based on query
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

# Update Google Sheets after processing
def update_google_sheets(rows_to_sure, rows_to_not_sure, sure_sheet, not_sure_sheet):
    if rows_to_sure:
        sure_sheet.append_rows(rows_to_sure, value_input_option='RAW')
    if rows_to_not_sure:
        not_sure_sheet.append_rows(rows_to_not_sure, value_input_option='RAW')

# Add headers to sheets if they don't exist
def check_and_add_headers(sheet):
    headers = ["URL", "Title", "Description", "Tier", "Details", "Source", "Languages", "Good Keywords", "Bad Keywords", "Timestamp"]
    if len(sheet.get_all_values()) <= 1:  # Only the header exists
        sheet.insert_row(headers, 1)
