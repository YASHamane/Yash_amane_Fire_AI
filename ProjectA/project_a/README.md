# Project A: Income-Tax Engine — Rules, LLM, or Both?

An auditable, rupee-exact Indian income-tax calculator for salaried individuals covering **FY 2024-25 (AY 2025-26)** and the **Finance Act 2025 (FY 2025-26 / AY 2026-27)** changes.

---

## 1. Quick Start

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- GNU Make or PowerShell

### Run Everything with One Command
```bash
make all
```
Or run the individual stages:
```bash
make test         # Run test cases and assertions against official calculator checks
make bench        # Run accuracy, determinism, latency, cost, and traceability benchmarks
make parse-eval   # Evaluate plain-language extraction and clarification on 50 user queries
make change       # Execute the FY 2025-26 Finance Act change experiment
make report       # Generate RESULTS_A.md from results/*.json
make ui           # Launch interactive web dashboard on localhost:8500
```

### Launch Interactive Web UI
```bash
python run_ui.py   # Or: make ui (opens dashboard at http://localhost:8500)
```

---

## 2. Architecture Diagram (ASCII)

```
                            [ USER INPUT ]
                 "Salary 15 LPA, Mumbai, paying 25k rent, age 32"
                                  │
                                  ▼
                   ┌───────────────────────────────┐
                   │    1. NLP INPUT PARSER        │
                   │    (Hybrid: LLM + Rules)      │
                   │    - Extracts entity fields   │
                   │    - Normalizes LPA, Cr, pm   │
                   │    - Rule-based validator:    │
                   │      "Ask, Don't Guess"       │
                   └──────────────┬────────────────┘
                                  │
         Missing / Contradictory? │ Valid TaxpayerInput
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
┌──────────────────┐                              ┌──────────────────┐
│ Clarifying       │                              │ 2. TAX ENGINE    │
│ Question         │                              │ (Hand-Coded /    │
│ ("Please specify │                              │  Compiled Rules) │
│ your gross       │                              │ - Base YAML +    │
│ annual salary")  │                              │   FY Overlay     │
└──────────────────┘                              │ - Exact Fraction │
                                                  │ - Sec 288A/288B  │
                                                  │   statutory rnd  │
                                                  └────────┬─────────┘
                                                           │
                                                           ▼ TaxResult
                                                  ┌──────────────────┐
                                                  │ 3. AUDIT TRACE   │
                                                  │ Every rupee tied │
                                                  │ to an official   │
                                                  │ statutory clause │
                                                  └──────────────────┘
```

---

## 3. The Three Implementations

1. **(a) Hand-Coded Rules (`impl_a_rules/`):**
   Statutory law parameters live strictly in declarative data (`rules_data/fy2024_25.yaml` and `fy2025_26.yaml`). Progressive slab logic, marginal relief formulas, and Chapter VI-A caps live in small, pure Python functions. Every step emits a structured `TraceLine`.
2. **(b) LLM at Runtime (`impl_b_llm_runtime/`):**
   Sends official statutory text (`rule_text/*.md`) plus user input to Gemini with `temperature=0`. Zero arithmetic post-correction in code. Shows raw LLM failure modes on multi-step progressive calculations.
3. **(c) LLM-Compiled Rules (`impl_c_llm_compiled/`):**
   LLM compiles the natural-language rule text into a restricted Python specification (`generated/rules_fy*.py`) once offline. Verified and fixed via human review (`REVIEW_LOG.md`). Executes with **zero network calls** and microsecond speed.

---

## 4. Glossary & Statutory Sections

- **FY (Financial Year):** The 12-month period in which income is earned (e.g. 1 April 2024 to 31 March 2025).
- **AY (Assessment Year):** The year following the FY in which income is assessed and taxed (FY 2024-25 = AY 2025-26).
- **Sec 16(ia):** Standard deduction for salaried employees (Rs 50,000 old regime; Rs 75,000 new regime).
- **Sec 10(13A) & Rule 2A:** House Rent Allowance (HRA) exemption (least of actual HRA, rent - 10% basic, or 50%/40% basic).
- **Sec 80C:** Deductions up to Rs 1,50,000 for EPF, PPF, ELSS, Life Insurance, etc.
- **Sec 80CCD(1B):** Additional voluntary NPS deduction up to Rs 50,000.
- **Sec 80D:** Health insurance premium deduction (Rs 25,000 self/family, Rs 50,000 for seniors).
- **Sec 24(b):** Deduction for interest paid on housing loan for self-occupied property (capped at Rs 2,00,000 in old regime; disallowed in new regime).
- **Sec 87A:** Rebate ensuring zero tax up to threshold (old: Rs 5L / Rs 12,500; new FY25: Rs 7L / Rs 25,000; new FY26: Rs 12L / Rs 60,000). Includes marginal relief clause.
- **Sec 115BAC:** The default New Tax Regime.
- **Sec 288A & 288B:** Statutory rounding of total taxable income and tax payable to nearest Rs 10 (paise ignored).
