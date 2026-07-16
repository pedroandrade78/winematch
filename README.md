# WineMatch

Content-based wine recommender (SBERT embeddings + FAISS cosine similarity)
over the [Wine Reviews 130k](https://www.kaggle.com/datasets/zynicide/wine-reviews/data) dataset.

Requires **Python 3.10.6**.

## One search box

A single query combines a wine reference (name or id) with an optional
`+ property` modifier:

```
Ornellaia 2014 Le Volte Red + low price
109 + low price
Malbec + high rating
109 + under 30
```

The part before `+` can be a wine title (matched by substring) or a
`wine_id` (digits only). The part after `+` is handled two ways:

- **Price/rating direction** ("low price", "cheap", "budget-friendly",
  "high rating", "top rated"...) is classified via SBERT similarity
  against a couple of short anchor phrases in `model.STRUCTURED_ANCHORS`
  — synonyms and rephrasings work because the *embedding* is compared,
  not a literal keyword list.
- **Anything else** ("sweet", "fruity", "high alcohol", "oaky", "tannic",
  "crisp"...) is embedded and blended into the query vector itself
  (`model.MODIFIER_BLEND_WEIGHT` controls how strongly), so the search
  is naturally pulled toward wines whose descriptions match that style —
  no fixed vocabulary required.
- Explicit numeric constraints ("under 30", "over 90 points") are still
  extracted with simple regex, since these need to map to an exact
  filter on a real numeric column.

See `model.parse_query()` and `model.classify_structured_modifier()`.

## Files

- `data_engineering.py` — cleaning, column pruning, feature engineering (`run_pipeline`)
- `model.py` — embeddings, FAISS index, unified `recommend()` (handles both name- and id-based queries + modifiers)
- `api.py` — FastAPI app (`/recommend`, `/wines/{id}`, `/version`)
- `ui.py` — Streamlit front end ("WineMatch"), single search box
- `tests.py` — unit tests (data cleaning, query parsing, recommend logic, API), run offline with mocked model
- `Dockerfile`, `nginx.conf` — single image serving both FastAPI and Streamlit on port 80
- `requirements.txt`

## Setup

```bash
pip install -r requirements.txt
```

Download `winemag-data-130k-v2.csv` from Kaggle and place it in this folder.

## Build the model (run once)

```bash
python data_engineering.py   # -> wines_clean.csv
python model.py              # -> ./artifacts/ (index.faiss, metadata.parquet, version.json)
```

## Run locally

```bash
uvicorn api:app --reload             # API on http://localhost:8000
streamlit run ui.py                  # UI on http://localhost:8501 (separate terminal)
```

The UI calls the API at `API_URL` (defaults to `http://localhost:8000`).

## Run tests

```bash
pytest tests.py -v
```

Tests use small synthetic data and a monkeypatched SBERT model, so they run
without downloading any models or needing the real 130k-row dataset.

## Run in Docker (single image, one port)

```bash
docker build -t winematch .
docker run -p 80:80 -v $(pwd)/artifacts:/app/artifacts winematch
```

Then open `http://localhost` (UI) — API is reachable at `http://localhost/api/...`.

## API example

```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"query": "109 + low price", "top_k": 5}'
```
