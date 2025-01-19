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
        error_handler("id to label", wikidata_id, e)
        return wikidata_id

# Function to convert Label (e.g., "country of citizenship") to ID (e.g., "P27")
def label_to_id(label):
    try:
        sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
        sparql.setQuery(f"""
        SELECT ?entity ?label WHERE {{
            ?entity rdfs:label "{label}"@en.
            FILTER(STRSTARTS(STR(?entity), "http://www.wikidata.org/entity/"))
        }}
        """)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
    
        entities = []
        if results["results"]["bindings"]:
            for binding in results["results"]["bindings"]:
                entities.append(binding["entity"]["value"].split("/")[-1])  # Extract ID from the URL
            return entities
        else:
            return []
    except Exception as e:
        error_handler("label to id", label, str(e))
        return []


# Query Wikidata dynamically, including Hebrew label and instance of
def query_wikidata(property_id, value_id, language="en"):
    if not property_id or not value_id:
        return {"error": "Property ID and Value ID must be provided."}  
    try:
        query = f"""
        SELECT DISTINCT ?item ?itemLabel ?itemLabel_he ?website ?instance_of_label WHERE {{
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{language}". }}
          {{
            SELECT DISTINCT ?item WHERE {{
              ?item p:{property_id} ?statement0.
              ?statement0 (ps:{property_id}/(wdt:P279*)) wd:{value_id}.
            }}
          }}
          OPTIONAL {{ ?item wdt:P856 ?website }}  # Personal website
          OPTIONAL {{ ?item rdfs:label ?itemLabel_he. FILTER(LANG(?itemLabel_he) = "he") }}  # Hebrew label
          OPTIONAL {{ ?item wdt:P31 ?instance_of. }}  # Instance of
          OPTIONAL {{ ?instance_of rdfs:label ?instance_of_label. FILTER(LANG(?instance_of_label) = "{language}") }}  # Instance of label
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



def run(client):
    st.write("This tool searches Wikidata for entries. The results are saved [here](https://docs.google.com/spreadsheets/d/1s1J1QRMnJukdvVhNU5EM_O625VGg198XwC6MTobb0SM/).")

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
        websites_sheet = client.open_by_key(st.secrets["wikidata_id"]).worksheet("Websites")
        names_sheet = client.open_by_key(st.secrets["wikidata_id"]).worksheet("Names")
        timestamp = datetime.now(pytz.timezone('Asia/Jerusalem')).strftime("%Y-%m-%d %H:%M:%S")
        
        # Add headers if the sheets are empty
        if len(websites_sheet.get_all_values()) <= 1:  # Only the header exists
            websites_sheet.append_row(["Name", "Wikidata ID", "Website", "Property Label", "Value Label", "Property ID", "Value ID", "Hebrew Label", "Instance Of", "Timestamp"])
        if len(names_sheet.get_all_values()) <= 1:  # Only the header exists
            names_sheet.append_row(["Name", "Wikidata ID", "Property Label", "Value Label", "Property ID", "Value ID", "Hebrew Label", "Instance Of", "Timestamp"])
    
        if property_label and value_label:
            try:
                # Convert labels to IDs
                property_id = label_to_id(property_label)
                value_id = label_to_id(value_label)
                                                
                # Query Wikidata for all possible IDs
                if isinstance(property_id, list) and property_id:
                    st.info(f"Found {len(property_id)} possible Property IDs for '{property_label}'.")
                else:
                    st.info(f"Found 1 Property ID: {property_id}")
                
                if isinstance(value_id, list) and value_id:
                    st.info(f"Found {len(value_id)} possible IDs for '{value_label}'.")
                else:
                    st.info(f"Found 1 Value ID: {value_id}")

                # Query Wikidata for all possible combinations
                results = []
                for p_id in (property_id if isinstance(property_id, list) else [property_id]):
                    for v_id in (value_id if isinstance(value_id, list) else [value_id]):
                        query_results = query_wikidata(p_id, v_id)
                        if query_results and "results" in query_results and "bindings" in query_results["results"]:
                            results.append({
                                "p_id": p_id,
                                "v_id": v_id,
                                "property_label": id_to_label(p_id),
                                "value_label": id_to_label(v_id),
                                "results": query_results["results"]["bindings"]
                            })

                # Process results
                if results:
                    st.success("Query completed!")
                    websites_batch = []
                    names_batch = []
                    
                    for result_data in results:
                        p_id = result_data["p_id"]
                        v_id = result_data["v_id"]
                        property_label = result_data["property_label"]
                        value_label = result_data["value_label"]
                        
                        for result in result_data["results"]:
                            # Get the English and Hebrew labels for the item
                            name_en = result["itemLabel"].get("value", "")
                            name_he = result.get("itemLabel_he", {}).get("value", "")
                            
                            # If no English label, fallback to the item's value or any available label
                            if not name_en and "item" in result:
                                name_en = result["item"].get("value", "").split("/")[-1]  # Fallback to item ID as label
                            
                            website = result.get("website", {}).get("value", "")
                            wikidata_id = result["item"].get("value", "").split("/")[-1]
                            
                            # Get the Instance Of value (P31)
                            instance_of = result.get("instance_of_label", {}).get("value", "Unknown")
                            
                            # Prepare the row data
                            row_data = [
                                name_en,
                                name_he,
                                website,
                                wikidata_id,
                                instance_of,
                                f"{property_label} ({p_id})",
                                f"{value_label} ({v_id})",
                                timestamp
                            ]
                            
                            # Write to appropriate sheet
                            if website:
                                websites_batch.append(row_data)
                            else:
                                # Exclude website column for Names sheet
                                names_batch.append([
                                    name_en,
                                    name_he,
                                    wikidata_id,
                                    instance_of,
                                    f"{property_label} ({p_id})",
                                    f"{value_label} ({v_id})",
                                    timestamp
                                ])
                    
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
