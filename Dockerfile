FROM python:3.10.6-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the SBERT model so it's cached in the image
# (load_sbert_model uses local_files_only=True, so it must already be cached)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY . .

CMD uvicorn api:app --host 0.0.0.0 --port $PORT
