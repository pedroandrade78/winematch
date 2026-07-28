# ---------------------------------------------------------------------
# 1. Base image: Python 3.10, "slim" version to keep the image small.
# ---------------------------------------------------------------------
FROM python:3.10.6-slim

# Set the working directory inside the container. Every command below
# runs from this folder.
WORKDIR /app

# ---------------------------------------------------------------------
# 2. Copy and install dependencies FIRST.
# Docker caches each step: if requirements.txt doesn't change, Docker
# will reuse this step next time instead of re-installing everything,
# which makes rebuilding the image much faster.
# ---------------------------------------------------------------------
COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------
# 3. Copy the application code and install it as a package.
# ---------------------------------------------------------------------
COPY package_folder package_folder
COPY setup.py setup.py

RUN pip install --no-cache-dir -e .

# ---------------------------------------------------------------------
# 4. Copy the pre-built model artifacts.
# IMPORTANT: run "python build_artifacts.py" locally BEFORE building
# this image, so the ./artifacts folder exists and contains
# index.faiss, metadata.parquet and version.json.
# ---------------------------------------------------------------------
COPY artifacts artifacts

# ---------------------------------------------------------------------
# 5. Start the API.
# Cloud Run injects the PORT environment variable at runtime, so we
# bind Uvicorn to it. Locally it defaults to 8000.
# ---------------------------------------------------------------------

# This CMD starts the FastAPI app differently depending on whether the container is running locally or on Google Cloud Run.
# If no PORT variable exists, it uses local development settings with port 8000 and --reload;
# if PORT exists, it uses the port provided by Cloud Run.

CMD ["sh", "-c", "if [ -z \"$PORT\" ]; then uvicorn package_folder.api_file:app  --host 0.0.0.0 --port 8000; else uvicorn package_folder.api_file:app --host 0.0.0.0 --port \"$PORT\"; fi"]


#If the above does not work use the following commands:

#local
# CMD uvicorn mush_package.api_file:app --reload --host 0.0.0.0

#gcp (cloud run) deployment
# CMD uvicorn mush_package.api_file:app --reload --host 0.0.0.0 --port $PORT
