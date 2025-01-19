import streamlit as st
from SPARQLWrapper import SPARQLWrapper, JSON
from datetime import datetime
import pytz

# Error handler function to streamline error handling
def error_handler(function, item, error_message):
    st.error(f"Error processing {function} for '{item}': {error_message}")
    return "Error", "Error"

# Function to convert ID (e.g., "P27") to Label (e.g., "country of citizenship")
def id_to_label(wikidata_id):
    try:
        sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
        sparql.setQuery(f"""
        SELECT ?label WHERE {{
            wd:{wikidata_id} rdfs:label ?label.
            FILTER(LANG(?label) = "en")
        }}
        """)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        if results["results"]["bindings"]:
            return results["results"]["bindings"][0]["label"]["value"]
        else:
            return wikidata_id
    except Exception as e:
        error_handler("id to label", url, e)
        return wikidata_id

# Function to convert Label (e.g., "country of citizenship") to ID (e.g., "P27")
def label_to_id(label):
    try:
        sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
        sparql.setQuery(f"""
        SELECT ?entity WHERE {{
            ?entity rdfs:label "{label}"@en.
            FILTER(STRSTARTS(STR(?entity), "http://www.wikidata.org/entity/"))  # Exclude non-Wikidata entities
        }}
        """)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
    
        if results["results"]["bindings"]:
            return results["results"]["bindings"][0]["entity"]["value"].split("/")[-1]
        else:
            return None  # Return None if no matching ID is found
    except Exception as e:
        error_handler("label to id", label, str(e))
        return None


# Query Wikidata dynamically, including subclasses and handling empty results
def query_wikidata(property_id, value_id, language="en"):
    if not property_id or not value_id:
        return {"error": "Property ID and Value ID must be provided."}  
    try:
        query = f"""
        SELECT DISTINCT ?item ?itemLabel ?website WHERE {{
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{language}". }}
          {{
            SELECT DISTINCT ?item WHERE {{
              ?item p:{property_id} ?statement0.
              ?statement0 (ps:{property_id}/(wdt:P279*)) wd:{value_id}.
            }}
          }}
          OPTIONAL {{ ?item wdt:P856 ?website }}  # Personal website
        }}
        """
        sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        
        # Check if results are empty
        if results.get("results", {}).get("bindings"):
            return results
        else:
            return {"error": "No results found for the given property and value."}
    
    except ValueError as ve:
        return {"error": f"Value error: {ve}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


# Streamlit app logic
def run(client):
    st.write("This tool searches Wikidata for enteries. The results are saved [here](https://docs.google.com/spreadsheets/d/1s1J1QRMnJukdvVhNU5EM_O625VGg198XwC6MTobb0SM/).")

    # Display examples table
    st.subheader("Examples")
    st.table([
        {"Property": "country of citizenship", "Matching Value": "Israel"},
        {"Property": "religion or worldview", "Matching Value": "Judaism"},
        {"Property": "ethnic group", "Matching Value": "Jewish people"},
        {"Property": "instance of", "Matching Value": "Jewish organization"},
        {"Property": "instance of", "Matching Value": "yeshiva"}
    ])
    
    with st.form("wikitada_form"):
        # Input fields for one property and value
        col1, col2 = st.columns(2)
        with col1:
            property_label = st.text_input("Property")
        with col2:
            value_label = st.text_input("Matching Value")
            
        submit_button = st.form_submit_button("Search Wikidata")
        
        # Process filters and query Wikidata
    if submit_button:
            # Set up Google Sheets
            websites_sheet = client.open_by_key(st.secrets["wikidata_id"]).worksheet("Websites")
            names_sheet = client.open_by_key(st.secrets["wikidata_id"]).worksheet("Names")
            timestamp = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime("%Y-%m-%d %H:%M:%S")
        
            # Add headers if the sheets are empty
            if len(websites_sheet.get_all_values()) <= 1:  # Only the header exists
                websites_sheet.append_row(["Name", "Website", "Source", "Timestamp"])
            if len(names_sheet.get_all_values()) <= 1:  # Only the header exists
                names_sheet.append_row(["Name", "Source", "Timestamp"])
    
            if property_label and value_label:
                try:
                    # Convert labels to IDs
                    property_id = label_to_id(property_label)
                    value_id = label_to_id(value_label)
                    explanation = f"{id_to_label(property_id)} - {id_to_label(value_id)}"
    
                    # Query Wikidata
                    st.info("Querying Wikidata...")
                    results = query_wikidata(property_id, value_id)
                    
                    # Process results
                    if results and "results" in results and "bindings" in results["results"]:
                        st.success("Query completed!")
                        websites_batch = []
                        names_batch = []
                    
                        for result in results["results"]["bindings"]:
                            # Attempt to get the English label
                            name_en = ""
                            if "itemLabel" in result:
                                name_en = result["itemLabel"].get("value", "")
                            
                            # If no English label, fallback to the item's value or any available label
                            if not name_en and "item" in result:
                                name_en = result["item"].get("value", "").split("/")[-1]  # Fallback to item ID as label
                        
                            website = result.get("website", {}).get("value", "")
                    
                            if website:
                                websites_batch.append([name_en, website, explanation, timestamp])
                            else:
                                names_batch.append([name_en, explanation, timestamp])
                    
                        # Write results to Google Sheets
                        if websites_batch:
                            websites_sheet.append_rows(websites_batch)
                        if names_batch:
                            names_sheet.append_rows(names_batch)
    
                        st.success("Results written to Google Sheets!")
                    else:
                        st.warning("No results found!")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("Please enter both a property and a value.")

