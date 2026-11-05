"""Data Profiler for NYC 311 Service Requests (2023).

Task 1: Profiles raw 2023 data, finding real data quality defects that naturally
exist in production data (with concrete counts, rates, and example unique_keys).
Derives a clean reference dataset (100% verified anomaly-free) used as the
baseline source for controlled corruption injection.
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np

# Add project_b to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from project_b.src.config import (
    RAW_DATA_DIR,
    CLEAN_DATA_DIR,
    RESULTS_DIR,
    NYC_LAT_MIN,
    NYC_LAT_MAX,
    NYC_LON_MIN,
    NYC_LON_MAX,
    CANONICAL_COLUMNS,
)

# Compiled regex patterns for PII detection in free-text fields
PHONE_REGEX = re.compile(r"(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?[2-9]\d{2}[-.\s]?\d{4}")
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def load_raw_dataset(limit: int = None) -> pd.DataFrame:
    """Loads raw consolidated or monthly parquet file."""
    master_path = RAW_DATA_DIR / "nyc_311_2023_full.parquet"
    if master_path.exists():
        df = pd.read_parquet(master_path)
    else:
        # Fall back to any available monthly files
        files = list(RAW_DATA_DIR.glob("nyc_311_2023_*.parquet"))
        if not files:
            raise FileNotFoundError("No raw 311 parquet files found in data/raw/")
        df = pd.read_parquet(files[0])
    
    if limit and len(df) > limit:
        df = df.iloc[:limit].copy()
    return df


def load_zip_borough_ref() -> Dict[str, str]:
    """Loads official NYC ZIP code to Borough reference map."""
    ref_path = RAW_DATA_DIR / "nyc_zip_borough_reference.csv"
    if not ref_path.exists():
        return {}
    ref_df = pd.read_csv(ref_path)
    # normalize keys and values to uppercase strings
    return dict(zip(ref_df["incident_zip"].astype(str).str.zfill(5), ref_df["borough"].str.upper()))


def profile_raw_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Analyzes raw dataset across all data quality dimensions.
    
    Returns:
        summary_df: DataFrame with counts, percentages, and description of defects.
        examples_dict: Concrete example records (unique_keys and row snippets).
    """
    total_rows = len(df)
    results = []
    examples = {}

    zip_ref = load_zip_borough_ref()

    # 1. Null Counts per Column
    for col in CANONICAL_COLUMNS:
        if col in df.columns:
            null_count = int(df[col].isna().sum())
            null_pct = (null_count / total_rows) * 100
            results.append({
                "issue_type": "null_values",
                "column": col,
                "count": null_count,
                "percentage": round(null_pct, 4),
                "description": f"Null/missing values in column '{col}'"
            })
            if null_count > 0:
                sample_keys = df[df[col].isna()]["unique_key"].dropna().astype(str).head(3).tolist()
                examples[f"null_{col}"] = sample_keys

    # 2. Closed Date Earlier Than Created Date
    dt_created = pd.to_datetime(df["created_date"], errors="coerce")
    dt_closed = pd.to_datetime(df["closed_date"], errors="coerce")
    
    both_present = dt_created.notna() & dt_closed.notna()
    closed_before_created = both_present & (dt_closed < dt_created)
    cbc_count = int(closed_before_created.sum())
    results.append({
        "issue_type": "closed_before_created",
        "column": "closed_date",
        "count": cbc_count,
        "percentage": round((cbc_count / total_rows) * 100, 4),
        "description": "Closed timestamp is chronologically earlier than Created timestamp"
    })
    if cbc_count > 0:
        examples["closed_before_created"] = df[closed_before_created][["unique_key", "created_date", "closed_date"]].head(3).to_dict(orient="records")

    # 3. Future Dates (Created Date > current reference or year boundary)
    future_dates = dt_created > pd.Timestamp("2023-12-31 23:59:59")
    fd_count = int(future_dates.sum())
    results.append({
        "issue_type": "future_created_date",
        "column": "created_date",
        "count": fd_count,
        "percentage": round((fd_count / total_rows) * 100, 4),
        "description": "Created date falls in the future beyond 2023 calendar year"
    })
    if fd_count > 0:
        examples["future_created_date"] = df[future_dates]["unique_key"].head(3).tolist()

    # 4. Impossible or Zero Lat/Long / Out of NYC Bounding Box
    lat = pd.to_numeric(df["latitude"], errors="coerce")
    lon = pd.to_numeric(df["longitude"], errors="coerce")
    
    has_coords = lat.notna() & lon.notna()
    zero_coords = (lat == 0.0) | (lon == 0.0)
    out_of_bounds = has_coords & (
        (lat < NYC_LAT_MIN) | (lat > NYC_LAT_MAX) |
        (lon < NYC_LON_MIN) | (lon > NYC_LON_MAX)
    )
    bad_coords = zero_coords | out_of_bounds
    bad_coord_count = int(bad_coords.sum())
    results.append({
        "issue_type": "invalid_or_out_of_bounds_coordinates",
        "column": "latitude,longitude",
        "count": bad_coord_count,
        "percentage": round((bad_coord_count / total_rows) * 100, 4),
        "description": f"Coordinates equal to (0,0) or outside NYC bounding box [{NYC_LAT_MIN}-{NYC_LAT_MAX}, {NYC_LON_MIN}-{NYC_LON_MAX}]"
    })
    if bad_coord_count > 0:
        examples["invalid_coordinates"] = df[bad_coords][["unique_key", "latitude", "longitude"]].head(3).to_dict(orient="records")

    # 5. ZIP Code Inconsistent with Borough (vectorized lookup)
    zip_mismatch_mask = pd.Series(False, index=df.index)
    if zip_ref:
        clean_zips = df["incident_zip"].astype(str).str.strip().str[:5].str.zfill(5)
        clean_borough = df["borough"].astype(str).str.strip().str.upper()
        expected_borough = clean_zips.map(zip_ref)
        
        valid_comp = expected_borough.notna() & (~clean_borough.isin(["UNSPECIFIED", "", "NONE", "NAN"]))
        zip_mismatch_mask = valid_comp & (clean_borough != expected_borough)

    zip_mismatch_count = int(zip_mismatch_mask.sum())
    results.append({
        "issue_type": "zip_borough_mismatch",
        "column": "incident_zip,borough",
        "count": zip_mismatch_count,
        "percentage": round((zip_mismatch_count / total_rows) * 100, 4),
        "description": "Incident ZIP code does not match official USPS NYC Borough mapping"
    })
    if zip_mismatch_count > 0:
        examples["zip_borough_mismatch"] = df[zip_mismatch_mask][["unique_key", "incident_zip", "borough"]].head(3).to_dict(orient="records")

    # 6. Unspecified Categories
    unspec_borough = df["borough"].astype(str).str.upper().isin(["UNSPECIFIED", "UNKNOWN", ""])
    unspec_count = int(unspec_borough.sum())
    results.append({
        "issue_type": "unspecified_borough",
        "column": "borough",
        "count": unspec_count,
        "percentage": round((unspec_count / total_rows) * 100, 4),
        "description": "Borough explicitly recorded as 'Unspecified' or empty"
    })
    if unspec_count > 0:
        examples["unspecified_borough"] = df[unspec_borough]["unique_key"].head(3).tolist()

    # 7. Duplicate Unique Keys
    dup_keys_count = int(df["unique_key"].duplicated().sum())
    results.append({
        "issue_type": "duplicate_unique_keys",
        "column": "unique_key",
        "count": dup_keys_count,
        "percentage": round((dup_keys_count / total_rows) * 100, 4),
        "description": "Primary key 'unique_key' collisions / exact duplicates"
    })
    if dup_keys_count > 0:
        dup_keys = df[df["unique_key"].duplicated()]["unique_key"].head(3).tolist()
        examples["duplicate_unique_keys"] = dup_keys

    # 8. Inconsistent Casing and Whitespace
    raw_desc = df["descriptor"].astype(str)
    whitespace_flaws = raw_desc.str.startswith(" ") | raw_desc.str.endswith(" ") | raw_desc.str.contains(r"\s{2,}")
    ws_count = int(whitespace_flaws.sum())
    results.append({
        "issue_type": "whitespace_formatting_inconsistencies",
        "column": "descriptor",
        "count": ws_count,
        "percentage": round((ws_count / total_rows) * 100, 4),
        "description": "Leading, trailing, or double whitespace in descriptor field"
    })

    # 9. PII (Personal Identifiable Information) in Free Text
    # Check descriptor and resolution_description for phone numbers and email addresses
    combined_text = df["descriptor"].fillna("").astype(str) + " " + df["resolution_description"].fillna("").astype(str)
    has_phone = combined_text.str.contains(PHONE_REGEX, regex=True)
    has_email = combined_text.str.contains(EMAIL_REGEX, regex=True)
    pii_mask = has_phone | has_email
    pii_count = int(pii_mask.sum())
    results.append({
        "issue_type": "pii_in_free_text",
        "column": "descriptor,resolution_description",
        "count": pii_count,
        "percentage": round((pii_count / total_rows) * 100, 4),
        "description": "Telephone numbers or email addresses detected in free-text fields"
    })
    if pii_count > 0:
        examples["pii_in_free_text"] = df[pii_mask][["unique_key", "descriptor", "resolution_description"]].head(3).to_dict(orient="records")

    # 10. Status vs Resolution Contradiction (e.g. Closed status with pending/in-progress resolution)
    status_upper = df["status"].fillna("").astype(str).str.upper()
    res_lower = df["resolution_description"].fillna("").astype(str).str.lower()
    
    closed_with_pending = (status_upper == "CLOSED") & (
        res_lower.str.contains(r"\b(?:in progress|still open|pending inspection|unable to investigate|scheduled for follow up)\b", regex=True)
    )
    open_with_closed = (status_upper.isin(["OPEN", "PENDING", "IN PROGRESS"])) & (
        res_lower.str.contains(r"\b(?:condition was resolved|service request was closed|inspected and no violation found)\b", regex=True)
    )
    contradiction_mask = closed_with_pending | open_with_closed
    contradiction_count = int(contradiction_mask.sum())
    results.append({
        "issue_type": "status_resolution_contradiction",
        "column": "status,resolution_description",
        "count": contradiction_count,
        "percentage": round((contradiction_count / total_rows) * 100, 4),
        "description": "Semantic mismatch between status and resolution description"
    })
    if contradiction_count > 0:
        examples["status_resolution_contradiction"] = df[contradiction_mask][["unique_key", "status", "resolution_description"]].head(3).to_dict(orient="records")

    summary_df = pd.DataFrame(results)
    return summary_df, examples


def build_clean_dataset(df: pd.DataFrame, target_size: int = 10000, overwrite: bool = True) -> pd.DataFrame:
    """Builds a verified clean reference dataset passing all quality filters.
    
    Why: To rigorously measure false alarms and inject controlled corruption,
    we must start with a clean baseline that is known to contain 0 defects.
    """
    clean_path = CLEAN_DATA_DIR / "clean_reference.parquet"
    if clean_path.exists() and not overwrite:
        return pd.read_parquet(clean_path)

    zip_ref = load_zip_borough_ref()
    
    # Required non-null columns
    valid_mask = (
        df["unique_key"].notna() &
        df["created_date"].notna() &
        df["closed_date"].notna() &
        df["agency"].notna() &
        df["complaint_type"].notna() &
        df["descriptor"].notna() &
        df["status"].notna() &
        df["resolution_description"].notna() &
        df["incident_zip"].notna() &
        df["borough"].notna() &
        df["latitude"].notna() &
        df["longitude"].notna()
    )

    # Valid temporal ordering
    dt_created = pd.to_datetime(df["created_date"], errors="coerce")
    dt_closed = pd.to_datetime(df["closed_date"], errors="coerce")
    temporal_valid = (dt_closed >= dt_created) & (dt_created <= pd.Timestamp("2023-12-31 23:59:59"))

    # Valid coordinates
    lat = pd.to_numeric(df["latitude"], errors="coerce")
    lon = pd.to_numeric(df["longitude"], errors="coerce")
    coord_valid = (lat >= NYC_LAT_MIN) & (lat <= NYC_LAT_MAX) & (lon >= NYC_LON_MIN) & (lon <= NYC_LON_MAX)

    # Valid borough and ZIP (vectorized lookup)
    clean_zips = df["incident_zip"].astype(str).str.strip().str[:5].str.zfill(5)
    clean_borough = df["borough"].astype(str).str.strip().str.upper()
    expected_borough = clean_zips.map(zip_ref)
    zip_valid = expected_borough.notna() & (clean_borough == expected_borough)

    # No PII in text
    combined_text = df["descriptor"].fillna("").astype(str) + " " + df["resolution_description"].fillna("").astype(str)
    no_phone = ~combined_text.str.contains(PHONE_REGEX, regex=True)
    no_email = ~combined_text.str.contains(EMAIL_REGEX, regex=True)
    no_pii = no_phone & no_email

    # Combine all clean masks
    all_clean_mask = valid_mask & temporal_valid & coord_valid & zip_valid & no_pii
    clean_df = df[all_clean_mask].copy()

    # Drop any duplicates
    clean_df = clean_df.drop_duplicates(subset=["unique_key"])

    if len(clean_df) > target_size:
        clean_df = clean_df.sample(n=target_size, random_state=42).reset_index(drop=True)

    clean_df.to_parquet(clean_path, index=False)
    print(f"Constructed verified clean reference dataset of {len(clean_df)} rows at {clean_path}")
    return clean_df


if __name__ == "__main__":
    raw_df = load_raw_dataset()
    summary, examples = profile_raw_data(raw_df)
    
    summary_path = RESULTS_DIR / "profile_summary.csv"
    examples_path = RESULTS_DIR / "profile_examples.json"
    
    summary.to_csv(summary_path, index=False)
    with open(examples_path, "w", encoding="utf-8") as f:
        json.dump(examples, f, indent=2, default=str)
        
    print(f"Saved profiling summary to {summary_path}")
    print(f"Saved example issues to {examples_path}")
    
    clean_df = build_clean_dataset(raw_df)
