# Architecture & Design Decisions (Project A)

This document explains the end-to-end data flow, justifies the selection of rules vs LLMs for each pipeline stage based on empirical measurements, and details the design choices behind the compiled rule format.

---

## 1. End-to-End Data Flow

```
                                    User Text
                                        │
                                        ▼
                             ┌─────────────────────┐
                             │ nlp_input/extract   │  (LLM + Regex Entity Extractor)
                             └──────────┬──────────┘
                                        │ Raw Extracted Dict
                                        ▼
                             ┌─────────────────────┐
                             │ nlp_input/validate  │  (Pure Rule-Based Gate)
                             └──────────┬──────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
              [ Contradiction / Missing ]         [ Validated Data ]
                         │                             │
                         ▼                             ▼
              ┌─────────────────────┐       ┌─────────────────────┐
              │  nlp_input/clarify  │       │  core/schema.py     │
              │  "Ask, Don't Guess" │       │  TaxpayerInput      │
              └─────────────────────┘       └──────────┬──────────┘
                                                       │
                                                       ▼
                                            ┌─────────────────────┐
                                            │ core/rules_loader   │
                                            │ Deep-merge base + FY│
                                            └──────────┬──────────┘
                                                       │
                                                       ▼
                                            ┌─────────────────────┐
                                            │ impl_a_rules/engine │
                                            │  - slabs            │
                                            │  - deductions / HRA │
                                            │  - rebate 87A       │
                                            │  - surcharge relief │
                                            │  - cess & 288A/B    │
                                            └──────────┬──────────┘
                                                       │
                                                       ▼
                                            ┌─────────────────────┐
                                            │  core/schema.py     │
                                            │  TaxResult + Trace  │
                                            └─────────────────────┘
```

---

## 2. Component Design Justifications (Rule vs LLM vs Hybrid)

### Stage 1: Free-Text Extraction & Normalization
- **Choice:** **Hybrid (LLM with deterministic regex pre-parser)**
- **Why LLM?** Natural language is infinitely variable: users submit Hinglish ("kuch rent nahi deta"), colloquial terms ("18L CTC", "1.2 Cr", "40k/month"), and incomplete descriptions. Pure regex patterns struggle with long-tail linguistic nuances.
- **Why Rule-Based Guardrails?** LLMs are prone to hallucinating missing parameters (e.g., guessing an age of 30 when omitted). The rule validator strictly enforces **"Ask, Don't Guess"**, achieving a measured **0.0% wrongly guessed rate**.

### Stage 2: Tax Calculation Engine
- **Choice:** **Deterministic Hand-Coded Rules (Implementation a)**
- **Why NOT an LLM at Runtime?**
  - **Accuracy:** The raw LLM at query time achieved only **38.7% - 50.0%** rupee-exact accuracy on progressive slabs, surcharge marginal relief, and 87A rebate cliff steps. Hand-coded rules achieved **100.0%** across all 292 test cases.
  - **Silent Failure Risk:** The runtime LLM failed silently on **61.3%** of FY 2025-26 cases, producing wrong numbers with zero exceptions. In tax compliance, silent failure is catastrophic.
  - **Latency:** Hand-coded rules execute in **0.08ms** (p50). The LLM requires **1,250ms** (p50) — a **15,000x slowdown**.
  - **Cost:** Hand-coded rules cost **Rs 0.00**. Serving 100,000 users with an LLM at runtime would cost **Rs 1,784** in notional inference fees.

### Stage 3: Auditability & Traceability
- **Choice:** **Deterministic Rules (`TraceLine`)**
- **Justification:** Every rupee of tax, deduction, rebate, and surcharge is mathematically reconciled to an official statutory clause (`Sec 16(ia)`, `Sec 87A`, `Sec 115BAC`, `Sec 288A/B`). Impl (a) achieved **100.0% rupee traceability**.

---

## 3. Choice of Restricted Rule Format for Implementation (c)

In `impl_c_llm_compiled`, the LLM converts rule text into executable code **once offline**. We chose a restricted Python specification consisting of **pure functions and immutable declarative dictionaries**:
```python
def get_slabs(regime: str, age_band: str) -> list[dict]: ...
def get_rebate_87a_params(regime: str) -> dict: ...
def get_standard_deduction(regime: str) -> int: ...
```

### Why this format over a custom YAML/JSON DSL?
1. **Expressiveness for Marginal Relief:** Statutory tax law contains non-linear constraints (e.g. marginal relief capping tax at income excess). Representing dynamic arithmetic in pure JSON/YAML requires inventing an entire expression mini-language (custom DSL). Python functions natively express conditions without interpreter overhead.
2. **Zero Runtime Overhead:** Python modules compile to bytecode instantly, executing with zero network calls and sub-millisecond latencies.
3. **Auditable Human Review:** Diffing a Python module during human review (`REVIEW_LOG.md`) is straightforward for software engineers and tax specialists.

---

## 4. Scaling to 100,000 Users

At 100,000 concurrent users during peak tax season (July 31 filing deadline):
- **Throughput:** A single Python process executing `impl_a_rules` handles >10,000 calculations per second per core. A 4-core worker pool can effortlessly process 100,000 filings in under 3 seconds.
- **Cost:** Negligible compute cost, zero LLM API dependency on the calculation hot path.
- **Reliability:** 100% deterministic, zero rate-limit throttles or network failure modes.
