"""
Model layer: SBERT embeddings, FAISS similarity search, and a single
recommend() function that powers one search box.

Query syntax (one search box, "+" separates the wine reference from
a desired property):
    "Ornellaia 2014 Le Volte Red + low price"
    "109 + low price"                (109 = wine_id)
    "Pinot Noir + sweet and fruity"
    "109 + high alcohol"
    "109 + under 30"

Modifiers are handled two ways:
  - price / rating direction: classified via SBERT similarity against a
    couple of short anchor phrases (not a fixed literal keyword list --
    synonyms like "budget-friendly" or "affordable" match the same
    anchor as "cheap" because the *embedding* is compared, not the text).
  - anything else (sweet, fruity, oaky, high alcohol, tannic, crisp...):
    embedded and blended into the query vector itself, so the similarity
    search is naturally pulled toward wines whose descriptions match
    that style. No fixed vocabulary needed for this part at all.
"""
import difflib
import json
import os
import re

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# in-memory state, populated by load_artifacts()
_index = None
_metadata = None
_model = None

# Short anchor phrases used only to *classify* whether a modifier is about
# price or rating direction (structured columns SBERT can't infer from
# text alone). Everything that doesn't match one of these closely is
# treated as a free-form semantic style modifier instead.
STRUCTURED_ANCHORS = {
    "price_low": {
        "text": "cheap inexpensive low price budget affordable value wine",
        "column": "price", "ascending": True,
    },
    "price_high": {
        "text": "expensive high price premium luxury costly splurge wine",
        "column": "price", "ascending": False,
    },
    "rating_high": {
        "text": "highly rated top rated best rated high score critically acclaimed",
        "column": "points", "ascending": False,
    },
    "rating_low": {
        "text": "low rated poorly rated bad reviews weak score",
        "column": "points", "ascending": True,
    },
}
STRUCTURED_MATCH_THRESHOLD = 0.5
MODIFIER_BLEND_WEIGHT = 0.35  # how much the semantic modifier shifts the query vector


# ---------------------------------------------------------------------
# embeddings + index
# ---------------------------------------------------------------------

def load_sbert_model(model_name: str = MODEL_NAME) -> SentenceTransformer:
    """Load a pretrained sentence-transformers model."""
    return SentenceTransformer(model_name, local_files_only=True)


def generate_embeddings(texts: pd.Series, model: SentenceTransformer) -> np.ndarray:
    """Encode a series of text into a normalized (n_samples, embedding_dim) array."""
    embeddings = model.encode(
        texts.tolist(),
        show_progress_bar=True,
        normalize_embeddings=True,  # so inner product == cosine similarity
    )
    return np.asarray(embeddings, dtype="float32")


def build_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    """Build a flat inner-product FAISS index (cosine similarity, since embeddings are normalized)."""
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index


def search_index(index: faiss.Index, query_vector: np.ndarray, top_k: int = 5):
    """Return (scores, indices) of the top_k nearest neighbours to query_vector."""
    query_vector = np.asarray(query_vector, dtype="float32").reshape(1, -1)
    scores, indices = index.search(query_vector, top_k)
    return scores[0], indices[0]


def _embed_text(text: str) -> np.ndarray:
    """Embed a single piece of text using the loaded SBERT model."""
    return np.asarray(_model.encode([text], normalize_embeddings=True)[0])


# ---------------------------------------------------------------------
# query parsing ("wine name or id" + "property")
# ---------------------------------------------------------------------

def classify_structured_modifier(modifier_text: str, threshold: float = STRUCTURED_MATCH_THRESHOLD):
    """
    Check whether modifier_text is really about price/rating direction, by
    comparing its embedding to a few anchor phrases -- not literal keyword
    matching, so synonyms and rephrasings are picked up automatically.
    Returns (column, ascending) or None if it doesn't match closely enough.
    """
    anchor_items = list(STRUCTURED_ANCHORS.items())
    anchor_texts = [info["text"] for _, info in anchor_items]

    vectors = _model.encode(anchor_texts + [modifier_text], normalize_embeddings=True)
    anchor_vecs, query_vec = np.asarray(vectors[:-1]), np.asarray(vectors[-1])

    scores = anchor_vecs @ query_vec
    best_idx = int(np.argmax(scores))

    if scores[best_idx] >= threshold:
        _, info = anchor_items[best_idx]
        return info["column"], info["ascending"]
    return None


def parse_query(raw_query: str):
    """
    Split a single search-box query on '+' into:
      - identifier: a wine name/description, or a wine_id (digits only)
      - modifiers: {
            "sort_by": col or None, "ascending": bool or None,
            "hard_filters": {...},
            "semantic_modifier": free-form style text or None,
        }
    """
    parts = [p.strip() for p in raw_query.split("+")]
    identifier = parts[0]
    modifier_text = " ".join(parts[1:]).strip()

    modifiers = {"sort_by": None, "ascending": None, "hard_filters": {}, "semantic_modifier": None}
    if not modifier_text:
        return identifier, modifiers

    m = re.search(r"under \$?(\d+(\.\d+)?)", modifier_text, re.IGNORECASE)
    if m:
        modifiers["hard_filters"]["price_max"] = float(m.group(1))

    m = re.search(r"over \$?(\d+(\.\d+)?)", modifier_text, re.IGNORECASE)
    if m:
        modifiers["hard_filters"]["price_min"] = float(m.group(1))

    m = re.search(r"(\d+)\+?\s*points", modifier_text, re.IGNORECASE)
    if m:
        modifiers["hard_filters"]["min_points"] = int(m.group(1))

    structured = classify_structured_modifier(modifier_text)
    if structured:
        modifiers["sort_by"], modifiers["ascending"] = structured
    else:
        # not about price/rating -> treat as a descriptive style modifier
        # (sweet, fruity, oaky, high alcohol, tannic, crisp, ...)
        modifiers["semantic_modifier"] = modifier_text

    return identifier, modifiers



MAX_RESULTS_PER_WINERY = 2  # cap so one winery/vineyard doesn't fill the whole results list


def diversify_by_winery(candidates: pd.DataFrame, top_k: int, max_per_winery: int = MAX_RESULTS_PER_WINERY) -> pd.DataFrame:
    """
    Keep results in similarity order, but cap how many wines from the same
    winery can appear, so results feel varied instead of e.g. 5 vintages of
    the same wine. Candidates must already be sorted by relevance.
    """
    if "winery" not in candidates.columns:
        return candidates.head(top_k)

    counts = {}
    keep_rows = []
    for _, row in candidates.iterrows():
        winery = row.get("winery")
        seen = counts.get(winery, 0)
        if seen < max_per_winery:
            keep_rows.append(row)
            counts[winery] = seen + 1
        if len(keep_rows) >= top_k:
            break

    if not keep_rows:
        return candidates.head(top_k)
    return pd.DataFrame(keep_rows)




def apply_filters(candidates: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Apply optional hard filters: price_min, price_max, variety, country, min_points."""
    if not filters:
        return candidates

    df = candidates
    if filters.get("price_min") is not None:
        df = df[df["price"] >= filters["price_min"]]
    if filters.get("price_max") is not None:
        df = df[df["price"] <= filters["price_max"]]
    if filters.get("variety"):
        df = df[df["variety"].str.lower() == filters["variety"].lower()]
    if filters.get("country"):
        df = df[df["country"].str.lower() == filters["country"].lower()]
    if filters.get("min_points") is not None:
        df = df[df["points"] >= filters["min_points"]]

    return df


FUZZY_MATCH_CUTOFF = 0.6  # 0-1, higher = stricter. Tolerates small typos, not wildly different text.


def _fuzzy_title_match(identifier: str):
    """
    Find the closest wine title to `identifier` using approximate string
    matching (no extra dependency -- uses Python's built-in difflib), so a
    small typo like "Onelaia" still finds "Ornellaia". Returns the row
    position in _metadata, or None if nothing is close enough.
    """
    titles = _metadata["title"].astype(str)
    close = difflib.get_close_matches(identifier.lower(), titles.str.lower(), n=1, cutoff=FUZZY_MATCH_CUTOFF)
    if not close:
        return None

    match_pos = titles.str.lower().tolist().index(close[0])
    return match_pos


def _pick_best_title_match(identifier: str, title_matches: pd.DataFrame) -> int:
    """
    When several titles contain `identifier` as a substring, picking the
    first one by row position is arbitrary (depends on original CSV order,
    not relevance). Instead, prefer the title whose length is closest to
    the identifier's -- e.g. searching "Ornellaia 2014" should prefer an
    exact-ish title match over a much longer, less specific one. Ties are
    broken by keeping the first occurrence (stable).
    Returns a row position (not wine_id).
    """
    lengths = title_matches["title"].str.len()
    closeness = (lengths - len(identifier)).abs()
    best_local_pos = closeness.values.argmin()
    return int(title_matches.index[best_local_pos])





def _resolve_query_vector(identifier: str, semantic_modifier: str = None):
    """
    Turn the identifier (+ optional semantic style modifier) into a query
    vector, and return (vector, exclude_wine_id).
    - digits only -> treat as wine_id, use its stored embedding
    - otherwise -> try a title substring match; fall back to embedding the raw text
    A semantic_modifier (e.g. "sweet and fruity") is embedded separately and
    blended into the base vector so the search is pulled toward that style.
    """
    identifier = identifier.strip()
    exclude_id = None
    base_vector = None

    if identifier.isdigit():
        wine_id = int(identifier)
        matches = _metadata.index[_metadata["wine_id"] == wine_id]
        if len(matches) > 0:
            row_pos = int(matches[0])
            base_vector = _index.reconstruct(row_pos)
            exclude_id = wine_id

    if base_vector is None:
        title_matches = _metadata[_metadata["title"].str.contains(identifier, case=False, na=False)]
        if not title_matches.empty:
            row_pos = int(title_matches.index[0])
            base_vector = _index.reconstruct(row_pos)
            exclude_id = int(title_matches.iloc[0]["wine_id"])

    if base_vector is None:
        base_vector = _embed_text(identifier)

    if semantic_modifier:
        mod_vector = _embed_text(semantic_modifier)
        combined = (1 - MODIFIER_BLEND_WEIGHT) * np.asarray(base_vector) + MODIFIER_BLEND_WEIGHT * mod_vector
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined = combined / norm
        return combined, exclude_id

    return base_vector, exclude_id


# ---------------------------------------------------------------------
# recommend (single entry point for both name-based and id-based queries)
# ---------------------------------------------------------------------

def recommend(query: str, top_k: int = 5, filters: dict = None) -> pd.DataFrame:
    """
    Single search-box entry point.
    `query` can be a wine name/description, a wine_id, and optionally a
    "+ property" modifier, e.g. "Ornellaia 2014 + sweet and fruity" or
    "109 + low price".
    `filters` (optional) are hard filters that override/extend parsed modifiers.
    """
    if _index is None or _metadata is None or _model is None:
        raise RuntimeError("Artifacts not loaded. Call load_artifacts() first.")

    identifier, modifiers = parse_query(query)
    query_vector, exclude_id = _resolve_query_vector(identifier, modifiers["semantic_modifier"])

    fetch_k = max(top_k * 5, 20)
    scores, indices = search_index(_index, query_vector, top_k=fetch_k)

    valid = indices >= 0
    candidates = _metadata.iloc[indices[valid]].copy()
    candidates["similarity"] = scores[valid]

    if exclude_id is not None:
        candidates = candidates[candidates["wine_id"] != exclude_id]

    combined_filters = {**modifiers["hard_filters"], **(filters or {})}
    candidates = apply_filters(candidates, combined_filters)

    if modifiers["sort_by"]:
        # Explicit sort requested (e.g. "low price") -- respect it exactly,
        # diversification would fight against what the user asked for.
        candidates = candidates.sort_values(modifiers["sort_by"], ascending=modifiers["ascending"])
        return candidates.head(top_k)

    candidates = candidates.sort_values("similarity", ascending=False)
    return diversify_by_winery(candidates, top_k)


# ---------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------

def build_model(df: pd.DataFrame, artifacts_dir: str, model_name: str = MODEL_NAME) -> None:
    """Full model pipeline: embed text_corpus -> build FAISS index -> save artifacts."""
    model = load_sbert_model(model_name)
    embeddings = generate_embeddings(df["text_corpus"], model)
    index = build_faiss_index(embeddings)
    save_artifacts(index, df, artifacts_dir, model_name=model_name)


def save_artifacts(index: faiss.Index, metadata: pd.DataFrame, artifacts_dir: str, model_name: str = MODEL_NAME) -> None:
    """Persist FAISS index, metadata table, and version info to disk."""
    os.makedirs(artifacts_dir, exist_ok=True)

    faiss.write_index(index, os.path.join(artifacts_dir, "index.faiss"))
    metadata.to_parquet(os.path.join(artifacts_dir, "metadata.parquet"), index=False)

    version_info = {
        "model_name": model_name,
        "num_wines": len(metadata),
        "embedding_dim": index.d,
    }
    with open(os.path.join(artifacts_dir, "version.json"), "w") as f:
        json.dump(version_info, f, indent=2)


def load_artifacts(artifacts_dir: str) -> None:
    """Load FAISS index, metadata table, and SBERT model into module-level state for serving."""
    global _index, _metadata, _model

    with open(os.path.join(artifacts_dir, "version.json")) as f:
        version_info = json.load(f)

    _model = load_sbert_model(version_info["model_name"])
    _metadata = pd.read_parquet(os.path.join(artifacts_dir, "metadata.parquet"))
    _index = faiss.read_index(os.path.join(artifacts_dir, "index.faiss"))

def load_local_artifacts(artifacts_dir: str) -> None:
    """Load FAISS index, metadata table, and SBERT model into module-level state for serving."""

    _metadata = pd.read_parquet(os.path.join(artifacts_dir, "metadata.parquet"))
    _index = faiss.read_index(os.path.join(artifacts_dir, "index.faiss"))
    return _index, _metadata



def get_version_info(artifacts_dir: str) -> dict:
    """Read the persisted version/build info."""
    with open(os.path.join(artifacts_dir, "version.json")) as f:
        return json.load(f)


def search_titles(query: str, limit: int = 8) -> list:
    """
    Return up to `limit` wine titles that contain `query` (case-insensitive),
    for a type-ahead autocomplete box. Requires load_artifacts() to have
    been called.
    """
    if _metadata is None:
        raise RuntimeError("Artifacts not loaded. Call load_artifacts() first.")

    matches = _metadata[_metadata["title"].str.contains(query, case=False, na=False)]
    return matches["title"].head(limit).tolist()



def get_wine_by_id(wine_id: int) -> dict:
    """Look up a single wine's metadata by id. Requires load_artifacts() to have been called."""
    if _metadata is None:
        raise RuntimeError("Artifacts not loaded. Call load_artifacts() first.")

    row = _metadata[_metadata["wine_id"] == wine_id]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


if __name__ == "__main__":
    from data_engineering import run_pipeline

    df = run_pipeline("raw_data/winemag-data-130k-v2.csv")
    build_model(df, artifacts_dir="artifacts")
    print("Model artifacts saved to ./artifacts")
