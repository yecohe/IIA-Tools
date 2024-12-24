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

# Streamlit app logic
def run():
    st.subheader("Wikidata Tool")

    # Initialize session state for dynamic rows
    if "filters" not in st.session_state:
        st.session_state.filters = [{"property": "", "value": ""}]

    # Display dynamic input rows
    for i, filter_row in enumerate(st.session_state.filters):
        cols = st.columns(2)
        cols[0].text_input(f"Property {i+1}", key=f"property_{i}", value=filter_row["property"])
        cols[1].text_input(f"Value {i+1}", key=f"value_{i}", value=filter_row["value"])

    # Add and remove buttons
    col1, col2 = st.columns([1, 1])
    if col1.button("Add Row"):
        st.session_state.filters.append({"property": "", "value": ""})
    if col2.button("Remove Row") and len(st.session_state.filters) > 1:
        st.session_state.filters.pop()

    # Process filters and query Wikidata
    if st.button("Run Query"):
        # Convert inputs to SPARQL filters
        filters = []
        explanations = []

        for filter_row in st.session_state.filters:
            property_label = filter_row["property"]
            value_label = filter_row["value"]

            if property_label and value_label:
                property_id = label_to_id(property_label)
                value_id = label_to_id(value_label)
                filters.append(f"?entity wdt:{property_id} wd:{value_id}.")
                explanations.append(f"{property_label} is {value_label}")

        if filters:
            st.info("Querying Wikidata...")
            results = query_wikidata(filters)
            st.success("Query completed!")

            # Display results
            if results["results"]["bindings"]:
                for result in results["results"]["bindings"]:
                    entity_label = result["entityLabel"]["value"]
                    website = result.get("website", {}).get("value", "No website available")
                    st.write(f"**Entity**: {entity_label}, **Website**: {website}")
            else:
                st.warning("No results found!")
        else:
            st.error("Please add at least one valid filter.")

