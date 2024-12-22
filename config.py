import gspread
from google.oauth2 import service_account
import json

# Google Sheets configuration
SCOPE = [
    "https://spreadsheets.google.com/feeds", 
    "https://www.googleapis.com/auth/spreadsheets", 
    "https://www.googleapis.com/auth/drive"
]


# Authenticate and authorize Google Sheets
def authenticate_google_sheets(credentials_file):
    try:
        # Process credentials and authenticate
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(credentials_file.read().decode('utf-8')),  
            scopes=SCOPE
        )
        
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        raise Exception(f"Error authenticating Google Sheets: {e}")

