import streamlit as st
from googlesearch import search
from datetime import datetime
import pytz
import re
from collections import Counter
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

# Load criteria from the Google Sheet
def load_criteria():
    rows = query_sheet.get_all_records()
    filters = []
    explanations = []

    for row in rows:
        property_name = row["Property"].strip()
        property_id = label_to_id(property_name)
        value_name = row["Matching Value"].strip()
        matching_value = label_to_id(value_name)
        explanation = f"{property_name} is {value_name}"
        filters.append(f"?entity wdt:{property_id} wd:{matching_value}.")
        explanations.append(explanation)

    return filters, explanations

# Query Wikidata dynamically
def query_wikidata(filters):
    # Add "OR" between filters
    filter_conditions = " UNION ".join([f"{{ {f} }}" for f in filters])
    query = f"""
    SELECT ?entity ?entityLabel ?entityAltLabel ?website WHERE {{
        {filter_conditions}
        OPTIONAL {{ ?entity wdt:P856 ?website }}  # Personal website
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()

# Process query results in batches of 20
def process_results(results, filters, explanations, client):
    batch_size = 10000
    websites_batch = []
    names_batch = []

    # Iterate through the results and explanations for each row
    for i, result in enumerate(results["results"]["bindings"]):
        name_en = result["entityLabel"]["value"]
        website = result.get("website", {}).get("value", "")

        # Get the explanation for the corresponding filter
        # Since there can be multiple rows per filter, we get the explanation from the filters list
        explanation = explanations[i % len(filters)]  # Use modulo to cycle through explanations if needed

        if website:
            websites_batch.append([name_en, website, explanation])
        else:
            names_batch.append([name_en, explanation])

        # Write batches of rows
        if len(websites_batch) >= batch_size:
            websites_sheet.append_rows(websites_batch)
            print(f"Added {batch_size} names with websites")
            websites_batch = []

        if len(names_batch) >= batch_size:
            names_sheet.append_rows(names_batch)
            print(f"Added {batch_size} names")
            names_batch = []

    # Write remaining rows
    if websites_batch:
        websites_sheet.append_rows(websites_batch)
    if names_batch:
        names_sheet.append_rows(names_batch)


def run(client):
    st.subheader("Wikidata Tool")
    st.write("This tool interacts with Wikidata for advanced queries.")
    st.text_input("Enter a Wikidata query")
