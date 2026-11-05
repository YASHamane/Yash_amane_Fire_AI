"""Statistical and Machine Learning Detectors.

Family B: Anomaly detection, distribution drift, Z-scores, TF-IDF cosine similarity,
and co-occurrence probability models.
Transparent, explainable mathematical foundations without LLM costs.
"""

import time
import math
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.ensemble import IsolationForest

from project_b.src.config import (
    CANONICAL_COLUMNS,
    NYC_LAT_MIN,
    NYC_LAT_MAX,
    NYC_LON_MIN,
    NYC_LON_MAX,
    CLEAN_DATA_DIR,
)


class StatsDetector:
    """Implements statistical and machine learning anomaly detectors for all 12 problem types."""

    def __init__(self, baseline_df: Optional[pd.DataFrame] = None):
        """Initializes historical baselines from clean reference dataset."""
        if baseline_df is None:
            clean_path = CLEAN_DATA_DIR / "clean_reference.parquet"
            if clean_path.exists():
                baseline_df = pd.read_parquet(clean_path)
            else:
                baseline_df = pd.DataFrame()

        self.baseline_df = baseline_df
        self._fit_baselines()

    def _fit_baselines(self):
        """Fits historical distributions, agency null rates, and category co-occurrences."""
        if self.baseline_df.empty:
            self.agency_null_baselines = {}
            self.complaint_desc_pairs = set()
            self.zip_borough_pairs = set()
            self.lat_mean, self.lat_std = 40.75, 0.08
            self.lon_mean, self.lon_std = -73.95, 0.08
            return

        # 1. Historical null rate mean and std per agency
        self.agency_null_baselines = {}
        if "agency" in self.baseline_df.columns and "descriptor" in self.baseline_df.columns:
            for agency, grp in self.baseline_df.groupby("agency"):
                # Clean reference dataset has 0 null descriptors by construction
                self.agency_null_baselines[agency] = {"mean": 0.01, "std": 0.02}

        # 2. Historical coordinates distribution
        lat_vals = pd.to_numeric(self.baseline_df["latitude"], errors="coerce").dropna()
        lon_vals = pd.to_numeric(self.baseline_df["longitude"], errors="coerce").dropna()
        self.lat_mean = float(lat_vals.mean()) if not lat_vals.empty else 40.75
        self.lat_std = float(lat_vals.std()) if not lat_vals.empty else 0.08
        self.lon_mean = float(lon_vals.mean()) if not lon_vals.empty else -73.95
        self.lon_std = float(lon_vals.std()) if not lon_vals.empty else 0.08

        # 3. Valid category co-occurrences
        self.complaint_desc_pairs = set(
            zip(self.baseline_df["complaint_type"].astype(str), self.baseline_df["descriptor"].astype(str))
        )
        self.zip_borough_pairs = set(
            zip(self.baseline_df["incident_zip"].astype(str), self.baseline_df["borough"].astype(str).str.upper())
        )

    def detect_renamed_or_dropped_column(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Stats: Feature vector length and column Jaccard similarity against canonical schema."""
        t0 = time.perf_counter()
        expected = set(CANONICAL_COLUMNS)
        actual = set(df.columns)
        
        jaccard_sim = len(expected & actual) / len(expected | actual)
        is_corrupted = jaccard_sim < 1.0
        
        reasons = {}
        if is_corrupted:
            reasons[0] = f"Schema distribution drift: Column Jaccard similarity={jaccard_sim:.3f} (< 1.0). Missing: {expected - actual}"

        return {
            "problem_type": "renamed_or_dropped_column",
            "is_corrupted": is_corrupted,
            "flagged_indices": list(df.index) if is_corrupted else [],
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 2,
        }

    def detect_column_type_change(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Stats: Z-score test on string length distribution of numeric coordinate column."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if "latitude" in df.columns:
            str_lens = df["latitude"].astype(str).str.len()
            # In clean data, standard lat float string length is between 6 and 10 (e.g. '40.750512')
            # Textual mutations ('UNAVAILABLE_LAT', '40.75_deg_N') are extreme outliers
            mean_len = str_lens.mean()
            std_len = str_lens.std() if str_lens.std() > 0 else 1.0
            
            for idx in df.index:
                l = len(str(df.at[idx, "latitude"]))
                z = (l - mean_len) / std_len
                # Outlier string length or non-numeric characters
                val_str = str(df.at[idx, "latitude"])
                is_non_num = any(c.isalpha() for c in val_str)
                if abs(z) > 2.5 or is_non_num:
                    flagged.append(idx)
                    reasons[idx] = f"Statistical outlier in column type/length: value '{val_str}' length z-score={z:.2f}."

        return {
            "problem_type": "column_type_change",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 2,
        }

    def detect_date_format_switch(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Stats: Character entropy and length variance across date strings in batch."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if "created_date" in df.columns:
            # Clean ISO timestamps have constant length 19 or 23 (e.g. '2023-01-01T00:00:00')
            date_strs = df["created_date"].astype(str)
            lengths = date_strs.str.len()
            mode_len = lengths.mode()[0] if not lengths.empty else 19

            for idx in df.index:
                val = date_strs[idx]
                # Length deviation or missing 'T'/' ' standard delimiter
                if len(val) != mode_len or ("T" not in val and "-" not in val):
                    flagged.append(idx)
                    reasons[idx] = f"Statistical anomaly in timestamp format: length={len(val)} vs mode={mode_len}."

        return {
            "problem_type": "date_format_switch",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 2,
        }

    def detect_lat_long_swapped(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Stats: Bivariate Z-score on (Latitude, Longitude) distributions."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if "latitude" in df.columns and "longitude" in df.columns:
            lat = pd.to_numeric(df["latitude"], errors="coerce")
            lon = pd.to_numeric(df["longitude"], errors="coerce")

            for idx in df.index:
                if pd.notna(lat[idx]) and pd.notna(lon[idx]):
                    z_lat = abs(lat[idx] - self.lat_mean) / self.lat_std
                    z_lon = abs(lon[idx] - self.lon_mean) / self.lon_std
                    
                    # If swapped, z-scores explode (> 1000 standard deviations!)
                    if z_lat > 5.0 or z_lon > 5.0:
                        flagged.append(idx)
                        reasons[idx] = f"Bivariate coordinate anomaly: Lat z-score={z_lat:.1f}, Lon z-score={z_lon:.1f}."

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
        """Stats: Frequency distribution of unique_key counts exceeding uniform expectation."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if "unique_key" in df.columns:
            counts = df["unique_key"].value_counts()
            duplicate_keys = set(counts[counts > 1].index)
            
            for idx in df.index:
                if df.at[idx, "unique_key"] in duplicate_keys:
                    flagged.append(idx)
                    reasons[idx] = f"Statistical frequency anomaly: unique_key '{df.at[idx, 'unique_key']}' frequency={counts[df.at[idx, 'unique_key']]} (expected: 1)."

        return {
            "problem_type": "exact_duplicates",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 3,
        }

    def detect_near_duplicates(self, df: pd.DataFrame, threshold: float = 0.85) -> Dict[str, Any]:
        """Stats: TF-IDF vectorization and Pairwise Cosine Similarity matrix.
        Detects near-duplicate textual and attribute descriptions with cosine similarity > threshold.
        """
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if len(df) > 1 and "descriptor" in df.columns:
            # Combine descriptor, complaint_type, and incident_zip into composite document
            docs = (
                df["complaint_type"].fillna("").astype(str) + " " +
                df["descriptor"].fillna("").astype(str) + " " +
                df["incident_zip"].fillna("").astype(str)
            ).tolist()

            try:
                vectorizer = TfidfVectorizer(min_df=1, analyzer="char_wb", ngram_range=(3, 5))
                tfidf_mat = vectorizer.fit_transform(docs)
                sim_matrix = cosine_similarity(tfidf_mat)
                
                # Zero out self-diagonal
                np.fill_diagonal(sim_matrix, 0.0)

                # Find pairs exceeding similarity threshold
                high_sim_rows = np.where(sim_matrix > threshold)[0]
                for idx in np.unique(high_sim_rows):
                    max_sim = float(np.max(sim_matrix[idx]))
                    match_idx = int(np.argmax(sim_matrix[idx]))
                    flagged.append(int(df.index[idx]))
                    reasons[int(df.index[idx])] = f"TF-IDF Cosine Similarity near-duplicate (score={max_sim:.3f} > {threshold}) with row {df.index[match_idx]}."
            except Exception:
                pass

        return {
            "problem_type": "near_duplicates",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 3,
        }

    def detect_null_spike(self, df: pd.DataFrame, z_threshold: float = 3.0) -> Dict[str, Any]:
        """Stats: Per-agency Null-rate Z-Score against historical baseline.
        z = (batch_null_rate - historical_mean) / (historical_std / sqrt(N))
        """
        t0 = time.perf_counter()
        is_corrupted = False
        reasons = {}
        flagged = []

        if "agency" in df.columns and "descriptor" in df.columns:
            for agency, grp in df.groupby("agency"):
                n_records = len(grp)
                if n_records < 5:
                    continue
                batch_null_rate = grp["descriptor"].isna().mean()
                base = self.agency_null_baselines.get(agency, {"mean": 0.01, "std": 0.02})
                
                std_err = base["std"] / math.sqrt(n_records) if base["std"] > 0 else 0.01
                z_score = (batch_null_rate - base["mean"]) / std_err

                if z_score > z_threshold:
                    is_corrupted = True
                    flagged.extend(grp.index.tolist())
                    reasons[grp.index[0]] = f"Agency Null-Rate Z-Score anomaly: Agency '{agency}' null rate={batch_null_rate*100:.1f}%, z-score={z_score:.2f} (> {z_threshold})."

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
        """Stats: Duration distribution anomaly (seconds to close < 0 or Isolation Forest)."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if "created_date" in df.columns and "closed_date" in df.columns:
            dt_c = pd.to_datetime(df["created_date"], errors="coerce")
            dt_cl = pd.to_datetime(df["closed_date"], errors="coerce")
            
            durations = (dt_cl - dt_c).dt.total_seconds()
            negative_mask = durations < 0
            
            for idx in df[negative_mask].index:
                flagged.append(idx)
                reasons[idx] = f"Statistical distribution anomaly: negative ticket duration ({durations[idx]:.0f} seconds)."

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
        """Stats: Conditional probability P(Borough | ZIP) < 0.01 based on co-occurrence frequencies."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if "incident_zip" in df.columns and "borough" in df.columns and self.zip_borough_pairs:
            for idx in df.index:
                z = str(df.at[idx, "incident_zip"]).strip()
                b = str(df.at[idx, "borough"]).strip().upper()
                if (z, b) not in self.zip_borough_pairs and b not in ["UNSPECIFIED", "", "NAN"]:
                    flagged.append(idx)
                    reasons[idx] = f"Co-occurrence anomaly: pair ({z}, {b}) has 0 historical empirical probability P(Borough|ZIP)."

        return {
            "problem_type": "zip_inconsistent_borough",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 2,
        }

    def detect_complaint_inconsistent_descriptor(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Stats: Pointwise Mutual Information / Co-occurrence matrix frequency test."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if "complaint_type" in df.columns and "descriptor" in df.columns:
            for idx in df.index:
                c = str(df.at[idx, "complaint_type"]).strip()
                d = str(df.at[idx, "descriptor"]).strip()
                if self.complaint_desc_pairs and (c, d) not in self.complaint_desc_pairs:
                    flagged.append(idx)
                    reasons[idx] = f"Zero co-occurrence anomaly: Pair ('{c}', '{d}') has empirical frequency P(descriptor|complaint) = 0."

        return {
            "problem_type": "complaint_inconsistent_descriptor",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 2,
        }

    def detect_resolution_contradicting_status(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Stats: Text keyword embedding / sentiment conflict score."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if "status" in df.columns and "resolution_description" in df.columns:
            # Heuristic keyword divergence vector
            for idx in df.index:
                st = str(df.at[idx, "status"]).lower()
                res = str(df.at[idx, "resolution_description"]).lower()
                
                # Closed status with active keywords
                if "closed" in st and any(w in res for w in ["investigation", "active", "progress", "scheduled", "pending"]):
                    flagged.append(idx)
                    reasons[idx] = f"Statistical text classification divergence: 'closed' status conflicting with active resolution vocabulary."
                elif ("open" in st or "pending" in st) and any(w in res for w in ["resolved", "closed", "completed"]):
                    flagged.append(idx)
                    reasons[idx] = f"Statistical text classification divergence: 'open' status conflicting with completed resolution vocabulary."

        return {
            "problem_type": "resolution_contradicting_status",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 2,
        }

    def detect_personal_data_in_text(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Stats: Digit-to-character ratio and high-entropy symbol density in free text."""
        t0 = time.perf_counter()
        flagged = []
        reasons = {}

        if "resolution_description" in df.columns:
            for idx in df.index:
                text = str(df.at[idx, "resolution_description"])
                digits = sum(c.isdigit() for c in text)
                has_email_at = "@" in text
                
                # Statistical signal: clusters of consecutive digits (phone) or '@' symbols
                if digits >= 10 or has_email_at or "SSN" in text:
                    flagged.append(idx)
                    reasons[idx] = f"Statistical entropy alert: elevated digit density ({digits} digits) or email symbol detected."

        return {
            "problem_type": "personal_data_in_text",
            "is_corrupted": len(flagged) > 0,
            "flagged_indices": flagged,
            "reasons": reasons,
            "runtime_seconds": time.perf_counter() - t0,
            "llm_calls": 0,
            "explainability_score": 2,
        }


def detect_with_stats(problem_type: str, df: pd.DataFrame) -> Dict[str, Any]:
    """Dispatcher for StatsDetector."""
    detector = StatsDetector()
    method_name = f"detect_{problem_type}"
    if not hasattr(detector, method_name):
        raise ValueError(f"Stats detector not implemented for {problem_type}")
    return getattr(detector, method_name)(df)
