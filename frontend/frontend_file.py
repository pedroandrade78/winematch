"""
frontend_file.py

This is the frontend of the Wine Recommender project, built with
Streamlit (https://streamlit.io/). It is a SEPARATE, lightweight
project: it does NOT need pandas, FAISS or SBERT. Its only job is to:
  1. show a simple web page with inputs (a search box, filters, ...)
  2. send those inputs to our FastAPI backend
  3. display the results it gets back

Run it locally with:
    streamlit run frontend_file.py
"""

import os

import requests
import streamlit as st

# ---------------------------------------------------------------------
# 1. The URL of the backend API.
#
# While developing, this points to your local API (started with
# `uvicorn package_folder.api_file:app --reload --port 8000`).
# Once you deploy the API to Cloud Run, replace this with the Service
# URL you get from `gcloud run deploy` (or set the API_URL environment
# variable so you don't have to change the code).
# ---------------------------------------------------------------------
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")


# ---------------------------------------------------------------------
# 2. Page title and description
# ---------------------------------------------------------------------
st.title("🍷 Wine Recommender")
st.write(
    "Search for a wine by name, by id, or by the style you like. "
    "You can also add a property after a '+', for example: "
    "`Pinot Noir + low price` or `109 + sweet and fruity`."
)


# ---------------------------------------------------------------------
# 3. User inputs
# ---------------------------------------------------------------------
query = st.text_input("What are you looking for?", placeholder="e.g. Ornellaia 2014 Le Volte Red + low price" or "109 + low price")
top_k = st.slider("Number of recommendations", min_value=1, max_value=20, value=5)

with st.expander("Optional filters"):
    variety = st.text_input("Variety (exact match)", "")
    country = st.text_input("Country (exact match)", "")
    price_min = st.number_input("Minimum price", min_value=0.0, value=0.0, step=1.0)
    price_max = st.number_input("Maximum price", min_value=0.0, value=0.0, step=1.0)
    min_points = st.number_input("Minimum points (rating)", min_value=0, value=0, step=1)


# ---------------------------------------------------------------------
# 4. When the user clicks the button: call the API and show the results
# ---------------------------------------------------------------------
if st.button("Get recommendations"):
    if not query:
        st.warning("Please type something to search for first.")
    else:
        # Build the query parameters, only including filters that were
        # actually set by the user.
        params = {"query": query, "top_k": top_k}
        if variety:
            params["variety"] = variety
        if country:
            params["country"] = country
        if price_min > 0:
            params["price_min"] = price_min
        if price_max > 0:
            params["price_max"] = price_max
        if min_points > 0:
            params["min_points"] = min_points

        with st.spinner("Asking the API for recommendations..."):
            try:
                response = requests.get(f"{API_URL}/recommend", params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.RequestException as error:
                st.error(f"Could not reach the API at {API_URL}. Error: {error}")
                data = None

        if data:
            results = data.get("results", [])
            if not results:
                st.info("No wines matched your search. Try a different query.")
            else:
                st.success(f"Found {len(results)} wine(s) for '{query}'")
                for wine in results:
                    st.subheader(wine.get("title", "Unknown wine"))
                    st.write(
                        f"**Variety:** {wine.get('variety')}  |  "
                        f"**Country:** {wine.get('country')}"
                    )
                    st.write(
                        f"**Price:** ${wine.get('price')}  |  "
                        f"**Points:** {wine.get('points')}"
                    )
                    st.write(wine.get("description", ""))
                    st.markdown("---")



# API_URL=https://your-service-url.a.run.app streamlit run frontend_file.py
