"""
Data engineering: cleaning, preprocessing, and feature engineering
for the wine reviews dataset (winemag-data-130k-v2.csv).

Expected raw columns:
country, description, designation, points, price, province,
region_1, region_2, taster_name, taster_twitter_handle, title, variety, winery
"""

import pandas as pd
import numpy as np
import os
import re

# Import for special characters (Mojibake)
import ftfy


TEXT_COLUMNS = ["country", "description", "designation", "province",
                "region_1", "region_2", "taster_name", "taster_twitter_handle",
                 "title", "variety", "winery"]

DROP_COLUMNS = ["Unnamed: 0","designation", "region_2","taster_twitter_handle"]



def load_raw_data(path: str) -> pd.DataFrame:
    """Load the raw CSV into a DataFrame."""
    df = pd.read_csv(path)
    print(f"✅ Loaded {len(df)} rows and {len(df.columns)} columns from {path}")
    return df


def report_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Return a summary table of NaN/empty counts per column (+ total row)."""

    # Check number of missing values in each column
    missing_values = df.isna().sum()

    # Check the % of missing values in each column, rounded by 2 decimal places.
    missing_percentages = (df.isna().mean() * 100).round(2)

    # Create a summary DataFrame
    summary = pd.DataFrame({
        "Missing Values": missing_values,
        "Missing %": missing_percentages
    })
    print("✅ Missing values summary:")
    print(summary)
    return summary


def clean_text(text):
    """Clean text: remove line breaks, tabs, extra spaces, and normalize accents."""
    if pd.isna(text):
        return np.nan

    # correction encoding Mojibake (ftfy)
    text = ftfy.fix_text(text)

    # Remove break lines and tabs
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")

    # Remove multiple spaces
    text = re.sub(r"\s+", " ", text)

    # Remove spaces at the beginning and end
    text = text.strip()

    # Normalize accents
    text = text.encode("utf-8", "ignore").decode("utf-8")

    return text

def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Clean text columns: remove line breaks, tabs, extra spaces, and normalize accents."""

    for col in TEXT_COLUMNS:
         df[col] = df[col].astype(str).apply(clean_text)

    # Convert 'nan' strings back to NaN
    df = df.replace('nan', np.nan)

    print(f"✅ Cleaned text columns: {', '.join(TEXT_COLUMNS)}")
    return df


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate rows based on Title column."""

    # Drop duplicates based on title.
    before = len(df)
    df = df.drop_duplicates(subset=["title"])
    after = len(df)
    print(f"✅ Duplicate titles removed: {before - after}")
    return df


def drop_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop columns not used by the recommender: region_2, taster_twitter_handle, winery."""

    df =df.drop(columns=DROP_COLUMNS, errors="ignore")
    print(f"✅ Dropped columns: {', '.join(DROP_COLUMNS)}")
    return df


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop rows unusable for recommendation (no description/price),
    impute the rest with reasonable defaults (points -> median,
    text columns -> "Unknown").
    """
    # For Price the null values will be dropped, as the price is a key feature for the recommender system. For the other columns, the null values will be filled with 'Unknown' for categorical columns and 0 for numerical columns.
    df = df.dropna(subset=["price"]).copy()

    # For the country the null values will be replace according with the winery Location.
    df.loc[df["winery"] == "Gotsa Family Wines", "country"] = "Georgia"
    df.loc[df["winery"] == "Barton & Guestier", "country"] = "France"
    df.loc[df["winery"] == "Kakhetia Traditional Winemaking", "country"] = "Georgia"
    df.loc[df["winery"] == "Tsililis", "country"] = "Greece"
    df.loc[df["winery"] == "Ross-idi", "country"] = "Bulgaria"
    df.loc[df["winery"] == "Les Frères Dutruy", "country"] = "Switzerland"
    df.loc[df["winery"] == "El Capricho", "country"] = "Spain"
    df.loc[df["winery"] == "Büyülübağ", "country"] = "Turkey"
    df.loc[df["winery"] == "Psagot", "country"] = "Israel"
    df.loc[df["winery"] == "Orbelus", "country"] = "Bulgaria"
    df.loc[df["winery"] == "St. Donat", "country"] = "Hungary"
    df.loc[df["winery"] == "Familia Deicas", "country"] = "Uruguay"
    df.loc[df["winery"] == "Bartho Eksteen", "country"] = "South Africa"
    df.loc[df["winery"] == "Stone Castle", "country"] = "Kosovo"
    df.loc[df["winery"] == "Teliani Valley", "country"] = "Georgia"
    df.loc[df["winery"] == "Undurraga", "country"] = "Chile"
    df.loc[df["winery"] == "Mt. Beautiful", "country"] = "New Zealand"
    df.loc[df["winery"] == "Neumeister", "country"] = "Austria"
    df.loc[df["winery"] == "Bachelder", "country"] = "Canada"
    df.loc[df["winery"] == "Chilcas", "country"] = "Chile"
    df.loc[df["winery"] == "Santa Ema", "country"] = "Chile"
    df.loc[df["winery"] == "Newton Johnson", "country"] = "South Africa"
    df.loc[df["winery"] == "Ktima Voyatzi", "country"] = "Greece"
    df.loc[df["winery"] == "Lismore", "country"] = "South Africa"
    df.loc[df["winery"] == "Logodaj", "country"] = "Bulgaria"
    df.loc[df["winery"] == "Somlói Vándor", "country"] = "Hungary"
    df.loc[df["winery"] == "Amiran Vepkhvadze", "country"] = "Georgia"

    #The only missing variety is for Carmen 1999 (Maipo Valley) from chile which variety is Cabernet Sauvignon, so we will fill the missing value with this variety.
    df["variety"] = df["variety"].fillna("Cabernet Sauvignon")

    # If region is missing it should be fill with the Title inside parenthesis if exists, otherwise it should be filled with 'unknown'.
    df["region_1"] = (df["region_1"].fillna(df["title"].str.extract(r'\((.*?)\)')[0]   # select the extracted Series
        .fillna('unknown')
        )
    )

    # If province is missing it should be fill with the region if exists, otherwise it should be filled with 'unknown'.
    df["province"] = (df["province"].fillna(df["region_1"])
        .fillna('unknown')
    )

    # Replace the empty value with the word "unknown" on the column "taster_name".
    df["taster_name"] = df["taster_name"].fillna("unknown")



    # Check number of missing values in each column
    missing_values = df.isna().sum()

    # Check the % of missing values in each column, rounded by 2 decimal places.
    missing_percentages = (df.isna().mean() * 100).round(2)

    # Create a summary DataFrame
    summary = pd.DataFrame({
        "Missing Values": missing_values,
        "Missing %": missing_percentages
    })
    print(f"✅ Handled missing values: {df.isna().sum().sum()} remaining")
    print(summary)

    return df


def build_text_corpus(df: pd.DataFrame) -> pd.Series:
    """
    Combine description + variety + region_1 into one text field.
    This is what gets embedded by SBERT.
    """
    return (
        df["description"].astype(str)
        + ". Variety: " + df["variety"].astype(str)
        + ". Region: " + df["region_1"].astype(str)
    )



def build_feature_set(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assemble the final feature set: text corpus + filterable metadata.
    Adds a 'wine_id' column and renames region_1 -> region.
    """
    df = df.copy()
    df["text_corpus"] = build_text_corpus(df)
    df = df.reset_index(drop=True)
    df.insert(0, "wine_id", df.index)

    # Rename region_1 as region
    df = df.rename(columns={"region_1": "region"})

    keep_cols = [
        "wine_id", "country",
        "title", "description",
        "variety","province","region","winery",
        "price", "points", "taster_name","text_corpus"
    ]

    keep_cols = [c for c in keep_cols if c in df.columns]

    # Lowercase only text columns
    for c in keep_cols:
        if df[c].dtype == "object":
            df[c] = df[c].str.lower()
    print(f"✅ Final Dataset with follow columns: {', '.join(keep_cols)}")

    return df



def run_pipeline(raw_csv_path: str, output_csv_path: str = None) -> pd.DataFrame:
    """Full data pipeline: load -> dedupe -> drop columns -> clean -> feature engineer."""
    df = load_raw_data(raw_csv_path)
    report_missing_values(df)      # Only prints
    df = clean_text_columns(df)
    df = drop_duplicates(df)
    df = drop_columns(df)
    df = handle_missing_values(df)
    df = build_feature_set(df)

    if output_csv_path:
        df.to_csv(output_csv_path, index=False)

    return df


if __name__ == "__main__":
    result = run_pipeline("raw_data/winemag-data-130k-v2.csv",
                          "raw_data/wines_clean.csv")
    print(f"✅ Cleaned dataset: {result.shape[0]} rows, {result.shape[1]} columns")
