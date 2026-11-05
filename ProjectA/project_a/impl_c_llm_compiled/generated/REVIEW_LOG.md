# Human Review Log: LLM-Compiled Rules (impl_c_llm_compiled)

**File Reviewed:** `generated/rules_fy2024_25.py`  
**Generated From:** `rules_data/rule_text/fy2024_25.md`  
**Reviewer:** Yash Amane (GitHub: @YASHamane)  
**Date:** 2026-11-05  

---

## 1. Executive Summary
The LLM compilation step translated the natural-language statutory text into a restricted Python specification. While the LLM correctly identified standard slabs and standard deduction amounts, it introduced three subtle, high-severity bugs that would have resulted in silent calculation errors without manual human review and verification.

---

## 2. Issues Caught & Human Fixes Applied

### Issue 1: Missing Marginal Relief Proviso for Section 87A (New Regime)
- **What the LLM generated:**
  The LLM defined `get_rebate_87a_params("new")` with `{"limit": 700000, "max_rebate": 25000, "marginal_relief": False}`.
- **Why it is wrong:**
  Under Section 87A first proviso clause (b) (inserted by Finance Act 2023), resident taxpayers with total income slightly exceeding Rs 7,00,000 receive marginal relief (tax payable cannot exceed total income minus Rs 7,00,000). Setting `marginal_relief: False` would have taxed an individual earning Rs 7,00,010 at Rs 20,001 (plus cess), completely missing the statutory marginal relief cliff protection!
- **Fix Applied:**
  Enabled `"marginal_relief": True` and linked the statutory clause `Sec 87A, first proviso (b)`.

### Issue 2: Conflation of Senior Citizen Age Bands in 80D
- **What the LLM generated:**
  Combined 80D for self and parents into a single `{"cap": 50000}` dictionary without distinguishing the taxpayer's age band from the parents' senior citizen status (`parents_are_senior`).
- **Why it is wrong:**
  Section 80D provides two independent limits: up to Rs 25,000 (Rs 50,000 if senior) for self/family, and a separate Rs 25,000 (Rs 50,000 if senior) for parents. Conflating them allowed only Rs 50,000 aggregate instead of up to Rs 1,00,000 when both are seniors.
- **Fix Applied:**
  Separated `section_80d_self_family` and `section_80d_parents` with distinct `cap` and `cap_if_senior` fields matching statutory provisions.

### Issue 3: Use of Floating Point Rates
- **What the LLM generated:**
  Used `0.05`, `0.10`, `0.20`, `0.30` as float rates.
- **Why it is wrong:**
  Floating point math introduces binary representation inaccuracies that cause off-by-one rupee discrepancies under Sec 288A/Sec 288B rounding checks.
- **Fix Applied:**
  Enforced integer percentages (`rate_pct: 5`, `rate_pct: 20`, etc.) and exact `Fraction` evaluation in runtime arithmetic.

---

## 3. Conclusion & Takeaway
LLM-assisted compilation accelerates boilerplate generation, but automated formal verification (oracle comparisons) and rigorous line-by-line human review are mandatory safeguards against silent legal drafting hallucinations.
