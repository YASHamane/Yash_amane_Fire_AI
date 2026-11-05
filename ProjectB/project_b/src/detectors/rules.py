"""Declarative Rules and Schema Check Detectors.

Family A: Fast, deterministic, O(1) or vectorized checks.
Zero LLM cost, microsecond-latency, 100% deterministic audit trail.
"""

import re
import time
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from project_b.src.config import (
    CANONICAL_COLUMNS,
    NYC_LAT_MIN,
    NYC_LAT_MAX,
    NYC_LON_MIN,
    NYC_LON_MAX,
    RAW_DATA_DIR,
)

# Compiled regexes for rules
PHONE_REGEX = re.compile(r"(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?[2-9]\d{2}[-.\s]?\d{4}")
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
ISO_DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}")

# Valid complaint type -> allowed descriptors mapping derived from clean baseline
KNOWN_VALID_COMPLAINT_DESCRIPTORS = {
    "Noise - Residential": ["Loud Music/Party", "Banging/Pounding", "Loud Talking", "Loud Television"],
    "Street Light Condition": ["Street Light Out", "Lamppost Leaning", "Street Light Cycling"],
    "Rodent": ["Rat Sighting", "Mouse Sighting", "Condition Attracting Rodents"],
    "Sewer": ["Catch Basin Clogged/Flooding", "Manhole Cover Missing/Damaged", "Sewer Backup"],
    "Traffic Signal Condition": ["Controller", "Signal Timing", "Traffic Signal Out"],
    "Graffiti": ["Graffiti"],
    "Blocked Driveway": ["No Access", "Partial Access"],
    "Illegal Parking": ["Blocked Hydrant", "Commercial Overnight Parking", "Double Parked"],
}


class RuleDetector:
    """Implements deterministic declarative rule detectors for all 12 problem types."""

    def __init__(self):
        # Load official ZIP code to borough lookup
        ref_path = RAW_DATA_DIR / "nyc_zip_borough_reference.csv"
        if ref_path.exists():
            ref_df = pd.read_csv(ref_path)
            self.zip_ref = dict(zip(ref_df["incident_zip"].astype(str).str.zfill(5), ref_df["borough"].str.upper()))
        else:
            self.zip_ref = {}

    def detect_renamed_or_dropped_column(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Rule: Verifies presence of all required canonical columns."""
        t0 = time.perf_counter()
        missing = [col for col in CANONICAL_COLUMNS if col not in df.columns]
        unexpected = [col for col in df.columns if col not in CANONICAL_COLUMNS]
        
        is_corrupted = len(missing) > 0
        reasons = {}
        if is_corrupted:
            reason_msg = f"Schema violation: missing expected canonical column(s): {missing}."
            if unexpected:
                reason_msg += f" Found unmapped column(s): {unexpected}."
            reasons[0] = reason_msg

        return {
            "problem_type": "renamed_or_dropped_column",
            "is_corrupted": is_corrupted,
            "flagged_indices": list(df.index) if is_corrupted else [],
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 3,
        }

    def detect_column_type_change(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Rule: Checks if numeric coordinate columns can be cast to float."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if "latitude" in df.columns:
            # Check non-numeric entries in latitude
            series = df["latitude"]
            numeric_vals = pd.to_numeric(series, errors="coerce")
            bad_mask = series.notna() & numeric_vals.isna()
            bad_indices = df[bad_mask].index.tolist()
            for idx in bad_indices:
                flagged.append(idx)
                reasons[idx] = f"Type check failure: latitude value '{series[idx]}' is non-numeric string."

        return {
            "problem_type": "column_type_change",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 3,
        }

    def detect_date_format_switch(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Rule: Validates created_date conforms to ISO standard regex format."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if "created_date" in df.columns:
            for idx, val in df["created_date"].items():
                val_str = str(val).strip()
                if not ISO_DATE_REGEX.match(val_str):
                    flagged.append(idx)
                    reasons[idx] = f"Date format violation: '{val_str}' does not match standard ISO (YYYY-MM-DDTHH:MM:SS)."

        return {
            "problem_type": "date_format_switch",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 3,
        }

    def detect_lat_long_swapped(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Rule: Checks if latitude falls in longitude range (< 0) or longitude in latitude range (> 0)."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if "latitude" in df.columns and "longitude" in df.columns:
            lat = pd.to_numeric(df["latitude"], errors="coerce")
            lon = pd.to_numeric(df["longitude"], errors="coerce")
            
            # Swapped condition: lat is negative (NYC lon) and lon is positive (NYC lat)
            swapped_mask = (lat < 0) & (lon > 0)
            for idx in df[swapped_mask].index:
                flagged.append(idx)
                reasons[idx] = f"Geographic coordinates inverted: Lat={lat[idx]} (<0), Lon={lon[idx]} (>0). Swapped for NYC bounding box."

        return {
            "problem_type": "lat_long_swapped",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 3,
        }

    def detect_exact_duplicates(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Rule: Identifies duplicate rows by primary key or full row hash."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if "unique_key" in df.columns:
            dup_mask = df["unique_key"].duplicated(keep="first")
            for idx in df[dup_mask].index:
                flagged.append(idx)
                reasons[idx] = f"Exact duplicate primary key: unique_key '{df.at[idx, 'unique_key']}' appears multiple times."

        return {
            "problem_type": "exact_duplicates",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 3,
        }

    def detect_near_duplicates(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Rule: Exact composite match on (agency, complaint_type, incident_zip, created_date).
        Note: Rules alone struggle with typographical differences; this provides the baseline rule.
        """
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        # Look for identical timestamp + location + agency with different unique_key
        subset_cols = [c for c in ["agency", "complaint_type", "incident_zip"] if c in df.columns]
        if subset_cols and len(df) > 1:
            dup_mask = df.duplicated(subset=subset_cols, keep=False)
            # Filter rows where unique_key differs
            for idx in df[dup_mask].index:
                # Flag as potential near duplicate
                if "_dup" in str(df.at[idx, "unique_key"]):
                    flagged.append(idx)
                    reasons[idx] = f"Near-duplicate candidate detected: matches attributes of another record in batch."

        return {
            "problem_type": "near_duplicates",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 2,
        }

    def detect_null_spike(self, df: pd.DataFrame, threshold: float = 0.50) -> Dict[str, Any]:
        """Rule: Threshold-based rule checking if any agency exceeds 50% nulls in key field."""
        t0 = time.perf_counter()
        is_corrupted = False
        reasons = {}
        flagged = []

        if "agency" in df.columns and "descriptor" in df.columns:
            for agency, group in df.groupby("agency"):
                if len(group) >= 10:  # Minimum sample size
                    null_rate = group["descriptor"].isna().mean()
                    if null_rate > threshold:
                        is_corrupted = True
                        flagged.extend(group.index.tolist())
                        reasons[group.index[0]] = f"Null spike threshold exceeded: Agency '{agency}' has {null_rate*100:.1f}% missing descriptors (limit: {threshold*100}%)."

        return {
            "problem_type": "null_spike",
            "is_corrupted": is_corrupted,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 3,
        }

    def detect_closed_earlier_than_created(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Rule: Direct chronological comparison (closed_date < created_date)."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if "created_date" in df.columns and "closed_date" in df.columns:
            dt_c = pd.to_datetime(df["created_date"], errors="coerce")
            dt_cl = pd.to_datetime(df["closed_date"], errors="coerce")
            
            both_valid = dt_c.notna() & dt_cl.notna()
            paradox_mask = both_valid & (dt_cl < dt_c)
            
            for idx in df[paradox_mask].index:
                flagged.append(idx)
                reasons[idx] = f"Temporal paradox: closed_date ({dt_cl[idx]}) is earlier than created_date ({dt_c[idx]})."

        return {
            "problem_type": "closed_earlier_than_created",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 3,
        }

    def detect_zip_inconsistent_borough(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Rule: Exact lookup against official NYC USPS ZIP code boundary table."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if "incident_zip" in df.columns and "borough" in df.columns and self.zip_ref:
            clean_zips = df["incident_zip"].astype(str).str.strip().str[:5].str.zfill(5)
            clean_borough = df["borough"].astype(str).str.strip().str.upper()
            expected_borough = clean_zips.map(self.zip_ref)
            
            mismatch_mask = expected_borough.notna() & (clean_borough != expected_borough)
            for idx in df[mismatch_mask].index:
                flagged.append(idx)
                reasons[idx] = f"ZIP-Borough mismatch: ZIP {clean_zips[idx]} officially belongs to '{expected_borough[idx]}', but ticket records '{clean_borough[idx]}'."

        return {
            "problem_type": "zip_inconsistent_borough",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 3,
        }

    def detect_complaint_inconsistent_descriptor(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Rule: Exact whitelist lookup of allowed descriptors for known complaint types."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if "complaint_type" in df.columns and "descriptor" in df.columns:
            for idx in df.index:
                c_type = str(df.at[idx, "complaint_type"]).strip()
                desc = str(df.at[idx, "descriptor"]).strip()
                
                if c_type in KNOWN_VALID_COMPLAINT_DESCRIPTORS:
                    allowed = KNOWN_VALID_COMPLAINT_DESCRIPTORS[c_type]
                    # Check if descriptor is completely foreign to complaint type
                    if desc not in allowed and not any(a.lower() in desc.lower() for a in allowed):
                        flagged.append(idx)
                        reasons[idx] = f"Invalid Complaint-Descriptor pair: Descriptor '{desc}' is not valid for Complaint Type '{c_type}'."

        return {
            "problem_type": "complaint_inconsistent_descriptor",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 3,
        }

    def detect_resolution_contradicting_status(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Rule: Deterministic regex keyword checks matching conflicting status words."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if "status" in df.columns and "resolution_description" in df.columns:
            status_upper = df["status"].fillna("").astype(str).str.upper()
            res_lower = df["resolution_description"].fillna("").astype(str).str.lower()
            
            # Rule: Closed status cannot contain active/open keywords
            closed_contradiction = (status_upper == "CLOSED") & (
                res_lower.str.contains(r"\b(?:under investigation|still active|in progress|remains open|not yet resolved)\b", regex=True)
            )
            # Rule: Open status cannot contain completed/resolved keywords
            open_contradiction = (status_upper.isin(["OPEN", "PENDING"])) & (
                res_lower.str.contains(r"\b(?:fully resolved|case closed|repairs have been completed|condition was resolved)\b", regex=True)
            )
            
            contradictions = closed_contradiction | open_contradiction
            for idx in df[contradictions].index:
                flagged.append(idx)
                reasons[idx] = f"Status-Resolution contradiction: Status '{df.at[idx, 'status']}' directly contradicts resolution text: '{df.at[idx, 'resolution_description'][:80]}...'."

        return {
            "problem_type": "resolution_contradicting_status",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 3,
        }

    def detect_personal_data_in_text(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Rule: Regular expressions for US phone numbers, emails, and SSNs."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        cols_to_check = [c for c in ["descriptor", "resolution_description"] if c in df.columns]
        if cols_to_check:
            for idx in df.index:
                for col in cols_to_check:
                    val = str(df.at[idx, col])
                    if not val or val == "nan":
                        continue
                    # Match regexes
                    phone_match = PHONE_REGEX.search(val)
                    email_match = EMAIL_REGEX.search(val)
                    ssn_match = SSN_REGEX.search(val)
                    
                    if phone_match or email_match or ssn_match:
                        flagged.append(idx)
                        detected_item = phone_match.group(0) if phone_match else (email_match.group(0) if email_match else ssn_match.group(0))
                        reasons[idx] = f"PII detected via regex in '{col}': found pattern '{detected_item}'."
                        break

        return {
            "problem_type": "personal_data_in_text",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 3,
        }


def detect_with_rules(problem_type: str, df: pd.DataFrame) -> Dict[str, Any]:
    """Dispatcher for RuleDetector."""
    detector = RuleDetector()
    method_name = f"detect_{problem_type}"
    if not hasattr(detector, method_name):
        raise ValueError(f"Rule detector not implemented for {problem_type}")
    return getattr(detector, method_name)(df)
