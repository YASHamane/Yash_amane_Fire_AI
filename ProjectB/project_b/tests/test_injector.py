"""Unit tests for controlled corruption injector across all 12 problem types."""

import pytest
import pandas as pd
import numpy as np

from project_b.src.injector import (
    inject_renamed_or_dropped_column,
    inject_column_type_change,
    inject_date_format_switch,
    inject_lat_long_swapped,
    inject_exact_duplicates,
    inject_near_duplicates,
    inject_null_spike,
    inject_closed_earlier_than_created,
    inject_zip_inconsistent_borough,
    inject_complaint_inconsistent_descriptor,
    inject_resolution_contradicting_status,
    inject_personal_data_in_text,
    inject_problem,
    INJECTOR_REGISTRY,
)


@pytest.fixture
def sample_clean_df():
    """Generates a synthetic clean sample batch for injector verification."""
    data = {
        "unique_key": [f"KEY_{i:04d}" for i in range(100)],
        "created_date": ["2023-05-15T12:00:00.000"] * 100,
        "closed_date": ["2023-05-16T12:00:00.000"] * 100,
        "agency": ["NYPD"] * 70 + ["DOT"] * 30,
        "complaint_type": ["Noise - Residential"] * 100,
        "descriptor": ["Loud Music/Party"] * 100,
        "status": ["Closed"] * 100,
        "resolution_description": ["The Police Department responded and resolved the condition."] * 100,
        "incident_zip": ["10001"] * 100,
        "borough": ["MANHATTAN"] * 100,
        "latitude": [40.7505] * 100,
        "longitude": [-73.9934] * 100,
    }
    return pd.DataFrame(data)


def test_registry_contains_12_types():
    assert len(INJECTOR_REGISTRY) == 12


def test_inject_renamed_or_dropped_column(sample_clean_df):
    corrupted, gt = inject_renamed_or_dropped_column(sample_clean_df, rate=0.05, seed=42)
    assert gt["is_corrupted"] is True
    assert gt["level"] == "batch"
    # Column should either be missing or renamed
    meta = gt["metadata"]
    if meta["action"] == "drop":
        assert meta["column"] not in corrupted.columns
    else:
        assert meta["new_column"] in corrupted.columns
        assert meta["original_column"] not in corrupted.columns


def test_inject_column_type_change(sample_clean_df):
    corrupted, gt = inject_column_type_change(sample_clean_df, rate=0.10, seed=42)
    assert gt["is_corrupted"] is True
    assert len(gt["corrupted_indices"]) == 10
    for idx in gt["corrupted_indices"]:
        val = str(corrupted.at[idx, "latitude"])
        assert not val.replace(".", "", 1).replace("-", "", 1).isdigit()


def test_inject_date_format_switch(sample_clean_df):
    corrupted, gt = inject_date_format_switch(sample_clean_df, rate=0.10, seed=42)
    assert len(gt["corrupted_indices"]) == 10
    for idx in gt["corrupted_indices"]:
        val = corrupted.at[idx, "created_date"]
        # Format switched away from standard ISO
        assert "T" not in val or "/" in val or "." in val


def test_inject_lat_long_swapped(sample_clean_df):
    corrupted, gt = inject_lat_long_swapped(sample_clean_df, rate=0.10, seed=42)
    assert len(gt["corrupted_indices"]) == 10
    for idx in gt["corrupted_indices"]:
        # Latitude in NYC is ~40.7; when swapped it receives Longitude (~ -73.9)
        assert corrupted.at[idx, "latitude"] < 0
        assert corrupted.at[idx, "longitude"] > 0


def test_inject_exact_duplicates(sample_clean_df):
    corrupted, gt = inject_exact_duplicates(sample_clean_df, rate=0.10, seed=42)
    assert len(corrupted) == len(sample_clean_df) + 10
    assert len(gt["corrupted_indices"]) == 10
    assert corrupted["unique_key"].duplicated().sum() == 10


def test_inject_near_duplicates(sample_clean_df):
    corrupted, gt = inject_near_duplicates(sample_clean_df, rate=0.10, seed=42)
    assert len(corrupted) == len(sample_clean_df) + 10
    # unique_key should not be exact duplicate, but descriptor/timestamp is altered
    assert corrupted["unique_key"].duplicated().sum() == 0
    for idx in gt["corrupted_indices"]:
        assert "_dup" in corrupted.at[idx, "unique_key"]


def test_inject_null_spike(sample_clean_df):
    corrupted, gt = inject_null_spike(sample_clean_df, rate=0.80, seed=42)
    assert gt["is_corrupted"] is True
    assert gt["metadata"]["target_agency"] == "NYPD"
    nypd_rows = corrupted[corrupted["agency"] == "NYPD"]
    null_ratio = nypd_rows["descriptor"].isna().mean()
    assert null_ratio >= 0.75


def test_inject_closed_earlier_than_created(sample_clean_df):
    corrupted, gt = inject_closed_earlier_than_created(sample_clean_df, rate=0.10, seed=42)
    assert len(gt["corrupted_indices"]) == 10
    for idx in gt["corrupted_indices"]:
        dt_c = pd.to_datetime(corrupted.at[idx, "created_date"])
        dt_cl = pd.to_datetime(corrupted.at[idx, "closed_date"])
        assert dt_cl < dt_c


def test_inject_zip_inconsistent_borough(sample_clean_df):
    corrupted, gt = inject_zip_inconsistent_borough(sample_clean_df, rate=0.10, seed=42)
    assert len(gt["corrupted_indices"]) == 10
    for idx in gt["corrupted_indices"]:
        # 10001 is Manhattan; corrupted borough must not be Manhattan
        assert corrupted.at[idx, "borough"] != "MANHATTAN"


def test_inject_complaint_inconsistent_descriptor(sample_clean_df):
    corrupted, gt = inject_complaint_inconsistent_descriptor(sample_clean_df, rate=0.10, seed=42)
    assert len(gt["corrupted_indices"]) == 10
    for idx in gt["corrupted_indices"]:
        # Check incompatible combination
        c = corrupted.at[idx, "complaint_type"]
        d = corrupted.at[idx, "descriptor"]
        assert (c, d) in [
            ("Street Light Condition", "Loud Music/Party inside Apartment"),
            ("Rodent", "Pothole in Right Lane"),
            ("Noise - Residential", "Dead Animal on Highway"),
            ("Sewer", "No Hot Water or Heat in Radiator"),
            ("Traffic Signal Condition", "Bed Bugs Infestation in Mattress"),
            ("Graffiti", "Missing Street Name Sign"),
        ]


def test_inject_resolution_contradicting_status(sample_clean_df):
    corrupted, gt = inject_resolution_contradicting_status(sample_clean_df, rate=0.10, seed=42)
    assert len(gt["corrupted_indices"]) == 10
    for idx in gt["corrupted_indices"]:
        st = corrupted.at[idx, "status"]
        res = corrupted.at[idx, "resolution_description"]
        if st == "Closed":
            assert any(word in res.lower() for word in ["active", "open", "progress", "scheduled"])
        else:
            assert any(word in res.lower() for word in ["resolved", "closed"])


def test_inject_personal_data_in_text(sample_clean_df):
    corrupted, gt = inject_personal_data_in_text(sample_clean_df, rate=0.10, seed=42)
    assert len(gt["corrupted_indices"]) == 10
    for idx in gt["corrupted_indices"]:
        res = corrupted.at[idx, "resolution_description"]
        assert any(pii_type in res for pii_type in ["@", "(", "-", "SSN:"])
