# Project B: Data-Quality Checks — Rules, Statistics, or LLM Review?

An enterprise data-quality engine designed to protect production dashboards from dirty data without drowning teams in false alarms or burning money on LLM calls.

## Overview

This project implements and evaluates three distinct detection paradigms across 12 realistic data corruption types on NYC 311 service request data:
1. **Declarative Rules / Schema Checks**: Fast, deterministic, zero-token cost vector checks.
2. **Statistical / Machine Learning Detectors**: Z-score drift, PSI/KS distributions, TF-IDF cosine similarity, and co-occurrence isolation.
3. **Large Language Model (LLM) Review**: Gemini 1.5 Flash evaluation with structured JSON schemas, disk caching, and sample-based auditing.
4. **Production Hybrid Pipeline**: Intelligent triage directing cheap deterministic rules on 100% of rows, statistical drift checks per batch, and LLM review only on high-ambiguity alerts.

---

## Quickstart & Reproduction

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Git
- (Optional for live LLM calls) Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### Setup
```bash
# Clone the repository
git clone <repo-url>
cd ProjectB

# Create virtual environment and install pinned dependencies
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt

# (Optional) Configure Gemini API Key
copy .env.example .env
# Edit .env with your GEMINI_API_KEY
```

### Reproduce Every Number with ONE Command
To run the complete benchmark suite, verify tests, and reproduce all reported numbers:

```bash
# Using python directly:
python run_all.py

# Or using make:
make all
```

### Launch Interactive UI Dashboard
To run the visual interactive dashboard for demonstrations and technical defense interviews:

```bash
python run_ui.py
# Or directly:
python project_b/src/app.py
```
This opens `http://localhost:8501` featuring:
1. **Real 2023 Defects Profiler**: Live inspect 4,313 temporal paradoxes, 1,614 postal mismatches, and 109,221 PII leaks.
2. **The 12 Problem Injectors**: Side-by-side clean vs injected diff viewer with ground-truth badges.
3. **Detector Benchmark Matrix**: Dynamic filtering by injection rate (1%, 5%, 20%) and detector family.
4. **Hybrid Pipeline Simulator**: Step-by-step trace showing Tier 1 Rules -> Tier 2 Stats -> Tier 3 Gemini LLM triage ($0.076/1M rows, 197x cheaper).
5. **Technical Defense Cheat Sheet**: Fast reference for live code modifications and interview scenarios.

---

## Deliverables Index
- [`RESULTS_B.md`](RESULTS_B.md): Comprehensive benchmark results, per-problem detection & false-alarm tables, real 2023 data anomalies, and 50M rows/day scale design.
- [`DECISION_MATRIX.md`](DECISION_MATRIX.md): Detailed component-by-component selection matrix, justifying choices with empirical measurements and analyzing engineering trade-offs.
- [`EXPLAINED.md`](EXPLAINED.md): Technical defense preparation guide, file walkthroughs, technique glossaries, and 30 interview Q&As.
- [`AI_USAGE.md`](AI_USAGE.md): Audit of AI tools utilized and real error resolution logs.
- [`project_b/`](project_b/): Core codebase containing injectors, detector families, hybrid pipeline, tests, and generated results.
