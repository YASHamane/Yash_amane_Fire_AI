# FY 2025-26 Law Change Experiment (Task 5)

**Subject:** Evaluation of statutory changes under Finance Act 2025 (AY 2026-27) across Implementations (a), (b), and (c).  
**Date:** 2026-11-05  
**Baseline Git Tag:** `before-fy2025-26`  
**Working Branch:** `feature/fy2025-26-change`  

---

## 1. Summary of Statutory Changes (Finance Act 2025)
1. **New Regime Slabs (Section 115BAC(1A)):**
   - Nil up to Rs 4,00,000
   - 5% from Rs 4,00,001 to Rs 8,00,000
   - 10% from Rs 8,00,001 to Rs 12,00,000
   - 15% from Rs 12,00,001 to Rs 16,00,000
   - 20% from Rs 16,00,001 to Rs 20,00,000
   - 25% from Rs 20,00,001 to Rs 24,00,000
   - 30% above Rs 24,00,000
2. **Rebate under Section 87A (New Regime):**
   - Threshold raised to Rs 12,00,000 with maximum rebate of Rs 60,00, effectively making taxable income up to Rs 12,00,000 tax-free.
   - Marginal relief enacted for total income exceeding Rs 12,00,000 (tax payable cannot exceed income minus Rs 12,00,000).
3. **Unchanged Provisions:**
   - Standard deduction remains Rs 50,000 (old) and Rs 75,000 (new).
   - Old regime slab rates, Chapter VI-A deductions (80C, 80D, 24b), surcharge thresholds, and 4% cess remain strictly identical.

---

## 2. Comparison Across Implementations

| Metric | (a) Hand-Coded Rules | (b) LLM at Query Time | (c) LLM-Compiled Rules |
| :--- | :--- | :--- | :--- |
| **Time Taken** | 15 minutes | 10 minutes (prompt edit) | 35 minutes (prompt + compile + human review) |
| **Files Touched** | `rules_data/fy2025_26.yaml`, `sources.md` | `rules_data/rule_text/fy2025_26.md` | `rule_text/fy2025_26.md`, `generated/rules_fy2025_26.py`, `REVIEW_LOG.md` |
| **Code Changes?** | **None** (zero Python lines changed) | None (rule text only) | Generated Python module created |
| **Test Accuracy (301 Cases)**| **100.0%** (301 / 301) | **38.7%** (sampled) | **100.0%** (after human review) |
| **Loud Errors** | 0 | 0 | 0 |
| **Silent Failures** | **0** | **61.3%** | **0** (caught & fixed in review) |
| **Regression on FY 2024-25** | **100% Passed** (292 / 292 identical) | Not applicable | **100% Passed** (292 / 292 identical) |

---

## 3. Analysis of Failures: The Danger of Silent Errors

### Implementation (a) - Hand-Coded Rules
- **Behavior:** By isolating law in declarative YAML overlays (`rules_data/fy2025_26.yaml`) and keeping logic in small pure functions, applying the Budget required editing only 24 lines of YAML.
- **Silent Failures:** **0**. All 301 test cases matched the statutory oracle rupee-for-rupee.
- **Regression:** Deep-merge guarantees that requests specifying `fy="2024-25"` load only the base YAML, preventing regression.

### Implementation (b) - LLM at Query Time
- **Behavior:** The prompt was updated with the new rule text in under 10 minutes. However, the runtime engine failed silently on 61.3% of test cases.
- **Evidence of Silent Failure:**
  - Case `rebate_new_marginal_100` (Gross salary Rs 12,75,100; total income Rs 12,00,100):
    - *Expected Tax Payable:* Rs 100 (plus 4% cess = Rs 100).
    - *LLM Output:* Rs 60,015.
    - *Why it failed silently:* The LLM computed raw slab tax (Rs 60,015) and ignored the statutory marginal relief proviso under Section 87A(b). The system returned a legally wrong number with HTTP 200 and zero errors!
  - Case `slab_new_1600000_+10`:
    - The LLM miscalculated the 15% tier cumulative sum, resulting in an off-by-Rs 4,000 arithmetic hallucination.

### Implementation (c) - LLM-Compiled Rules
- **Behavior:** The compiler generated `rules_fy2025_26.py`. During manual human inspection (see `REVIEW_LOG.md`), we caught that the raw compilation missed the 12L marginal relief formula.
- **Remediation:** After correcting the generated code and committing the fix, Implementation (c) achieved 100.0% accuracy across all 301 cases with zero network calls.

---

## 4. Regression Verification
The entire test suite for FY 2024-25 (292 test cases) was executed against the updated codebase:
- `impl_a_rules`: 292 / 292 passed (100.0%).
- `impl_c_llm_compiled`: 292 / 292 passed (100.0%).
- Result: **Zero regressions detected.**
