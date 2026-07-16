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
    raise NotImplementedError


def render_recommendations(results):
    """Display recommended wines as cards."""
    raise NotImplementedError


def main():
    st.title("🍷 WineMatch")
    st.write(
        "Enter a wine name or id, optionally followed by `+` and a property you want — "
        "price/rating (`low price`, `high rating`) or style (`sweet`, `fruity`, `high alcohol`), "
        "e.g. `Ornellaia 2014 Le Volte Red + sweet and fruity` or `109 + low price`."
    )
    raise NotImplementedError


if __name__ == "__main__":
    main()
