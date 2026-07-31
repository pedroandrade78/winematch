"""
Streamlit UI for WineMatch.

Run with: streamlit run ui.py
"""

import os

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "https://winematch-v2-485046883553.europe-west1.run.app")

NAVY = "#1B2A4A"
RED_WINE_COLOR = "#8B1E3F"
WHITE_WINE_COLOR = "#B8860B"  # muted gold, not literally "white"
NEUTRAL_COLOR = "#4A4A4A"

RED_VARIETIES = {
    "pinot noir", "cabernet sauvignon", "merlot", "syrah", "shiraz",
    "malbec", "zinfandel", "sangiovese", "tempranillo", "grenache",
    "nebbiolo", "cabernet franc", "petite sirah", "red blend",
}
WHITE_VARIETIES = {
    "chardonnay", "sauvignon blanc", "riesling", "pinot grigio",
    "pinot gris", "gewurztraminer", "viognier", "chenin blanc",
    "moscato", "white blend", "gruner veltliner",
}

COMMON_VARIETIES = sorted(RED_VARIETIES | WHITE_VARIETIES)
VARIETY_DISPLAY_MAP = {v.title(): v for v in COMMON_VARIETIES}
VARIETY_DISPLAY_OPTIONS = ["Any"] + sorted(VARIETY_DISPLAY_MAP.keys()) + ["Other (type below)"]

COUNTRY_OVERRIDES = {
    "us": "US",
    "uk": "UK",
    "usa": "USA",
    "uae": "UAE",
}

st.set_page_config(page_title="WineMatch", page_icon="🍷", layout="wide")

st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;1,400&display=swap" rel="stylesheet">
    <style>
    html, body,
    [class*="st-"]:not([data-testid="stIconMaterial"]),
    [class*="css"]:not([data-testid="stIconMaterial"]),
    p, span:not([data-testid="stIconMaterial"]), div, label {
        font-family: 'Lora', serif !important;
    }
    h1, h2, h3, h4 {
        font-family: 'Lora', serif !important;
    }

    label[data-testid="stWidgetLabel"] p {
        font-size: 1.3rem !important;
        font-weight: 500 !important;
    }
    .stMarkdown p {
        font-size: 1.1rem !important;
    }
    div.stButton > button[kind="primary"] {
        font-size: 1.3rem !important;
        font-weight: 600 !important;
        padding: 0.75rem 2.5rem !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 10px rgba(27, 42, 74, 0.35) !important;
        letter-spacing: 0.03em !important;
        transition: all 0.2s ease-in-out !important;
    }
    div.stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 14px rgba(27, 42, 74, 0.45) !important;
        transform: translateY(-1px) !important;
    }
    div[data-testid="stTextInput"] {
        margin-bottom: 1.5rem;
    }
    div[data-testid="stSlider"] {
        margin-bottom: 1.5rem;
    }
    div[data-testid="stExpander"] {
        margin-bottom: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_variety_color(variety: str) -> str:
    """Best-effort color classification based on variety name; falls back to neutral."""
    if not variety:
        return NEUTRAL_COLOR
    v = variety.lower().strip()
    if v in RED_VARIETIES:
        return RED_WINE_COLOR
    if v in WHITE_VARIETIES:
        return WHITE_WINE_COLOR
    return NEUTRAL_COLOR


def points_to_stars(points) -> str:
    """
    Map an 80-100 point score to a 1-5 star display, using buckets tuned to
    this dataset's actual distribution (most wines score 85-92), so the
    common range spreads across more of the star scale.
    """
    try:
        points = float(points)
    except (TypeError, ValueError):
        return ""

    if points >= 95:
        stars = 5
    elif points >= 90:
        stars = 4
    elif points >= 87:
        stars = 3
    elif points >= 84:
        stars = 2
    else:
        stars = 1

    return "★" * stars + "☆" * (5 - stars)


def to_title_case(text: str) -> str:
    """Convert lowercase data-layer text to a more readable display form."""
    if not text:
        return text
    return text.title()


def to_title_case_country(text: str) -> str:
    """Title-case a country name, correctly handling abbreviations like US/UK."""
    if not text:
        return text
    key = text.lower().strip()
    if key in COUNTRY_OVERRIDES:
        return COUNTRY_OVERRIDES[key]
    return text.title()


def to_sentence_case(text: str) -> str:
    """Capitalize the first letter of each sentence for description text."""
    if not text:
        return text
    sentences = text.split(". ")
    return ". ".join(s[:1].upper() + s[1:] if s else s for s in sentences)


def call_recommend_api(query: str, top_k: int = 5, filters: dict = None):
    """Call the FastAPI /recommend endpoint and return results."""
    payload = {"query": query, "top_k": top_k}
    if filters:
        payload["filters"] = filters
    response = requests.post(f"{API_URL}/recommend", json=payload, timeout=60)
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

        variety_choice = st.selectbox("Variety (optional)", VARIETY_DISPLAY_OPTIONS)
        if variety_choice == "Other (type below)":
            other_variety = st.text_input("Type a variety")
            if other_variety.strip():
                filters["variety"] = other_variety.strip().lower()
        elif variety_choice != "Any":
            filters["variety"] = VARIETY_DISPLAY_MAP[variety_choice]

        country = st.text_input("Country (optional, e.g. France)")
        if country.strip():
            filters["country"] = country.strip()

    return filters


def render_wine_card(wine: dict):
    """Render a single wine as a color-coded card with a star rating."""
    color = get_variety_color(wine.get("variety", ""))
    stars = points_to_stars(wine.get("points"))
    title = to_title_case(wine.get("title", "Unknown wine"))
    variety = to_title_case(wine.get("variety", ""))
    country = to_title_case_country(wine.get("country", ""))
    description = to_sentence_case(wine.get("description", ""))

    with st.container(border=True):
        st.markdown(
            f"<h4 style='color:{color}; margin-bottom:0;'>{title}</h4>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<span style='color:{color};'>**{variety}**</span> · "
            f"{country} · ${wine.get('price', '?')} · "
            f"<span style='color:{color};'>{stars}</span> ({wine.get('points', '?')} pts)",
            unsafe_allow_html=True,
        )
        st.write(description)
        if "similarity" in wine:
            st.caption(f"Match score: {wine['similarity']:.3f} · id: {wine.get('wine_id')}")


def render_recommendations(results):
    """Display recommended wines as cards."""
    if not results:
        st.info("No matching wines found. Try a different name/id, property, or loosen your filters.")
        return
    for wine in results:
        render_wine_card(wine)


def main():
    st.markdown(
        f"<h1 style='color:{NAVY};'>🍷 WineMatch</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='font-style: italic; font-size: 1.05em;'>"
        "Enter a wine's name or id, optionally followed by a <code>+</code> and a quality you're after — "
        "price or rating (<em>low price</em>, <em>high rating</em>), or style (<em>sweet</em>, "
        "<em>fruity</em>, <em>high alcohol</em>). For example: "
        "<em>Ornellaia 2014 Le Volte Red + sweet and fruity</em>, or <em>109 + low price</em>. "
        "For precise constraints, such as an exact price range, use <strong>Advanced filters</strong> below."
        "</p>",
        unsafe_allow_html=True,
    )

    query = st.text_input("Please enter your search here:", placeholder="Ornellaia 2014 Le Volte Red + sweet and fruity")
    top_k = st.slider("Number of recommendations", 1, 20, 5)
    filters = render_filters_form()

    if st.button("Find similar wines", type="primary") and query.strip():
        with st.spinner("Finding wines... this can take a moment on first use."):
            try:
                results = call_recommend_api(query, top_k, filters)
                render_recommendations(results)
            except requests.RequestException as e:
                st.error(f"Could not reach the API: {e}")


if __name__ == "__main__":
    main()
