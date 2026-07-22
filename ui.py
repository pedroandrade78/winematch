"""
Streamlit UI for WineMatch.

Run with: streamlit run ui.py
"""

import os

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")


def call_recommend_api(query: str, top_k: int = 5):
    """Call the FastAPI /recommend endpoint and return results."""
    try:
        response = requests.post(
            f"{API_URL}/recommend",
            json={"query": query, "top_k": top_k},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error(f"Could not connect to the API at {API_URL}. Is it running?")
        return []
    except requests.exceptions.HTTPError as e:
        st.error(f"API returned an error: {e}")
        return []
    except requests.exceptions.Timeout:
        st.error("The API took too long to respond.")
        return []


def render_recommendations(results):
    """Display recommended wines as cards."""
    if not results:
        st.info("No recommendations to show yet.")
        return

    for wine in results:
        with st.container(border=True):
            st.subheader(wine.get("title", "Unknown wine"))
            col1, col2, col3 = st.columns(3)
            col1.metric("Price", f"${wine.get('price', '—')}")
            col2.metric("Rating", wine.get("points", "—"))
            col3.metric("Variety", wine.get("variety", "—"))
            st.caption(f"Country: {wine.get('country', '—')} · Wine ID: {wine.get('wine_id', '—')}")


def main():
    st.title("🍷 WineMatch")
    st.write(
        "Enter a wine name or id, optionally followed by `+` and a property you want — "
        "price/rating (`low price`, `high rating`) or style (`sweet`, `fruity`, `high alcohol`), "
        "e.g. `Ornellaia 2014 Le Volte Red + sweet and fruity` or `109 + low price`."
    )

    query = st.text_input("Search", placeholder="e.g. 109 + low price")
    top_k = st.slider("Number of results", min_value=1, max_value=10, value=5)

    if st.button("Search", type="primary") and query:
        with st.spinner("Finding wines..."):
            results = call_recommend_api(query, top_k=top_k)
        render_recommendations(results)


if __name__ == "__main__":
    main()
