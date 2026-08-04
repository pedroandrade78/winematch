"""
Streamlit UI for WineMatch.

Run with: streamlit run ui.py
"""

import os
import re

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "https://winematch-v2-485046883553.europe-west1.run.app")

NAVY = "#1B2A4A"
RED_WINE_COLOR = "#8B1E3F"
WHITE_WINE_COLOR = "#B8860B"  # muted gold, not literally "white"
ROSE_WINE_COLOR = "#D46A8C"  # dusty rose/pink
SPARKLING_WINE_COLOR = "#7C93A3"  # cool silvery-blue, evokes bubbles/effervescence
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

# Larger, dataset-derived keyword lists used only for card-title colouring
# (get_variety_color), covering 4 categories instead of 2. Kept separate
# from RED_VARIETIES/WHITE_VARIETIES above, which back the sidebar's
# "Variety" filter dropdown and must stay a short, curated list of exact,
# filterable values -- these ones are for substring matching against any
# variety string returned by the API, and cover ~99.97% of wines_clean.csv.
SPARKLING_COLOR_VARIETIES = {
    "sparkling", "champagne", "prosecco", "glera", "cava",
    "cremant", "crémant", "frizzante", "asti",
}

ROSE_COLOR_VARIETIES = {
    "rosé", "rose", "rosado", "rosato", "moscato rosa", "rosenmuskateller",
}

RED_COLOR_VARIETIES = {
    # major international reds
    "pinot noir", "pinot nero", "spätburgunder", "cabernet sauvignon", "cabernet franc",
    "cabernet", "merlot", "syrah", "shiraz", "malbec", "zinfandel", "primitivo",
    "sangiovese", "tempranillo", "tinta roriz", "tinto fino", "tinto del pais",
    "tinto velasco", "tinta del pais", "tinta del toro", "tinta de toro",
    "grenache", "garnacha", "cannonau", "nebbiolo", "barbera", "montepulciano",
    "nero d'avola", "nero di troia", "aglianico", "touriga nacional", "touriga franca",
    "touriga", "baga", "tannat", "carignan", "carignane", "carignano", "cariñena",
    "mourvèdre", "monastrell", "mataro", "gamay", "dolcetto", "corvina", "rondinella",
    "molinara", "negroamaro", "blaufränkisch", "kékfrankos", "kekfrankos", "frankovka",
    "zweigelt", "xinomavro", "agiorgitiko", "mavrud", "mavrodaphne", "mavrokalavryta",
    "mavrotragano", "mavroudi", "saperavi", "carmenère", "pinotage", "lagrein",
    "teroldego", "refosco", "marzemino", "freisa", "grignolino", "dornfelder",
    "lemberger", "st. laurent", "portugieser", "mencía", "graciano", "bobal",
    "alicante", "castelão", "trincadeira", "jaen", "aragonez", "aragonês", "ramisco",
    "tinta barroca", "tinta cao", "tinta madeira", "tinta miúda", "tinta negra mole",
    "vranac", "vranec", "plavac mali", "babić", "teran", "kadarka", "blauburger",
    "blauburgunder", "frühburgunder", "früburgunder", "schiava", "lambrusco",
    "rara neagra", "susumaniello", "gaglioppo", "sagrantino", "ciliegiolo",
    "colorino", "canaiolo", "pugnitello", "prugnolo gentile", "malvasia nera",
    "petite sirah", "petite verdot", "petit verdot", "red blend", "claret",
    "meritage", "g-s-m", "bordeaux-style red", "rhône-style red", "provence red",
    "austrian red", "portuguese red", "port", "trollinger", "bonarda",
    "nerello mascalese", "nerello cappuccio", "pinot meunier", "cinsault",
    "frappato", "charbono", "negrette", "norton", "baco noir", "prieto picudo",
    "alfrocheiro", "brachetto", "piedirosso", "kalecik karasi", "raboso",
    "mondeuse", "uva di troia", "counoise", "ruché", "trepat", "okuzgozu",
    "feteasca neagra", "gragnano", "chambourcin", "jacquez", "chancellor",
    "marquette", "st. vincent", "marselan", "mazuelo", "mansois", "duras",
    "braucol", "sirica", "sciaccerellu", "nielluciu", "melnik", "kotsifali",
    "tsapournakos", "papaskarasi", "karasakiz", "boğazkere", "çalkarası",
    "žilavka", "sousão", "souzao", "vinhão", "tinta francisca", "tinta amarela",
    "tinta fina", "tintilia", "morava", "listán negro", "grolleau", "groppello",
    "magliocco", "manzoni", "perricone", "poulsard", "trousseau", "abouriou",
    "cesanese", "durif", "alvarelhão", "aleatico", "albarossa", "argaman",
    "bastardo", "blatina", "bovale", "carcajolu", "carineña", "casavecchia",
    "centesimino", "chelois", "fer servadou", "forcallà", "franconia", "gamza",
    "mandilaria", "mission", "país", "monica", "otskhanuri sapere", "ojaleshi",
    "parraleta", "pignolo", "portuguiser", "prunelard", "rebo", "rufete",
    "schwartzriesling", "valdiguié", "kuntra", "vespolina",
    # generic red/black colour markers used as bare words in this dataset
    "noir", "nero", "nera", "rosso", "tinta", "tinto", "black", "negro", "kara",
}

WHITE_COLOR_VARIETIES = {
    "chardonnay", "sauvignon blanc", "sauvignon", "riesling", "pinot grigio",
    "pinot gris", "pinot blanc", "pinot bianco", "gewürztraminer", "gewurztraminer",
    "traminer", "traminette", "viognier", "chenin blanc", "moscato", "muscat",
    "muscatel", "moscatel", "white blend", "gruner veltliner", "grüner veltliner",
    "veltliner", "albariño", "albarino", "verdejo", "vermentino", "trebbiano",
    "garganega", "cortese", "falanghina", "fiano", "semillon", "sémillon",
    "torrontés", "grecanico", "grechetto", "greco", "godello", "arinto",
    "encruzado", "loureiro", "arneis", "friulano", "malvasia", "verdicchio",
    "vernaccia", "picpoul", "picolit", "colombard", "ugni blanc", "folle blanche",
    "chasselas", "silvaner", "sylvaner", "müller-thurgau", "kerner", "scheurebe",
    "furmint", "hárslevelü", "welschriesling", "graševina", "grasevina",
    "assyrtiko", "assyrtico", "roditis", "malagousia", "malagouzia", "vidal",
    "vidal blanc", "seyval blanc", "chardonel", "cayuga", "niagara", "diamond",
    "catawba", "symphony", "sacy", "elbling", "kisi", "rkatsiteli", "mtsvane",
    "chinuri", "carricante", "insolia", "inzolia", "catarratto", "grillo",
    "zibibbo", "moscato giallo", "cerceal", "fernão pires", "antão vaz", "gouveio",
    "rabigato", "viosinho", "loureiro-arinto", "azal", "avesso", "trajadura",
    "bical", "maria gomes", "malvar", "airen", "verdil", "xarel-lo", "macabeo",
    "treixadura", "verdelho", "verdello", "boal", "bual", "sercial", "terrantez",
    "white port", "biancolella", "grauburgunder", "weissburgunder", "auxerrois",
    "savagnin", "petit manseng", "gros manseng", "gros and petit manseng",
    "melon", "viura", "turbiana", "roussanne", "marsanne", "fumé blanc",
    "pedro ximénez", "moschofilero", "jacquère", "muskateller", "muskat",
    "hondarrabi zuri", "rotgipfler", "passerina", "palomino", "pansa blanca",
    "zierfandler", "tocai", "morillon", "muscadelle", "muscadine", "muscadel",
    "nosiola", "posip", "durella", "pallagrello bianco", "sherry", "clairette",
    "erbaluce", "favorita", "mauzac", "alvarinho", "pecorino", "ribolla gialla",
    "tokaji", "tokay", "aligoté", "albana", "albanello", "siria", "vignoles",
    "coda di volpe", "códega do larinho", "romorantin", "verduzzo", "rebula",
    "robola", "torontel", "nasco", "nuragus", "pignoletto", "sauvignonasse",
    "savatiano", "verdeca", "vespaiolo", "picapoll", "timorasso", "vitovska",
    "vilana", "torbato", "premsal", "pigato", "narince", "nascetta", "neuburger",
    "mantonico", "tamianka", "tamjanika", "misket", "gros plant", "edelzwicker",
    "madeleine angevine", "irsai oliver", "rieslaner", "rivaner", "sämling",
    "siegerrebe", "ryzlink rýnský", "thrapsathiri", "tsolikouri",
    "tămâioasă românească", "xinisteri", "xynisteri", "yapincak", "zlahtina",
    "marawi", "jampal", "loin de l'oeil", "moscadello", "debit", "dafni",
    "catalanesca", "biancale", "asprinio", "athiri", "altesse", "ansonica",
    "cococciola", "emir", "feteasca", "feteascǎ regalǎ", "paralleda",
    "rolle", "petit courbu", "cercial", "aidani", "caprettone",
    # generic white colour markers used as bare words in this dataset
    "bianco", "bianca", "blanc", "blanca", "blanco", "white",
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

N_CARD_COLUMNS = 3  # how many wine cards sit side by side per row

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
    section[data-testid="stSidebar"] {
        background-color: #FBF7F2;
        border-right: 1px solid rgba(27, 42, 74, 0.12);
    }
    section[data-testid="stSidebar"] h2 {
        color: #1B2A4A;
    }
    div[data-testid="stHorizontalBlock"] {
        align-items: stretch;
    }
    div[data-testid="column"] {
        display: flex;
        flex-direction: column;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-testid="stVerticalBlock"]) {
        height: 100%;
        box-sizing: border-box;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div > div[data-testid="stVerticalBlock"] {
        height: 100%;
        min-height: 300px;
        display: flex;
        flex-direction: column;
    }
    .wine-title {
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
        line-height: 1.25;
        margin-bottom: 0.15rem;
    }
    .wine-meta {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        display: block;
    }
    .header-spacer {
        margin-bottom: 2.25rem;
    }
    .glass-rating {
        letter-spacing: 0.15em;
    }
    .glass-rating .filled {
        opacity: 1;
    }
    .glass-rating .empty {
        opacity: 0.22;
        filter: grayscale(100%);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _matches_any_variety_keyword(v: str, keywords: set) -> bool:
    """Word-boundary substring match, so e.g. 'noir' doesn't match inside an unrelated word."""
    return any(re.search(rf"\b{re.escape(kw)}\b", v) for kw in keywords)


def get_variety_color(variety: str) -> str:
    """
    Best-effort color classification based on variety name, covering 4
    categories (checked in this priority order): sparkling, rosé, red,
    white. Falls back to NEUTRAL_COLOR if nothing matches.
    """
    if not variety:
        return NEUTRAL_COLOR
    v = variety.lower().strip()
    if _matches_any_variety_keyword(v, SPARKLING_COLOR_VARIETIES):
        return SPARKLING_WINE_COLOR
    if _matches_any_variety_keyword(v, ROSE_COLOR_VARIETIES):
        return ROSE_WINE_COLOR
    if _matches_any_variety_keyword(v, RED_COLOR_VARIETIES):
        return RED_WINE_COLOR
    if _matches_any_variety_keyword(v, WHITE_COLOR_VARIETIES):
        return WHITE_WINE_COLOR
    return NEUTRAL_COLOR


def points_to_glasses(points) -> str:
    """
    Map an 80-100 point score to a 1-5 wine-glass display (matching the 🍷
    used in the header), using buckets tuned to this dataset's actual
    distribution (most wines score 85-92), so the common range spreads
    across more of the scale. Returns HTML: filled glasses at full opacity,
    unfilled glasses dimmed.
    """
    try:
        points = float(points)
    except (TypeError, ValueError):
        return ""

    if points >= 95:
        filled = 5
    elif points >= 90:
        filled = 4
    elif points >= 87:
        filled = 3
    elif points >= 84:
        filled = 2
    else:
        filled = 1

    glasses = "".join(
        f"<span class='{'filled' if i < filled else 'empty'}'>🍷</span>"
        for i in range(5)
    )
    return f"<span class='glass-rating'>{glasses}</span>"


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


def render_filters_sidebar() -> dict:
    """
    Render the filters in a sidebar that's always visible. Each filter is
    behind a checkbox so an untouched field is genuinely omitted from the
    request, rather than sending a misleading 0/blank value as a real
    constraint. Returns a filters dict with only the enabled fields set
    (or {} if none).
    """
    filters = {}

    with st.sidebar:
        st.markdown(f"<h2 style='color:{NAVY};'>🔎 Filters</h2>", unsafe_allow_html=True)
        st.caption("Narrow down your recommendations (all optional).")

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


def format_price(price) -> str:
    """Format a price with no decimal places (rounds to the nearest dollar)."""
    try:
        return f"{round(float(price)):,}"
    except (TypeError, ValueError):
        return str(price) if price is not None else "?"


def render_wine_card(wine: dict):
    """Render a single wine as a color-coded card with a wine-glass rating."""
    color = get_variety_color(wine.get("variety", ""))
    glasses = points_to_glasses(wine.get("points"))
    title = to_title_case(wine.get("title", "Unknown wine"))
    variety = to_title_case(wine.get("variety", ""))
    country = to_title_case_country(wine.get("country", ""))
    description = to_sentence_case(wine.get("description", ""))
    price = format_price(wine.get("price"))

    with st.container(border=True):
        st.markdown(
            f"<h4 class='wine-title' style='color:{color};' title='{title}'>{title}</h4>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<span class='wine-meta'>"
            f"<span style='color:{color};'>**{variety}**</span> · "
            f"{country} · ${price}</span>"
            f"<span class='wine-meta'>{glasses} "
            f"<span style='color:{color};'>({wine.get('points', '?')} pts)</span></span>",
            unsafe_allow_html=True,
        )
        if description:
            with st.expander("Read description"):
                st.write(description)
        if "similarity" in wine:
            try:
                match_pct = f"{float(wine['similarity']) * 100:.0f}%"
            except (TypeError, ValueError):
                match_pct = wine["similarity"]
            st.caption(f"Match score: {match_pct} · id: {wine.get('wine_id')}")


def render_recommendations(results):
    """Display recommended wines as cards, laid out side by side."""
    if not results:
        st.info("No matching wines found. Try a different name/id, property, or loosen your filters.")
        return

    for row_start in range(0, len(results), N_CARD_COLUMNS):
        row_wines = results[row_start:row_start + N_CARD_COLUMNS]
        cols = st.columns(N_CARD_COLUMNS)
        for col, wine in zip(cols, row_wines):
            with col:
                render_wine_card(wine)


def main():
    filters = render_filters_sidebar()

    st.markdown(
        f"<h1 style='color:{NAVY}; text-align:center;'>🍷 WineMatch</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='header-spacer' style='text-align:center; font-size:1.15em; font-weight:500;'>"
        "Describe what you're craving, or point to a wine you love — we'll pour the closest match."
        "</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='font-style: italic; font-size: 1.05em; text-align:center;'>"
        "Enter a wine's name, optionally followed by a <code>+</code> and a quality you're after — "
        "price or rating (<em>low price</em>, <em>high rating</em>), or style (<em>sweet</em>, "
        "<em>fruity</em>, <em>high alcohol</em>). For example: "
        "<em>Ornellaia 2014 Le Volte Red + sweet and fruity</em>, or <em>109 + low price</em>. "
        "For precise constraints, such as an exact price range, use the <strong>Filters</strong> in the sidebar."
        "</p>",
        unsafe_allow_html=True,
    )

    query = st.text_input("Please enter your search here:", placeholder="Ornellaia 2014 Le Volte Red + sweet and fruity")
    top_k = st.slider("Number of recommendations", 1, 20, 5)

    if st.button("🍷 Uncork", type="primary") and query.strip():
        with st.spinner("Finding wines... this can take a moment on first use."):
            try:
                results = call_recommend_api(query, top_k, filters)
                render_recommendations(results)
            except requests.RequestException as e:
                st.error(f"Could not reach the API: {e}")


if __name__ == "__main__":
    main()
