"""
api_file.py

This file creates the API for the Wine Recommender project.

It uses FastAPI (https://fastapi.tiangolo.com/) which is a simple and
fast way to build APIs in Python. Every function decorated with
`@app.get(...)` becomes a URL that people (or the Streamlit frontend)
can call to get data back.

Beginner note: think of this file as the "front door" of the project.
It does NOT do any machine learning itself. It just:
  1. loads the already-trained model (FAISS index + SBERT model), and
  2. calls the `recommend()` function from model.py whenever someone
     asks for a recommendation.
"""

import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# We import our own model.py file, which lives in the same package
# (package_folder). This is where all the machine learning logic is.
from . import model


# ---------------------------------------------------------------------
# 1. Where are the trained model files stored?
#
# The "artifacts" folder contains 3 files that were created by running
# build_artifacts.py (index.faiss, metadata.parquet, version.json).
# We read the folder name from an environment variable so it is easy
# to change without touching the code, but we default to "artifacts".
# ---------------------------------------------------------------------
ARTIFACTS_DIR = os.environ.get("ARTIFACTS_DIR", "artifacts")


# ---------------------------------------------------------------------
# 2. Create the FastAPI application.
# This "app" object is what Uvicorn (the web server) will run.
# ---------------------------------------------------------------------
app = FastAPI(
    title="Wine Recommender API",
    description="A simple API that recommends wines based on a search query.",
)

# CORS = Cross-Origin Resource Sharing.
# This allows a frontend running on a different URL (like our Streamlit
# app) to call this API from a web browser. Without this, the browser
# would block the request for security reasons.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # "*" means "allow every website" (fine for a demo project)
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------
# 3. Load the model ONCE, when the API starts.
#
# Loading the SBERT model and the FAISS index takes a few seconds, so
# we must NOT do it inside every request (that would be very slow).
# FastAPI's "startup" event runs exactly once, right when the server
# boots up.
# ---------------------------------------------------------------------
@app.on_event("startup")
def load_model_artifacts():
    print(f"⏳ Loading model artifacts from '{ARTIFACTS_DIR}' ...")
    model.load_artifacts(ARTIFACTS_DIR)
    print("✅ Model artifacts loaded. API is ready!")


# ---------------------------------------------------------------------
# 4. Root endpoint ("/").
# This is just a simple health check so you can verify the API is
# alive by opening the URL in a browser.
# run:
# uvicorn mush_package.api_file:app --reload
# ---------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Welcome to the Wine Recommender API 🍷. Go to /docs to try it out."}


# ---------------------------------------------------------------------
# 5. Recommendation endpoint ("/recommend").
#
# This is the main endpoint. Example calls:
#   /recommend?query=109 + low price
#   /recommend?query=Pinot Noir + sweet and fruity&top_k=10
#   /recommend?query=Ornellaia&country=italy&price_max=50
# ---------------------------------------------------------------------
@app.get("/recommend")
def get_recommendations(
    query: str = Query(
        ...,  # "..." means this parameter is required
        description="Wine name, wine_id, or free text. You can add "
                     "'+ a property' e.g. '109 + low price'.",
    ),
    top_k: int = Query(5, ge=1, le=50, description="How many results to return"),
    variety: Optional[str] = Query(None, description="Exact variety filter, e.g. 'pinot noir'"),
    country: Optional[str] = Query(None, description="Exact country filter, e.g. 'france'"),
    price_min: Optional[float] = Query(None, description="Minimum price filter"),
    price_max: Optional[float] = Query(None, description="Maximum price filter"),
    min_points: Optional[int] = Query(None, description="Minimum rating (points) filter"),
):
    # Build a dictionary of filters, but only keep the ones the user
    # actually provided (skip the ones that are still None).
    filters = {
        "variety": variety,
        "country": country,
        "price_min": price_min,
        "price_max": price_max,
        "min_points": min_points,
    }
    filters = {key: value for key, value in filters.items() if value is not None}

    try:
        results_df = model.recommend(query, top_k=top_k, filters=filters)
    except RuntimeError as error:
        # This happens if load_artifacts() was never called successfully.
        raise HTTPException(status_code=500, detail=str(error))

    # FastAPI can turn Python dicts/lists into JSON automatically, but
    # it does not know how to convert a pandas DataFrame. So we convert
    # it ourselves into a list of simple dictionaries first.
    return {
        "query": query,
        "count": len(results_df),
        "results": results_df.to_dict(orient="records"),
    }


# ---------------------------------------------------------------------
# 6. Look up a single wine by its id ("/wine/{wine_id}").
# ---------------------------------------------------------------------
@app.get("/wine/{wine_id}")
def get_wine(wine_id: int):
    wine = model.get_wine_by_id(wine_id)
    if wine is None:
        raise HTTPException(status_code=404, detail=f"Wine with id {wine_id} not found")
    return wine


# ---------------------------------------------------------------------
# 7. Show which model version is currently deployed ("/version").
# Handy to double check what is running in production.
# ---------------------------------------------------------------------
@app.get("/version")
def get_version():
    return model.get_version_info(ARTIFACTS_DIR)
