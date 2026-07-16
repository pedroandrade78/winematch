"""
Unit tests: data engineering, recommendation logic, and API endpoints.
Run with: pytest tests.py -v

These tests use small synthetic data and a hand-built FakeModel (instead
of the real SBERT model), so they run offline without downloading
anything or needing the real 130k-row dataset. The FakeModel maps a
handful of known phrases to fixed vectors so we can test that:
  - structured (price/rating) modifiers are classified by embedding
    similarity, including synonyms that are NOT in the literal anchor text
  - anything else is treated as a free-form semantic style modifier and
    blended into the query vector
"""

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import data_engineering as de
import model


# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------

@pytest.fixture
def raw_df():
    return pd.DataFrame({
        "country": ["US", "US", None, "France"],
        "description": [
            "A rich, dry red with blackberry notes.",
            "A rich, dry red with blackberry notes.",  # duplicate
            "Crisp white with citrus and mineral notes.",
            None,  # missing description -> should be dropped
        ],
        "designation": [None, None, "Reserve", "Grand Cru"],
        "points": [90, 90, 88, np.nan],
        "price": [25.0, 25.0, 15.0, np.nan],  # last row missing price -> dropped
        "province": ["California", "California", "Oregon", "Burgundy"],
        "region_1": ["Napa", "Napa", "Willamette", None],
        "region_2": ["Napa", "Napa", None, None],
        "taster_name": ["Alice", "Alice", None, "Bob"],
        "taster_twitter_handle": ["@alice", "@alice", None, "@bob"],
        "title": ["Ornellaia 2014 Le Volte Red", "Ornellaia 2014 Le Volte Red",
                  "Winery B White 2019", "Winery C 2020"],
        "variety": ["Cabernet Sauvignon", "Cabernet Sauvignon", "Pinot Gris", "Pinot Noir"],
        "winery": ["Winery A", "Winery A", "Winery B", "Winery C"],
    })


@pytest.fixture
def clean_metadata():
    """A small pre-built metadata table, as if produced by data_engineering.run_pipeline."""
    return pd.DataFrame({
        "wine_id": [0, 1, 2],
        "title": ["Ornellaia 2014 Le Volte Red", "Sweet Fruity Rose", "Dry Tannic Red"],
        "description": ["desc a", "desc b", "desc c"],
        "text_corpus": ["text a", "text b", "text c"],
        "variety": ["Cabernet Sauvignon", "Rose", "Cabernet Sauvignon"],
        "country": ["US", "US", "France"],
        "region": ["Napa", "Napa", "Bordeaux"],
        "price": [80.0, 20.0, 50.0],
        "points": [95, 88, 92],
        "taster_name": ["Alice", "Bob", "Alice"],
    })


def _make_fake_model(vector_map, dim=4):
    """
    A fake SBERT model: looks up known phrases in vector_map (normalized),
    falls back to a tiny generic vector for anything unrecognized.
    """
    def lookup(text):
        v = vector_map.get(text, np.ones(dim) * 0.01)
        v = np.asarray(v, dtype="float32")
        return v / np.linalg.norm(v)

    class FakeModel:
        def encode(self, texts, normalize_embeddings=True):
            return np.array([lookup(t) for t in texts])

    return FakeModel()


@pytest.fixture
def anchor_vector_map():
    """Fixed vectors for the real anchor texts, plus some synonym phrases not in that text."""
    return {
        model.STRUCTURED_ANCHORS["price_low"]["text"]: [1.0, 0.0, 0.0, 0.0],
        model.STRUCTURED_ANCHORS["price_high"]["text"]: [-1.0, 0.0, 0.0, 0.0],
        model.STRUCTURED_ANCHORS["rating_high"]["text"]: [0.0, 1.0, 0.0, 0.0],
        model.STRUCTURED_ANCHORS["rating_low"]["text"]: [0.0, -1.0, 0.0, 0.0],
        "cheap": [0.95, 0.0, 0.05, 0.0],              # synonym, not literally in anchor text
        "affordable please": [0.9, 0.0, 0.1, 0.0],    # paraphrase
        "sweet and fruity": [0.0, 0.0, 1.0, 0.0],     # unrelated to price/rating
        "high alcohol": [0.0, 0.0, 0.0, 1.0],         # unrelated to price/rating
    }


# ---------------------------------------------------------------------
# data engineering
# ---------------------------------------------------------------------

def test_report_missing_values(raw_df):
    summary = de.report_missing_values(raw_df)
    assert "TOTAL" in summary.index
    assert summary.loc["country", "NaN_count"] == 1
    assert summary.loc["description", "NaN_count"] == 1


def test_drop_duplicates(raw_df):
    result = de.drop_duplicates(raw_df)
    assert len(result) == 3


def test_drop_columns(raw_df):
    result = de.drop_columns(raw_df)
    for col in ["region_2", "taster_twitter_handle", "winery"]:
        assert col not in result.columns
    assert "region_1" in result.columns  # untouched, not merged


def test_handle_missing_values(raw_df):
    deduped = de.drop_duplicates(raw_df)
    dropped = de.drop_columns(deduped)
    result = de.handle_missing_values(dropped)
    assert result["description"].isna().sum() == 0
    assert result["price"].isna().sum() == 0
    assert (result["country"] == "Unknown").sum() >= 1


def test_build_text_corpus_no_winery():
    df = pd.DataFrame({
        "description": ["Tastes great"],
        "variety": ["Merlot"],
        "region_1": ["Napa"],
    })
    corpus = de.build_text_corpus(df)
    assert "Tastes great" in corpus.iloc[0]
    assert "Merlot" in corpus.iloc[0]
    assert "Napa" in corpus.iloc[0]
    assert "Winery" not in corpus.iloc[0]


def test_run_pipeline_end_to_end(raw_df, tmp_path):
    raw_path = tmp_path / "raw.csv"
    raw_df.to_csv(raw_path)

    result = de.run_pipeline(str(raw_path))

    assert "wine_id" in result.columns
    assert "text_corpus" in result.columns
    assert "region" in result.columns
    for col in ["region_2", "taster_twitter_handle", "winery", "region_1"]:
        assert col not in result.columns
    assert result["description"].isna().sum() == 0
    assert result["price"].isna().sum() == 0
    assert len(result) == 2


# ---------------------------------------------------------------------
# structured modifier classification (price/rating, via SBERT similarity)
# ---------------------------------------------------------------------

def test_classify_structured_modifier_synonym_cheap(monkeypatch, anchor_vector_map):
    monkeypatch.setattr(model, "_model", _make_fake_model(anchor_vector_map))
    result = model.classify_structured_modifier("cheap")
    assert result == ("price", True)


def test_classify_structured_modifier_paraphrase(monkeypatch, anchor_vector_map):
    monkeypatch.setattr(model, "_model", _make_fake_model(anchor_vector_map))
    result = model.classify_structured_modifier("affordable please")
    assert result == ("price", True)


def test_classify_structured_modifier_unrelated_style(monkeypatch, anchor_vector_map):
    monkeypatch.setattr(model, "_model", _make_fake_model(anchor_vector_map))
    assert model.classify_structured_modifier("sweet and fruity") is None
    assert model.classify_structured_modifier("high alcohol") is None


def test_parse_query_price_threshold(monkeypatch, anchor_vector_map):
    monkeypatch.setattr(model, "_model", _make_fake_model(anchor_vector_map))
    identifier, modifiers = model.parse_query("109 + under 30")
    assert identifier == "109"
    assert modifiers["hard_filters"]["price_max"] == 30.0


def test_parse_query_semantic_modifier_passthrough(monkeypatch, anchor_vector_map):
    monkeypatch.setattr(model, "_model", _make_fake_model(anchor_vector_map))
    identifier, modifiers = model.parse_query("Pinot Noir + sweet and fruity")
    assert identifier == "Pinot Noir"
    assert modifiers["sort_by"] is None
    assert modifiers["semantic_modifier"] == "sweet and fruity"


def test_parse_query_no_modifier(monkeypatch, anchor_vector_map):
    monkeypatch.setattr(model, "_model", _make_fake_model(anchor_vector_map))
    identifier, modifiers = model.parse_query("Pinot Noir")
    assert identifier == "Pinot Noir"
    assert modifiers["sort_by"] is None
    assert modifiers["semantic_modifier"] is None


# ---------------------------------------------------------------------
# recommendation logic (unified recommend())
# ---------------------------------------------------------------------

def test_apply_filters_price_range(clean_metadata):
    result = model.apply_filters(clean_metadata, {"price_min": 30, "price_max": 100})
    assert set(result["wine_id"]) == {0, 2}


def test_apply_filters_variety(clean_metadata):
    result = model.apply_filters(clean_metadata, {"variety": "rose"})
    assert set(result["wine_id"]) == {1}


def test_build_faiss_index_and_search():
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0], [0.7, 0.7]], dtype="float32")
    index = model.build_faiss_index(embeddings)
    scores, indices = model.search_index(index, np.array([1.0, 0.0]), top_k=2)
    assert indices[0] == 0


@pytest.fixture
def loaded_model_with_style(monkeypatch, clean_metadata, anchor_vector_map):
    """
    4D wine embeddings where wine 1 ('Sweet Fruity Rose') strongly represents
    a 'sweet/fruity' style axis, and wine 2 ('Dry Tannic Red') is generic/dry.
    """
    embeddings = np.array([
        [1.0, 0.0, 0.0, 0.0],   # wine 0: generic
        [0.3, 0.0, 0.95, 0.0],  # wine 1: sweet & fruity
        [0.9, 0.0, 0.1, 0.0],   # wine 2: dry/tannic
    ], dtype="float32")
    for i in range(len(embeddings)):
        embeddings[i] /= np.linalg.norm(embeddings[i])
    index = model.build_faiss_index(embeddings)

    monkeypatch.setattr(model, "_index", index)
    monkeypatch.setattr(model, "_metadata", clean_metadata)
    monkeypatch.setattr(model, "_model", _make_fake_model(anchor_vector_map))
    monkeypatch.setattr(model, "MODIFIER_BLEND_WEIGHT", 0.6)  # strong pull, for a clear test
    return index


def test_recommend_price_modifier_via_synonym(loaded_model_with_style):
    # "cheap" isn't in the literal anchor text -- must be classified via embedding similarity
    results = model.recommend("Ornellaia 2014 Le Volte Red + cheap", top_k=2)
    assert 0 not in set(results["wine_id"])
    prices = results["price"].tolist()
    assert prices == sorted(prices)


def test_recommend_semantic_style_modifier_reranks(loaded_model_with_style):
    # without a modifier, the dry/tannic wine (2) should rank above the sweet one (1)
    plain = model.recommend("Ornellaia 2014 Le Volte Red", top_k=2)
    assert plain.iloc[0]["wine_id"] == 2

    # with "+ sweet and fruity", the sweet wine (1) should now rank first instead
    styled = model.recommend("Ornellaia 2014 Le Volte Red + sweet and fruity", top_k=2)
    assert styled.iloc[0]["wine_id"] == 1


def test_recommend_by_id_with_style_modifier(loaded_model_with_style):
    results = model.recommend("0 + sweet and fruity", top_k=2)
    assert 0 not in set(results["wine_id"])
    assert results.iloc[0]["wine_id"] == 1


def test_get_wine_by_id(monkeypatch, clean_metadata):
    monkeypatch.setattr(model, "_metadata", clean_metadata)
    wine = model.get_wine_by_id(1)
    assert wine["title"] == "Sweet Fruity Rose"
    assert model.get_wine_by_id(999) is None


# ---------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------

@pytest.fixture
def api_client(loaded_model_with_style, monkeypatch):
    import api  # import here so monkeypatching model happens before startup logic runs

    monkeypatch.setattr(
        model, "get_version_info",
        lambda artifacts_dir: {"model_name": "fake", "num_wines": 3, "embedding_dim": 4},
    )
    api.app.router.on_startup.clear()  # skip real artifact loading from disk
    return TestClient(api.app)


def test_recommend_endpoint_with_style_modifier(api_client):
    response = api_client.post(
        "/recommend", json={"query": "Ornellaia 2014 Le Volte Red + sweet and fruity", "top_k": 2}
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) <= 2
    assert results[0]["wine_id"] == 1


def test_get_wine_by_id_endpoint(api_client):
    response = api_client.get("/wines/1")
    assert response.status_code == 200
    assert response.json()["title"] == "Sweet Fruity Rose"


def test_get_wine_by_id_not_found(api_client):
    response = api_client.get("/wines/999")
    assert response.status_code == 404


def test_version_endpoint(api_client):
    response = api_client.get("/version")
    assert response.status_code == 200
    assert response.json()["model_name"] == "fake"
