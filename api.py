"""
FastAPI app exposing the wine recommender.

Run with: uvicorn api:app --host 0.0.0.0 --port 8000
"""

import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

print("DEBUG USE_MOCK_MODEL =", repr(os.getenv("USE_MOCK_MODEL")))

if os.getenv("USE_MOCK_MODEL", "false").lower() == "true":
    import mock_model as model
else:
    import model

ARTIFACTS_DIR = os.environ.get("ARTIFACTS_DIR", "artifacts")

app = FastAPI(title="WineMatch API")


class Filters(BaseModel):
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    variety: Optional[str] = None
    country: Optional[str] = None
    min_points: Optional[int] = None


class RecommendRequest(BaseModel):
    query: str  # e.g. "Ornellaia 2014 Le Volte Red + low price" or "109 + low price"
    top_k: int = 5
    filters: Optional[Filters] = None


@app.on_event("startup")
def startup_event():
    """Load recommender artifacts (index, metadata, SBERT model) into memory."""
    model.load_artifacts(ARTIFACTS_DIR)


@app.post("/recommend")
def recommend(request: RecommendRequest):
    """
    Single search-box endpoint. `query` is a wine name or wine_id, optionally
    followed by "+ desired property" (e.g. "+ low price", "+ high rating").
    """
    filters = request.filters.dict() if request.filters else None
    results = model.recommend(request.query, top_k=request.top_k, filters=filters)
    return results.to_dict(orient="records")


@app.get("/wines/{wine_id}")
def get_wine(wine_id: int):
    """Return details for a single wine by id."""
    wine = model.get_wine_by_id(wine_id)
    if wine is None:
        raise HTTPException(status_code=404, detail=f"Wine id {wine_id} not found")
    return wine


@app.get("/version")
def version():
    """Return model/version/build info."""
    return model.get_version_info(ARTIFACTS_DIR)
