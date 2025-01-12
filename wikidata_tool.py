import streamlit as st
from SPARQLWrapper import SPARQLWrapper, JSON

# Function to convert ID (e.g., "P27") to Label (e.g., "country of citizenship")
def id_to_label(wikidata_id):
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

# Function to convert Label (e.g., "country of citizenship") to ID (e.g., "P27")
def label_to_id(label):
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setQuery(f"""
    SELECT ?entity WHERE {{
        ?entity rdfs:label "{label}"@en.
    }}
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    if results["results"]["bindings"]:
        return results["results"]["bindings"][0]["entity"]["value"].split("/")[-1]
    else:
        return label

# Query Wikidata dynamically
def query_wikidata(property_id, value_id):
    query = f"""
    SELECT ?entity ?entityLabel ?website WHERE {{
        ?entity wdt:{property_id} wd:{value_id}.
        OPTIONAL {{ ?entity wdt:P856 ?website }}  # Personal website
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()

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
    
        # Process filters and query Wikidata
        if st.button("Run Query"):
            # Set up Google Sheets
            websites_sheet = client.open_by_key(st.secrets["wikidata_id"]).worksheet("Websites")
            names_sheet = client.open_by_key(st.secrets["wikidata_id"]).worksheet("Names")
            
            # Add headers if the sheets are empty
            if len(websites_sheet.get_all_values()) <= 1:  # Only the header exists
                websites_sheet.append_row(["Name", "Website", "Source"])
            if len(names_sheet.get_all_values()) <= 1:  # Only the header exists
                names_sheet.append_row(["Name", "Source"])
    
            if property_label and value_label:
                try:
                    # Convert labels to IDs
                    property_id = label_to_id(property_label)
                    value_id = label_to_id(value_label)
                    explanation = f"{property_label} - {value_label}"
    
                    # Query Wikidata
                    st.info("Querying Wikidata...")
                    results = query_wikidata(property_id, value_id)
                    st.success("Query completed!")
    
                    # Process results
                    if results and "results" in results and "bindings" in results["results"]:
                        websites_batch = []
                        names_batch = []
    
                        for result in results["results"]["bindings"]:
                            name_en = result["entityLabel"]["value"]
                            website = result.get("website", {}).get("value", "")
    
                            if website:
                                websites_batch.append([name_en, website, explanation])
                            else:
                                names_batch.append([name_en, explanation])
    
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

