"""
build_artifacts.py

Run this script ONE TIME, locally, BEFORE building the Docker image or
starting the API. It does the heavy, slow work up front so the API
itself only has to *load* the results (fast) instead of *computing*
them (slow) every time it starts.

What it does:
  1. Cleans the raw CSV file (package_folder/data_engineering.py)
  2. Computes SBERT embeddings for every wine and builds a FAISS
     similarity index (package_folder/model.py)
  3. Saves everything into the ./artifacts folder:
       - index.faiss       (the similarity search index)
       - metadata.parquet  (the cleaned wine data table)
       - version.json      (info about the model used)

How to run it:
    python build_artifacts.py

Before running, make sure the raw dataset is at:
    raw_data/winemag-data-130k-v2.csv
"""

from package_folder.data_engineering import run_pipeline
from package_folder.model import build_model

RAW_CSV_PATH = "raw_data/winemag-data-130k-v2.csv"
ARTIFACTS_DIR = "artifacts"


if __name__ == "__main__":
    print("Step 1/2: cleaning and preparing the data...")
    clean_df = run_pipeline(RAW_CSV_PATH)

    print("Step 2/2: computing embeddings and building the FAISS index...")
    build_model(clean_df, artifacts_dir=ARTIFACTS_DIR)

    print(f"✅ Done! Artifacts saved to ./{ARTIFACTS_DIR}")
    print("You can now run the API locally, or build the Docker image.")
