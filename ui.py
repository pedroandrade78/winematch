"""
Streamlit UI for WineMatch.

Run with: streamlit run ui.py
"""

import os

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")


def call_recommend_api(query: str, top_k: int = 5, filters: dict = None):
    """Call the FastAPI /recommend endpoint and return results."""
    payload = {"query": query, "top_k": top_k}
    if filters:
        payload["filters"] = filters
    response = requests.post(f"{API_URL}/recommend", json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def render_filters_form() -> dict:
    """
    Render an optional 'Advanced filters' section. Each filter is behind a
    checkbox so an untouched field is genuinely omitted from the request,
    rather than sending a misleading 0/blank value as a real constraint.
    Returns a filters dict with only the enabled fields set (or {} if none).
    """
    filters = {}

    with st.expander("Advanced filters (optional)"):
        use_price = st.checkbox("Filter by price range")
        if use_price:
            col1, col2 = st.columns(2)
            with col1:
                filters["price_min"] = st.number_input("Min price ($)", min_value=0.0, value=0.0, step=5.0)
            with col2:
                filters["price_max"] = st.number_input("Max price ($)", min_value=0.0, value=50.0, step=5.0)

        use_points = st.checkbox("Filter by minimum rating")
        if use_points:
            filters["min_points"] = st.slider("Minimum points", 80, 100, 90)

        variety = st.text_input("Variety (optional, e.g. Pinot Noir)")
        if variety.strip():
            filters["variety"] = variety.strip()

        country = st.text_input("Country (optional, e.g. France)")
        if country.strip():
            filters["country"] = country.strip()

    return filters


def render_recommendations(results):
    """Display recommended wines as cards."""
    if not results:
        st.info("No matching wines found. Try a different name/id, property, or loosen your filters.")
        return

    for wine in results:
        with st.container(border=True):
            st.subheader(wine.get("title", "Unknown wine"))
            st.write(
                f"**{wine.get('variety', '')}** · {wine.get('country', '')} · "
                f"${wine.get('price', '?')} · {wine.get('points', '?')} pts"
            )
            st.write(wine.get("description", ""))
            if "similarity" in wine:
                st.caption(f"Match score: {wine['similarity']:.3f} · id: {wine.get('wine_id')}")


def main():
    st.title("🍷 WineMatch")
    st.write(
        "Enter a wine name or id, optionally followed by `+` and a property you want — "
        "price/rating (`low price`, `high rating`) or style (`sweet`, `fruity`, `high alcohol`), "
        "e.g. `Ornellaia 2014 Le Volte Red + sweet and fruity` or `109 + low price`. "
        "Use **Advanced filters** below for hard constraints like an exact price range."
    )

    query = st.text_input("Search", placeholder="Ornellaia 2014 Le Volte Red + sweet and fruity")
    top_k = st.slider("Number of recommendations", 1, 20, 5)
    filters = render_filters_form()

    if st.button("Find similar wines", type="primary") and query.strip():
        with st.spinner("Finding wines..."):
            try:
                results = call_recommend_api(query, top_k, filters)
                render_recommendations(results)
            except requests.RequestException as e:
                st.error(f"Could not reach the API: {e}")


if __name__ == "__main__":
    main()
