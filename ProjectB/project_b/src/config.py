"""Configuration module for Project B: Data Quality Checks Pipeline.

Centralizes paths, column mappings, injection rates, detector settings,
and LLM cost assumptions.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_B_DIR = BASE_DIR / "project_b"
DATA_DIR = PROJECT_B_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
CLEAN_DATA_DIR = DATA_DIR / "clean"
INJECTED_DATA_DIR = DATA_DIR / "injected"
CACHE_DIR = DATA_DIR / "cache"
RESULTS_DIR = PROJECT_B_DIR / "results"

# Ensure all critical runtime directories exist
for directory in [RAW_DATA_DIR, CLEAN_DATA_DIR, INJECTED_DATA_DIR, CACHE_DIR, RESULTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Random seed for reproducible runs across injectors, splits, and models
RANDOM_SEED = 42

# Socrata NYC 311 API Endpoint and Dataset identifier
NYC_311_SODA_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.csv"
NYC_311_JSON_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
DATASET_ID = "erm2-nwe9"

# Socrata app token (optional, increases rate limits from 1,000 req/hr to 50,000 req/hr)
SOCRATA_APP_TOKEN = os.getenv("SOCRATA_APP_TOKEN", None)

# Canonical Column Names used consistently across our pipeline:
# Created Date, Closed Date, Complaint Type, Descriptor, Resolution Description,
# Status, Agency, Borough, Incident Zip, Latitude, Longitude, Unique Key.
CANONICAL_COLUMNS = [
    "unique_key",
    "created_date",
    "closed_date",
    "agency",
    "complaint_type",
    "descriptor",
    "status",
    "resolution_description",
    "incident_zip",
    "borough",
    "latitude",
    "longitude",
]

# Mapping from raw variant headers (e.g., SODA lowercase vs NYC Open Data Dec 2025 UI Title Case)
# to our canonical column names.
COLUMN_NAME_MAP = {
    # NYC Open Data Dec 2025 display titles (e.g. "Problem (formerly Complaint Type)")
    "Unique Key": "unique_key",
    "Created Date": "created_date",
    "Closed Date": "closed_date",
    "Agency": "agency",
    "Agency Name": "agency_name",
    "Complaint Type": "complaint_type",
    "Problem (formerly Complaint Type)": "complaint_type",
    "Descriptor": "descriptor",
    "Problem Detail (formerly Descriptor)": "descriptor",
    "Status": "status",
    "Resolution Description": "resolution_description",
    "Resolution Action Updated Date": "resolution_action_updated_date",
    "Incident Zip": "incident_zip",
    "Borough": "borough",
    "Latitude": "latitude",
    "Longitude": "longitude",
    # Classic SODA API lowercase identifiers
    "unique_key": "unique_key",
    "created_date": "created_date",
    "closed_date": "closed_date",
    "agency": "agency",
    "agency_name": "agency_name",
    "complaint_type": "complaint_type",
    "descriptor": "descriptor",
    "status": "status",
    "resolution_description": "resolution_description",
    "incident_zip": "incident_zip",
    "borough": "borough",
    "latitude": "latitude",
    "longitude": "longitude",
}

# The 12 assignment problem types
PROBLEM_TYPES = [
    "renamed_or_dropped_column",      # a
    "column_type_change",             # b
    "date_format_switch",             # c
    "lat_long_swapped",               # d
    "exact_duplicates",               # e
    "near_duplicates",                # f
    "null_spike",                     # g
    "closed_earlier_than_created",    # h
    "zip_inconsistent_borough",       # i
    "complaint_inconsistent_descriptor", # j
    "resolution_contradicting_status",  # k
    "personal_data_in_text",          # l
]

# Injection rates for benchmark evaluation (1%, 5%, 20%)
EVAL_INJECTION_RATES = [0.01, 0.05, 0.20]

# Batch sizes
EVAL_BATCH_SIZE = 1000
NUM_CLEAN_BATCHES = 5

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Published paid-tier pricing assumptions for Gemini 1.5 Flash (for pricing projection per 1M rows)
# Input: $0.075 per 1,000,000 tokens (for prompts <= 128k)
# Output: $0.30 per 1,000,000 tokens (for prompts <= 128k)
GEMINI_PRICE_INPUT_PER_M = 0.075
GEMINI_PRICE_OUTPUT_PER_M = 0.30

# Estimated AWS / Cloud compute cost per CPU-hour for rules & statistical detectors
# e.g., c6i.large ($0.085/hr for 2 vCPU -> ~$0.0425 per single core CPU-hour)
CPU_COST_PER_HOUR = 0.0425

# Geographic bounding box for New York City
NYC_LAT_MIN = 40.49
NYC_LAT_MAX = 40.92
NYC_LON_MIN = -74.26
NYC_LON_MAX = -73.69
