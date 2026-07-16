"""
Data engineering: cleaning, preprocessing, and feature engineering
for the wine reviews dataset (winemag-data-130k-v2.csv).

Expected raw columns:
country, description, designation, points, price, province,
region_1, region_2, taster_name, taster_twitter_handle, title, variety, winery
"""

import pandas as pd

DROP_COLUMNS = ["region_2", "taster_twitter_handle", "winery"]
TEXT_COLUMNS = ["country", "designation", "province", "variety", "region_1"]


def load_raw_data(path: str) -> pd.DataFrame:
    """Load the raw CSV into a DataFrame."""
    raise NotImplementedError


def report_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Return a summary table of NaN/empty counts per column (+ total row)."""
    raise NotImplementedError


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate rows based on description text (the main content signal)."""
    raise NotImplementedError


def drop_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop columns not used by the recommender: region_2, taster_twitter_handle, winery."""
    raise NotImplementedError


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop rows unusable for recommendation (no description/price),
    impute the rest with reasonable defaults (points -> median,
    text columns -> "Unknown").
    """
    raise NotImplementedError


def build_text_corpus(df: pd.DataFrame) -> pd.Series:
    """
    Combine description + variety + region_1 into one text field.
    This is what gets embedded by SBERT.
    """
    raise NotImplementedError


def build_feature_set(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assemble the final feature set: text corpus + filterable metadata.
    Adds a 'wine_id' column and renames region_1 -> region.
    """
    raise NotImplementedError


def run_pipeline(raw_csv_path: str, output_csv_path: str = None) -> pd.DataFrame:
    """Full data pipeline: load -> dedupe -> drop columns -> clean -> feature engineer."""
    raise NotImplementedError


if __name__ == "__main__":
    pass
