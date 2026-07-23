import pandas as pd
import numpy as np
import pickle
import gzip
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors



CLEAN_DATA_PATH = "notebooks/wines_clean_test.csv"
MODEL_NAME = "all-MiniLM-L6-v2"  # small, fast, good default SBERT model

ENGINE_PKL_PATH = "wine_engine.pkl"

ESSENTIAL_COLUMNS = ["title", "winery", "variety", "country", "points", "price"]

# LOAD THE CLEANED DATASET

def load_clean_data(path=CLEAN_DATA_PATH):

    df = pd.read_csv(path)

    df["description"] = df["description"].fillna("")

    print(f"[load_clean_data] Loaded {len(df)} wines from '{path}'.")
    return df


# LOAD THE SBERT MODEL

def load_sbert_model(model_name=MODEL_NAME):

    print(f"[load_sbert_model] Loading model '{model_name}'...")

    model = SentenceTransformer(model_name)

    print("[load_sbert_model] Model loaded.")
    return model


# ENCODE DESCRIPTIONS INTO EMBEDDINGS


def build_embeddings(model, descriptions, batch_size=64):

    print(f"[build_embeddings] Encoding {len(descriptions)} descriptions "
          "(this can take a few minutes)...")

    embeddings = model.encode(
        descriptions,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,  # makes cosine similarity math simpler/faster
    )


    print(f"[build_embeddings] Done. Shape: {embeddings.shape}")

    return embeddings



# BUILD THE NEAREST NEIGHBORS

def build_neighbors_index(embeddings):


    print("[build_neighbors_index] Building the Nearest Neighbors index...")

    neighbors_model = NearestNeighbors(
                                    metric="cosine",
                                    algorithm="brute")


    neighbors_model.fit(embeddings)

    print("[build_neighbors_index] Index ready.")

    return neighbors_model


# SAVE INTO ONE SINGLE .pkl FILE

def save_engine(df, embeddings, neighbors_model=None, path=ENGINE_PKL_PATH,
                 columns=ESSENTIAL_COLUMNS):

    Path(path).parent.mkdir(parents=True, exist_ok=True)

    available_columns = [c for c in columns if c in df.columns]
    df_to_save = df[available_columns].copy()

    # float16 instead of float32 -> half the storage size
    embeddings_to_save = embeddings.astype(np.float16)

    engine_data = {
        "df": df_to_save,
        "embeddings": embeddings_to_save,
    }

    # gzip.open instead of open() compresses the file as it's written.

    with gzip.open(path, "wb", compresslevel=5) as f:
        pickle.dump(engine_data, f)

    size_mb = Path(path).stat().st_size / 1e6
    print(f"[save_engine] Saved engine (table + embeddings) to '{path}' "
          f"({size_mb:.1f} MB).")





# LOAD A PREVIOUSLY SAVED ENGINE

def load_engine(path=ENGINE_PKL_PATH):

    with gzip.open(path, "rb") as f:
        engine_data = pickle.load(f)

    df = engine_data["df"]

    # Convert back to float32 for the actual similarity calculations
    embeddings = engine_data["embeddings"].astype(np.float32)
    neighbors_model = build_neighbors_index(embeddings)

    print(f"[load_engine] Loaded engine with {len(df)} wines from '{path}'.")
    return df, embeddings, neighbors_model




# RECOMMEND WINES

def recommend_wine(wine_title, df, embeddings, neighbors_model, top_n=5):


    matches = df.index[df["title"] == wine_title]
    if len(matches) == 0:
        print(f"[recommend_wine] Wine not found: '{wine_title}'")
        return None

    wine_index = matches[0]

    # kneighbors() returns two lists:
    #   distances -> how "far" (dissimilar) each neighbor is (0 = identical)
    #   indices   -> the position (row) of each neighbor in the table
    distances, indices = neighbors_model.kneighbors(
        embeddings[wine_index].reshape(1, -1), n_neighbors=top_n + 1
    )


    # We skip the first result [0], since it's always the wine itself
    distances = distances[0][1:]
    indices = indices[0][1:]
    similarities = 1 - distances

    result = df.iloc[indices][["title", "variety", "country", "points", "price"]].copy()
    result["similarity"] = similarities.round(3)
    return result


# BUILD THE FULL ENGINE FROM SCRATCH (convenience wrapper)

def build_engine_from_scratch(clean_data_path=CLEAN_DATA_PATH, model_name=MODEL_NAME):
    df = load_clean_data(clean_data_path)
    model = load_sbert_model(model_name)
    embeddings = build_embeddings(model, df["description"].tolist())
    neighbors_model = build_neighbors_index(embeddings)
    save_engine(df, embeddings, neighbors_model)

    return df, embeddings, neighbors_model






if __name__ == "__main__":
    # Build (or rebuild) the engine from scratch, since this is the
    # standalone entry point of the script.
    df, embeddings, neighbors_model = build_engine_from_scratch()
