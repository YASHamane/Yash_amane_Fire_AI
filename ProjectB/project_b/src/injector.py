"""Controlled Data Corruption Injector for Project B.

Task 2: Injects 12 distinct data quality problem types into clean batches
at controlled rates (e.g. 1%, 5%, 20%) with exact ground-truth labels.

Problem Types:
  a. renamed_or_dropped_column (batch-level)
  b. column_type_change (batch-level / row-level)
  c. date_format_switch (batch-level / row-level)
  d. lat_long_swapped (row-level)
  e. exact_duplicates (row-level)
  f. near_duplicates (row-level)
  g. null_spike (batch-level in one agency's records)
  h. closed_earlier_than_created (row-level)
  i. zip_inconsistent_borough (row-level)
  j. complaint_inconsistent_descriptor (row-level)
  k. resolution_contradicting_status (row-level)
  l. personal_data_in_text (row-level)
"""

import sys
import random
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
import numpy as np
import pandas as pd

# Add project_b to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from project_b.src.config import (
    CLEAN_DATA_DIR,
    INJECTED_DATA_DIR,
    RANDOM_SEED,
    EVAL_INJECTION_RATES,
    EVAL_BATCH_SIZE,
    NUM_CLEAN_BATCHES,
    PROBLEM_TYPES,
)


def _get_sample_indices(df: pd.DataFrame, rate: float, seed: int) -> List[int]:
    """Helper to select deterministic random row indices based on corruption rate."""
    n_rows = len(df)
    n_sample = max(1, int(round(n_rows * rate)))
    rng = np.random.default_rng(seed)
    sampled = rng.choice(df.index.values, size=min(n_sample, n_rows), replace=False)
    return sorted(sampled.tolist())


# ---------------------------------------------------------------------------
# Problem a: Renamed or Dropped Column (Batch-Level)
# ---------------------------------------------------------------------------
def inject_renamed_or_dropped_column(
    df: pd.DataFrame, rate: float = 0.05, seed: int = RANDOM_SEED
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Drops or renames a key canonical column at the batch level.
    
    Why: Upstream schema changes or ingestion configuration errors often
    cause missing or misspelled columns for an entire batch.
    """
    df_corrupt = df.copy()
    rng = random.Random(seed)
    target_col = rng.choice(["descriptor", "incident_zip", "resolution_description", "closed_date"])
    action = rng.choice(["drop", "rename"])
    
    if action == "drop":
        df_corrupt = df_corrupt.drop(columns=[target_col])
        meta = {"action": "drop", "column": target_col}
    else:
        new_col = f"{target_col}_legacy_v1"
        df_corrupt = df_corrupt.rename(columns={target_col: new_col})
        meta = {"action": "rename", "original_column": target_col, "new_column": new_col}

    ground_truth = {
        "problem_type": "renamed_or_dropped_column",
        "level": "batch",
        "rate": 1.0,  # Batch-level defect
        "is_corrupted": True,
        "corrupted_indices": list(df.index),
        "metadata": meta,
    }
    return df_corrupt, ground_truth


# ---------------------------------------------------------------------------
# Problem b: Column Type Change (Numbers arriving as strings / garbage)
# ---------------------------------------------------------------------------
def inject_column_type_change(
    df: pd.DataFrame, rate: float = 0.05, seed: int = RANDOM_SEED
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Corrupts numeric coordinate fields with string representations or invalid text.
    
    Why: Upstream schema drift can cause numeric columns (latitude/longitude)
    to arrive as unparseable strings (e.g. 'NaN', 'missing', '40.7128N', or symbol prefixes).
    """
    df_corrupt = df.copy()
    # Ensure column can accept string values (Pandas 3+ strict typing)
    df_corrupt["latitude"] = df_corrupt["latitude"].astype(object)
    target_idx = _get_sample_indices(df_corrupt, rate, seed)
    
    rng = random.Random(seed)
    for idx in target_idx:
        orig_val = df_corrupt.at[idx, "latitude"]
        # Invert type to string with non-numeric suffixes or textual sentinel
        mutations = [
            f"{orig_val}_deg_N",
            "UNAVAILABLE_LAT",
            f"STR_{orig_val}",
            "N/A",
            "ERR_COORD",
        ]
        df_corrupt.at[idx, "latitude"] = rng.choice(mutations)

    ground_truth = {
        "problem_type": "column_type_change",
        "level": "row",
        "rate": rate,
        "is_corrupted": True,
        "corrupted_indices": target_idx,
        "metadata": {"target_column": "latitude", "num_rows": len(target_idx)},
    }
    return df_corrupt, ground_truth


# ---------------------------------------------------------------------------
# Problem c: Date Format Switch Partway Through Batch
# ---------------------------------------------------------------------------
def inject_date_format_switch(
    df: pd.DataFrame, rate: float = 0.05, seed: int = RANDOM_SEED
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Changes timestamp formatting from ISO standard to non-standard format partway through batch.
    
    Why: Service upgrades mid-day or multi-region routing often causes timestamp
    formats to flip (e.g. from YYYY-MM-DDTHH:MM:SS to DD/MM/YYYY or Epoch millisecond).
    """
    df_corrupt = df.copy()
    target_idx = _get_sample_indices(df_corrupt, rate, seed)
    
    rng = random.Random(seed)
    for idx in target_idx:
        orig_date_str = str(df_corrupt.at[idx, "created_date"])
        try:
            ts = pd.to_datetime(orig_date_str)
            # Switch to non-standard alternative formats
            format_choices = [
                ts.strftime("%d/%m/%Y %H:%M:%S"),      # European DD/MM/YYYY
                ts.strftime("%Y.%m.%d-%H.%M"),         # Dot notation
                str(int(ts.timestamp())),              # Unix epoch seconds
                ts.strftime("%B %d, %Y at %I:%M %p"),  # Long written English
            ]
            df_corrupt.at[idx, "created_date"] = rng.choice(format_choices)
        except Exception:
            df_corrupt.at[idx, "created_date"] = "01-01-2023 00:00:00"

    ground_truth = {
        "problem_type": "date_format_switch",
        "level": "row",
        "rate": rate,
        "is_corrupted": True,
        "corrupted_indices": target_idx,
        "metadata": {"target_column": "created_date", "num_rows": len(target_idx)},
    }
    return df_corrupt, ground_truth


# ---------------------------------------------------------------------------
# Problem d: Latitude and Longitude Swapped
# ---------------------------------------------------------------------------
def inject_lat_long_swapped(
    df: pd.DataFrame, rate: float = 0.05, seed: int = RANDOM_SEED
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Swaps Latitude and Longitude values for selected rows.
    
    Why: GIS ETL pipelines often invert X and Y coordinates (Lon is negative ~-73,
    Lat is positive ~+40). When swapped, points end up in Antarctica or oceans.
    """
    df_corrupt = df.copy()
    target_idx = _get_sample_indices(df_corrupt, rate, seed)
    
    for idx in target_idx:
        lat = df_corrupt.at[idx, "latitude"]
        lon = df_corrupt.at[idx, "longitude"]
        # Swap values
        df_corrupt.at[idx, "latitude"] = lon
        df_corrupt.at[idx, "longitude"] = lat

    ground_truth = {
        "problem_type": "lat_long_swapped",
        "level": "row",
        "rate": rate,
        "is_corrupted": True,
        "corrupted_indices": target_idx,
        "metadata": {"num_rows": len(target_idx)},
    }
    return df_corrupt, ground_truth


# ---------------------------------------------------------------------------
# Problem e: Exact Duplicates
# ---------------------------------------------------------------------------
def inject_exact_duplicates(
    df: pd.DataFrame, rate: float = 0.05, seed: int = RANDOM_SEED
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Injects exact duplicates of existing rows into the batch.
    
    Why: Message queue re-deliveries (at-least-once semantics) or failed ETL
    retries duplicate records identically.
    """
    df_corrupt = df.copy()
    target_idx = _get_sample_indices(df_corrupt, rate, seed)
    dup_rows = df_corrupt.loc[target_idx].copy()
    
    # Concatenate duplicate rows
    corrupted_df = pd.concat([df_corrupt, dup_rows], ignore_index=True)
    corrupted_indices = list(range(len(df_corrupt), len(corrupted_df)))

    ground_truth = {
        "problem_type": "exact_duplicates",
        "level": "row",
        "rate": rate,
        "is_corrupted": True,
        "corrupted_indices": corrupted_indices,
        "metadata": {"num_duplicates": len(corrupted_indices)},
    }
    return corrupted_df, ground_truth


# ---------------------------------------------------------------------------
# Problem f: Near-Duplicates (Slightly altered timestamp or text)
# ---------------------------------------------------------------------------
def inject_near_duplicates(
    df: pd.DataFrame, rate: float = 0.05, seed: int = RANDOM_SEED
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Injects near-duplicates: same request with slight timestamp drift or minor text typos.
    
    Why: Users submitting the same issue twice via mobile app 2 minutes apart,
    or automated polling retries with micro-variations.
    """
    df_corrupt = df.copy()
    target_idx = _get_sample_indices(df_corrupt, rate, seed)
    dup_rows = df_corrupt.loc[target_idx].copy()
    
    rng = random.Random(seed)
    new_indices = []
    
    for i, (_, row) in enumerate(dup_rows.iterrows()):
        new_row = row.copy()
        # Give unique key a new suffix so it isn't an exact PK duplicate
        new_row["unique_key"] = f"{row['unique_key']}_dup"
        
        # Alter timestamp by +30 to 120 seconds
        try:
            ts = pd.to_datetime(row["created_date"])
            new_row["created_date"] = (ts + pd.Timedelta(seconds=rng.randint(30, 180))).isoformat()
        except Exception:
            pass
            
        # Introduce subtle typographical mutation in descriptor or resolution
        desc = str(row["descriptor"])
        if len(desc) > 5:
            # swap two characters or append whitespace
            pos = rng.randint(0, len(desc) - 2)
            mutated_desc = desc[:pos] + desc[pos+1] + desc[pos] + desc[pos+2:]
            new_row["descriptor"] = mutated_desc
        else:
            new_row["descriptor"] = f"{desc} ."

        dup_rows.iloc[i] = new_row

    corrupted_df = pd.concat([df_corrupt, dup_rows], ignore_index=True)
    new_indices = list(range(len(df_corrupt), len(corrupted_df)))

    ground_truth = {
        "problem_type": "near_duplicates",
        "level": "row",
        "rate": rate,
        "is_corrupted": True,
        "corrupted_indices": new_indices,
        "metadata": {"num_near_duplicates": len(new_indices)},
    }
    return corrupted_df, ground_truth


# ---------------------------------------------------------------------------
# Problem g: Null Spike in One Agency's Records
# ---------------------------------------------------------------------------
def inject_null_spike(
    df: pd.DataFrame, rate: float = 0.80, seed: int = RANDOM_SEED
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Spikes null values in a key field (e.g. descriptor or incident_zip) for one specific agency.
    
    Why: When a single municipal agency updates its integration endpoint or
    drops a mapping table, its tickets arrive with 80%+ missing descriptors.
    """
    df_corrupt = df.copy()
    # Find most frequent agency
    top_agency = df_corrupt["agency"].value_counts().index[0]
    agency_mask = df_corrupt["agency"] == top_agency
    agency_indices = df_corrupt[agency_mask].index.tolist()
    
    rng = random.Random(seed)
    n_corrupt = int(round(len(agency_indices) * rate))
    corrupt_idx = rng.sample(agency_indices, min(n_corrupt, len(agency_indices)))
    
    for idx in corrupt_idx:
        df_corrupt.at[idx, "descriptor"] = None

    ground_truth = {
        "problem_type": "null_spike",
        "level": "batch",
        "rate": rate,
        "is_corrupted": True,
        "corrupted_indices": corrupt_idx,
        "metadata": {"target_agency": top_agency, "target_column": "descriptor", "spike_rate": rate},
    }
    return df_corrupt, ground_truth


# ---------------------------------------------------------------------------
# Problem h: Closed Date Earlier Than Created Date
# ---------------------------------------------------------------------------
def inject_closed_earlier_than_created(
    df: pd.DataFrame, rate: float = 0.05, seed: int = RANDOM_SEED
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Sets closed_date chronologically earlier than created_date.
    
    Why: Time zone handling bugs, clock skew on dispatcher terminals,
    or operator back-dating errors.
    """
    df_corrupt = df.copy()
    target_idx = _get_sample_indices(df_corrupt, rate, seed)
    
    rng = random.Random(seed)
    for idx in target_idx:
        try:
            created_ts = pd.to_datetime(df_corrupt.at[idx, "created_date"])
            # Subtract 1 to 5 days
            shift_hours = rng.randint(24, 120)
            corrupt_closed = created_ts - pd.Timedelta(hours=shift_hours)
            df_corrupt.at[idx, "closed_date"] = corrupt_closed.isoformat()
        except Exception:
            df_corrupt.at[idx, "closed_date"] = "2022-01-01T00:00:00.000"

    ground_truth = {
        "problem_type": "closed_earlier_than_created",
        "level": "row",
        "rate": rate,
        "is_corrupted": True,
        "corrupted_indices": target_idx,
        "metadata": {"num_rows": len(target_idx)},
    }
    return df_corrupt, ground_truth


# ---------------------------------------------------------------------------
# Problem i: ZIP Code Inconsistent with Borough
# ---------------------------------------------------------------------------
def inject_zip_inconsistent_borough(
    df: pd.DataFrame, rate: float = 0.05, seed: int = RANDOM_SEED
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Replaces borough with a completely incompatible NYC borough for the row's ZIP.
    
    Why: Address auto-complete errors or cross-boundary jurisdictional confusion.
    """
    df_corrupt = df.copy()
    target_idx = _get_sample_indices(df_corrupt, rate, seed)
    
    boroughs = ["MANHATTAN", "BRONX", "BROOKLYN", "QUEENS", "STATEN ISLAND"]
    rng = random.Random(seed)
    
    for idx in target_idx:
        curr_b = str(df_corrupt.at[idx, "borough"]).upper()
        # Pick a different borough
        alternatives = [b for b in boroughs if b != curr_b]
        new_b = rng.choice(alternatives)
        df_corrupt.at[idx, "borough"] = new_b

    ground_truth = {
        "problem_type": "zip_inconsistent_borough",
        "level": "row",
        "rate": rate,
        "is_corrupted": True,
        "corrupted_indices": target_idx,
        "metadata": {"num_rows": len(target_idx)},
    }
    return df_corrupt, ground_truth


# ---------------------------------------------------------------------------
# Problem j: Complaint Type Inconsistent with Descriptor
# ---------------------------------------------------------------------------
def inject_complaint_inconsistent_descriptor(
    df: pd.DataFrame, rate: float = 0.05, seed: int = RANDOM_SEED
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Pairs mutually contradictory complaint types and descriptors.
    
    Why: Frontend UI dropdown desynchronization or misclassified category selection.
    """
    df_corrupt = df.copy()
    target_idx = _get_sample_indices(df_corrupt, rate, seed)
    
    # Incompatible pairs: (Complaint Type, Incompatible Descriptor)
    absurd_pairs = [
        ("Street Light Condition", "Loud Music/Party inside Apartment"),
        ("Rodent", "Pothole in Right Lane"),
        ("Noise - Residential", "Dead Animal on Highway"),
        ("Sewer", "No Hot Water or Heat in Radiator"),
        ("Traffic Signal Condition", "Bed Bugs Infestation in Mattress"),
        ("Graffiti", "Missing Street Name Sign"),
    ]
    rng = random.Random(seed)
    
    for idx in target_idx:
        c_type, desc = rng.choice(absurd_pairs)
        df_corrupt.at[idx, "complaint_type"] = c_type
        df_corrupt.at[idx, "descriptor"] = desc

    ground_truth = {
        "problem_type": "complaint_inconsistent_descriptor",
        "level": "row",
        "rate": rate,
        "is_corrupted": True,
        "corrupted_indices": target_idx,
        "metadata": {"num_rows": len(target_idx)},
    }
    return df_corrupt, ground_truth


# ---------------------------------------------------------------------------
# Problem k: Resolution Description Contradicting Status
# ---------------------------------------------------------------------------
def inject_resolution_contradicting_status(
    df: pd.DataFrame, rate: float = 0.05, seed: int = RANDOM_SEED
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Pairs 'Closed' status with active/unresolved text, or 'Open' status with resolved text.
    
    Why: Workflow state machines where the ticket status field transitions
    without updating the resolution memo, leading to CFO dashboard confusion.
    """
    df_corrupt = df.copy()
    target_idx = _get_sample_indices(df_corrupt, rate, seed)
    
    rng = random.Random(seed)
    unresolved_texts = [
        "The condition is still active and under investigation. Inspector scheduled for next Tuesday.",
        "Unable to investigate at this time due to lack of access. Complaint remains OPEN.",
        "Work in progress. Repair crew dispatched to site, condition has not yet been resolved.",
    ]
    resolved_texts = [
        "The Department of Housing Preservation and Development inspected the condition and verified it was fully resolved. Case CLOSED.",
        "All repairs have been completed and verified by site inspector. Issue closed.",
    ]
    
    for idx in target_idx:
        if rng.random() > 0.5:
            # Closed status with active/unresolved resolution text
            df_corrupt.at[idx, "status"] = "Closed"
            df_corrupt.at[idx, "resolution_description"] = rng.choice(unresolved_texts)
        else:
            # Open status with resolved resolution text
            df_corrupt.at[idx, "status"] = "Open"
            df_corrupt.at[idx, "resolution_description"] = rng.choice(resolved_texts)

    ground_truth = {
        "problem_type": "resolution_contradicting_status",
        "level": "row",
        "rate": rate,
        "is_corrupted": True,
        "corrupted_indices": target_idx,
        "metadata": {"num_rows": len(target_idx)},
    }
    return df_corrupt, ground_truth


# ---------------------------------------------------------------------------
# Problem l: Personal Data (PII) Inside Free-Text Fields
# ---------------------------------------------------------------------------
def inject_personal_data_in_text(
    df: pd.DataFrame, rate: float = 0.05, seed: int = RANDOM_SEED
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Injects phone numbers, personal email addresses, and full names into free text.
    
    Why: Complainants typing their private contact details into public complaint boxes,
    triggering GDPR/CCPA compliance breaches.
    """
    df_corrupt = df.copy()
    target_idx = _get_sample_indices(df_corrupt, rate, seed)
    
    pii_samples = [
        "Caller John Doe requested call back at 212-555-0143 or email jdoe_personal@gmail.com",
        "Contact superintendent Sarah Jenkins on mobile (917) 842-1984 regarding key access",
        "Tenant Michael Chang (SSN: 032-45-XXXX, Cell: 646.555.0199) requested immediate inspection",
        "Please update resident directly at emily.watson92@yahoo.com or text 347-555-8821",
    ]
    rng = random.Random(seed)
    
    for idx in target_idx:
        orig_text = str(df_corrupt.at[idx, "resolution_description"])
        pii = rng.choice(pii_samples)
        df_corrupt.at[idx, "resolution_description"] = f"{orig_text} [NOTE: {pii}]"

    ground_truth = {
        "problem_type": "personal_data_in_text",
        "level": "row",
        "rate": rate,
        "is_corrupted": True,
        "corrupted_indices": target_idx,
        "metadata": {"num_rows": len(target_idx)},
    }
    return df_corrupt, ground_truth


# ---------------------------------------------------------------------------
# Master Dispatcher and Fixed Evaluation Set Generator
# ---------------------------------------------------------------------------
INJECTOR_REGISTRY = {
    "renamed_or_dropped_column": inject_renamed_or_dropped_column,
    "column_type_change": inject_column_type_change,
    "date_format_switch": inject_date_format_switch,
    "lat_long_swapped": inject_lat_long_swapped,
    "exact_duplicates": inject_exact_duplicates,
    "near_duplicates": inject_near_duplicates,
    "null_spike": inject_null_spike,
    "closed_earlier_than_created": inject_closed_earlier_than_created,
    "zip_inconsistent_borough": inject_zip_inconsistent_borough,
    "complaint_inconsistent_descriptor": inject_complaint_inconsistent_descriptor,
    "resolution_contradicting_status": inject_resolution_contradicting_status,
    "personal_data_in_text": inject_personal_data_in_text,
}


def inject_problem(
    problem_type: str, df: pd.DataFrame, rate: float = 0.05, seed: int = RANDOM_SEED
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Generic entry point dispatching to specific corruption injector."""
    if problem_type not in INJECTOR_REGISTRY:
        raise ValueError(f"Unknown problem type: {problem_type}. Valid: {list(INJECTOR_REGISTRY.keys())}")
    return INJECTOR_REGISTRY[problem_type](df, rate=rate, seed=seed)


def generate_evaluation_dataset(
    clean_df: Optional[pd.DataFrame] = None,
    batch_size: int = EVAL_BATCH_SIZE,
    num_clean_batches: int = NUM_CLEAN_BATCHES,
    injection_rates: List[float] = EVAL_INJECTION_RATES,
    seed: int = RANDOM_SEED,
) -> Dict[str, Any]:
    """Generates and persists the complete fixed evaluation suite:
    - N clean batches (for false-alarm benchmark)
    - 12 problem types x 3 injection rates (1%, 5%, 20%)
    """
    if clean_df is None:
        clean_path = CLEAN_DATA_DIR / "clean_reference.parquet"
        if not clean_path.exists():
            raise FileNotFoundError("Clean reference dataset not found. Run profile.py first.")
        clean_df = pd.read_parquet(clean_path)

    rng = np.random.default_rng(seed)
    eval_suite = {
        "clean_batches": [],
        "injected_batches": {},
    }

    # Generate clean batches (shuffled independent samples)
    for b_idx in range(num_clean_batches):
        sampled = clean_df.sample(n=min(batch_size, len(clean_df)), random_state=seed + b_idx).reset_index(drop=True)
        batch_file = INJECTED_DATA_DIR / f"clean_batch_{b_idx}.parquet"
        sampled.to_parquet(batch_file, index=False)
        eval_suite["clean_batches"].append(str(batch_file))

    # Generate injected batches across all 12 problem types and rates
    for p_type in PROBLEM_TYPES:
        eval_suite["injected_batches"][p_type] = {}
        for rate in injection_rates:
            # Use clean batch 0 as standard base
            base_df = clean_df.sample(n=min(batch_size, len(clean_df)), random_state=seed).reset_index(drop=True)
            corrupt_df, gt = inject_problem(p_type, base_df, rate=rate, seed=seed)
            
            rate_pct = int(round(rate * 100))
            batch_file = INJECTED_DATA_DIR / f"injected_{p_type}_rate_{rate_pct}pct.parquet"
            gt_file = INJECTED_DATA_DIR / f"gt_{p_type}_rate_{rate_pct}pct.json"
            
            # Save corrupted batch and ground truth
            corrupt_df.to_parquet(batch_file, index=False)
            with open(gt_file, "w", encoding="utf-8") as f:
                import json
                json.dump(gt, f, indent=2, default=str)
                
            eval_suite["injected_batches"][p_type][rate] = {
                "batch_path": str(batch_file),
                "ground_truth_path": str(gt_file),
            }

    print(f"Generated complete evaluation suite: {num_clean_batches} clean batches and {len(PROBLEM_TYPES) * len(injection_rates)} injected batches.")
    return eval_suite


if __name__ == "__main__":
    generate_evaluation_dataset()
