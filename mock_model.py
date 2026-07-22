"""
Mock model layer — fake data so the UI/API can be developed and tested
independently of the real SBERT/FAISS implementation in model.py.
Toggle with USE_MOCK_MODEL=true.
"""

import pandas as pd

_FAKE_WINES = pd.DataFrame([
    {"wine_id": 1, "title": "Ornellaia 2014 Le Volte Red", "price": 45, "points": 91, "variety": "Red Blend", "country": "Italy"},
    {"wine_id": 2, "title": "Cheap Chianti Classico", "price": 15, "points": 85, "variety": "Sangiovese", "country": "Italy"},
    {"wine_id": 3, "title": "Fancy Napa Cabernet", "price": 120, "points": 96, "variety": "Cabernet Sauvignon", "country": "USA"},
])


def load_artifacts(artifacts_dir: str) -> None:
    print(f"[MOCK] Skipping real artifact load from {artifacts_dir}")


def recommend(query: str, top_k: int = 5, filters: dict = None) -> pd.DataFrame:
    print(f"[MOCK] recommend() called with query={query!r}, top_k={top_k}, filters={filters}")
    return _FAKE_WINES.head(top_k)


def get_wine_by_id(wine_id: int):
    row = _FAKE_WINES[_FAKE_WINES["wine_id"] == wine_id]
    return row.iloc[0].to_dict() if not row.empty else None


def get_version_info(artifacts_dir: str) -> dict:
    return {"version": "mock", "model_name": "mock-sbert"}
