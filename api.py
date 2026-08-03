"""
FastAPI app exposing the wine recommender.

Run with: uvicorn api:app --host 0.0.0.0 --port 8000
"""

import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

import model
import asyncio

print("DEBUG USE_MOCK_MODEL =", repr(os.getenv("USE_MOCK_MODEL")))

#if os.getenv("USE_MOCK_MODEL", "false").lower() == "true":
    #import mock_model as model
#else:
    #print("Importing model")
    #import model
from contextlib import asynccontextmanager

from sentence_transformers import SentenceTransformer

ARTIFACTS_DIR = os.environ.get("ARTIFACTS_DIR", "artifacts")

#app = FastAPI(title="WineMatch API")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

class Filters(BaseModel):
    price_min: Optional[float] = Field(default=None, ge=0)
    price_max: Optional[float] = Field(default=None, ge=0)
    variety: Optional[str] = None
    country: Optional[str] = None
    # The dataset's rating scale (Wine Enthusiast) runs 80-100; anything
    # outside that range can never match a wine, so reject it up front
    # instead of silently returning an empty result set.
    min_points: Optional[int] = Field(default=None, ge=80, le=100)

    @model_validator(mode="after")
    def check_price_range(self):
        if self.price_min is not None and self.price_max is not None and self.price_min > self.price_max:
            raise ValueError(f"price_min ({self.price_min}) cannot be greater than price_max ({self.price_max})")
        return self


class RecommendRequest(BaseModel):
    query: str  # e.g. "Ornellaia 2014 Le Volte Red + low price" or "109 + low price"
    top_k: int = Field(default=5, ge=1, le=100)
    filters: Optional[Filters] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading embedding model...", flush=True)

    model.load_artifacts(ARTIFACTS_DIR)
    print("Model artifacts loaded", flush=True)
    yield

    # Optional cleanup
    app.state.embedding_model = None

app = FastAPI(lifespan=lifespan)


#app.on_event("startup")
#ef startup_event():
#   """Load recommender artifacts (index, metadata, SBERT model) into memory."""
#   model.load_artifacts(ARTIFACTS_DIR)



@app.post("/recommend")
def recommend_endpoint(request: RecommendRequest):
    """
    Single search-box endpoint. `query` is a wine name or wine_id, optionally
    followed by "+ desired property" (e.g. "+ low price", "+ high rating").
    """
    filters = request.filters.dict() if request.filters else None
    results = model.recommend(request.query, top_k=request.top_k, filters=filters)
    return results.to_dict(orient="records")


@app.get("/search-titles")
def search_titles(q: str, limit: int = 8):
    """
    Autocomplete endpoint: return up to `limit` wine titles containing `q`
    (case-insensitive), for a type-ahead search box in the UI. Returns an
    empty list for a blank/short query rather than the whole catalogue.
    """
    if not q or len(q.strip()) < 2:
        return []
    return model.search_titles(q.strip(), limit=limit)


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
