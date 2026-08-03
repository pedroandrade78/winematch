"""
Streamlit UI for WineMatch.

Run with: streamlit run ui.py
"""

import html
import os

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "https://winematch-v2-485046883553.europe-west1.run.app")

EXAMPLE_QUERIES = [
    "Pinot Noir + sweet and fruity",
    "109 + low price",
    "Malbec + high rating",
    "Ornellaia 2014 Le Volte Red + sweet and fruity",
]


# ---------------------------------------------------------------------
# Custom styling only -- everything below still uses normal Streamlit
# commands (st.button, st.text_input, ...) and the same API calls/logic
# as before. This block just makes it look like a wine label.
# Palette: warm parchment background, deep bordeaux accent, gold touch.
# ---------------------------------------------------------------------
st.set_page_config(page_title="WineMatch", page_icon="🍷", layout="wide")

st.markdown(
    """
    <style>
    html, body, [class*="css"]  {
        font-family: sans-serif;
    }

    /* ---- Hero header ---- */
    .wm-hero {
        padding: 1.75rem 2rem;
        margin-bottom: 1.5rem;
        border-radius: 6px;
        background: linear-gradient(135deg, #6E1E33 0%, #8C2C46 100%);
        color: #F8EFE0;
    }
    .wm-hero h1 {
        font-family: 'Playfair Display', serif;
        font-size: 2.6rem;
        font-weight: 700;
        margin: 0 0 0.25rem 0;
        color: #F8EFE0;
        letter-spacing: 0.01em;
    }
    .wm-hero p {
        font-size: 1.02rem;
        margin: 0;
        color: #E9CBA7;
        font-style: italic;
    }

    /* ---- Eyebrow labels (small caps tags above content) ---- */
    .wm-eyebrow {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #9C6B3F;
        margin-bottom: 0.2rem;
    }

    /* ---- Wine result card, styled like a printed label ---- */
    .wm-card {
        background: #FFFDF8;
        border: 1px solid #E4D3AE;
        outline: 1px solid #E4D3AE;
        outline-offset: -5px;
        border-radius: 4px;
        padding: 1.1rem 1.2rem;
        margin-bottom: 1rem;
        height: 100%;
    }
    .wm-card h3 {
        font-family: 'Playfair Display', serif;
        font-size: 1.25rem;
        font-weight: 700;
        color: #4A1424;
        margin: 0.1rem 0 0.4rem 0;
        line-height: 1.25;
    }
    .wm-card .wm-meta {
        font-size: 0.85rem;
        color: #6B5B5B;
        margin-bottom: 0.55rem;
    }
    .wm-card .wm-desc {
        font-size: 0.88rem;
        color: #3A2E2E;
        font-style: italic;
        line-height: 1.45;
    }

    /* ---- Badges (price, points, match) ---- */
    .wm-badge {
        display: inline-block;
        padding: 0.15rem 0.55rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 0.4rem;
    }
    .wm-badge-price {
        background: #F1E3CB;
        color: #6E1E33;
    }
    .wm-badge-rating {
        background: #6E1E33;
        color: #F8EFE0;
    }
    .wm-badge-match {
        background: #E9CBA7;
        color: #4A1424;
    }

    /* ---- Empty state ---- */
    .wm-empty {
        border: 1px dashed #C9A97F;
        border-radius: 6px;
        padding: 1.5rem;
        text-align: center;
        color: #6B5B5B;
        background: #FBF6EE;
    }

    /* ---- Sidebar heading ---- */
    section[data-testid="stSidebar"] .wm-eyebrow {
        margin-top: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def call_search_titles_api(prefix: str, limit: int = 6):
    """Call the FastAPI /search-titles endpoint for autocomplete suggestions."""
    try:
        response = requests.get(f"{API_URL}/search-titles", params={"q": prefix, "limit": limit}, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []  # autocomplete is a nice-to-have -- fail silently, don't block the main search


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
    Render an optional 'Advanced filters' section in the sidebar. Each filter
    is behind a checkbox so an untouched field is genuinely omitted from the
    request, rather than sending a misleading 0/blank value as a real
    constraint. Returns a filters dict with only the enabled fields set
    (or {} if none).
    """
    filters = {}

    st.sidebar.markdown('<div class="wm-eyebrow">Refine your search</div>', unsafe_allow_html=True)
    st.sidebar.caption("Hard constraints (optional) — combined with whatever you type in the search box.")

    use_price = st.sidebar.checkbox("Filter by price range")
    if use_price:
        filters["price_min"] = st.sidebar.number_input("Min price ($)", min_value=0.0, value=0.0, step=5.0)
        filters["price_max"] = st.sidebar.number_input("Max price ($)", min_value=0.0, value=50.0, step=5.0)

    use_points = st.sidebar.checkbox("Filter by minimum rating")
    if use_points:
        filters["min_points"] = st.sidebar.slider("Minimum points", 80, 100, 90)

    variety = st.sidebar.text_input("Variety (e.g. Pinot Noir)")
    if variety.strip():
        filters["variety"] = variety.strip()

    country = st.sidebar.text_input("Country (e.g. France)")
    if country.strip():
        filters["country"] = country.strip()

    return filters


def points_to_glasses(points, filled_glass="🍷", empty_glass="·", scale=5) -> str:
    """Convert a 0-100 point score into a 1-5 wine-glass string for a quick visual read."""
    try:
        points = float(points)
    except (TypeError, ValueError):
        return empty_glass * scale
    filled = max(1, min(scale, round((points - 80) / 4)))  # 80pts -> 1 glass, 100pts -> 5 glasses
    return filled_glass * filled + empty_glass * (scale - filled)


def render_recommendations(results):
    """Display recommended wines as a grid of label-style cards."""
    if not results:
        st.markdown(
            '<div class="wm-empty">No wines matched your search. '
            'Try a different name/id, or loosen your filters.</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(f"##### Found {len(results)} wine(s)")

    columns = st.columns(2)
    for index, wine in enumerate(results):
        with columns[index % 2]:
            title = html.escape(str(wine.get("title", "Unknown wine")).title())
            variety_val = html.escape(str(wine.get("variety", "")).title())
            country_val = html.escape(str(wine.get("country", "")).title())
            description = html.escape(str(wine.get("description", "")))
            price = wine.get("price", "?")
            points = wine.get("points", "?")
            similarity = wine.get("similarity")
            glasses = points_to_glasses(points)
            match_badge = (
                f'<span class="wm-badge wm-badge-match">{similarity * 100:.0f}% match</span>'
                if similarity is not None else ""
            )

            st.markdown(
                f"""
                <div class="wm-card">
                    <div class="wm-eyebrow">{variety_val} &middot; {country_val}</div>
                    <h3>{title}</h3>
                    <div class="wm-meta">
                        <span class="wm-badge wm-badge-price">${price}</span>
                        <span class="wm-badge wm-badge-rating">{glasses} {points} pts</span>
                        {match_badge}
                    </div>
                    <div class="wm-desc">{description}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption(f"id: {wine.get('wine_id')}")


def main():
    st.markdown(
        """
        <div class="wm-hero">
            <h1>🍷 WineMatch</h1>
            <p>Describe what you're craving, or point to a wine you love — we'll pour the closest match.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write(
        "Enter a wine name or id, optionally followed by `+` and a property you want — "
        "price/rating (`low price`, `high rating`) or style (`sweet`, `fruity`, `high alcohol`). "
        "Use **Advanced filters** in the sidebar for hard constraints like an exact price range."
    )

    if "query" not in st.session_state:
        st.session_state["query"] = ""

    st.write("**Try:**")
    example_cols = st.columns(len(EXAMPLE_QUERIES))
    for col, example in zip(example_cols, EXAMPLE_QUERIES):
        if col.button(example, use_container_width=True):
            st.session_state["query"] = example

    search_col, button_col = st.columns([5, 1])
    with search_col:
        query = st.text_input(
            "What are you looking for?",
            key="query",
            placeholder="e.g. '109 + low price' or 'Pinot Noir + sweet and fruity'",
        )
    with button_col:
        search_clicked = st.button("Uncork 🍷", type="primary", use_container_width=True)

    # Autocomplete: only trigger on the wine-name part (before any "+"), and
    # only once there's enough text to make suggestions worthwhile.
    name_part = query.split("+")[0].strip()
    if name_part and len(name_part) >= 3:
        suggestions = call_search_titles_api(name_part)
        if suggestions:
            st.caption("Suggestions: " + " · ".join(suggestions[:6]))

    top_k = st.slider("Number of recommendations", 1, 20, 5)
    filters = render_filters_form()

    if search_clicked and query.strip():
        with st.spinner("Swirling through the cellar... (the first search can take a bit longer if the server is waking up)"):
            try:
                results = call_recommend_api(query, top_k, filters)
                render_recommendations(results)
            except requests.RequestException as e:
                st.error(f"Could not reach the API: {e}")
    elif search_clicked:
        st.warning("Type something in the search box before searching.")
    else:
        st.markdown(
            '<div class="wm-empty">Type a wine name, an id, or a style you like above, '
            'then hit <strong>Uncork</strong> to see your matches.</div>',
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
