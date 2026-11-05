# AI Usage Statement (Project A)

## 1. Tools Used and Roles
- **Google Gemini (free tier via `google-genai` SDK / Gemini 2.5 Flash):**
  - Used in `impl_b_llm_runtime` for query-time tax calculation from natural-language rules.
  - Used in `impl_c_llm_compiled` for one-time compilation of markdown rule excerpts into executable Python specifications.
  - Used in `nlp_input/extract.py` for plain-language entity extraction.
- **Antigravity / Coding Assistant:**
  - Used as a pair-programming partner to scaffold directory structure, implement pytest fixtures, type hints, and benchmark harnesses.

---

## 2. One Specific Place Where the AI Was Wrong and How It Was Caught

### The Hallucination / Error
During the compilation of `rules_fy2024_25.py` in Implementation (c), the AI translated Section 87A for the new regime as:
```python
def get_rebate_87a_params(regime: str) -> dict:
    return {"limit": 700000, "max_rebate": 25000, "marginal_relief": False}
```
The AI completely omitted the marginal relief formula under Section 87A first proviso clause (b), assuming marginal relief only applied to surcharge on incomes above Rs 50 Lakh.

### The Real-World Consequence
Under the AI's compiled code:
- An individual earning Rs 7,00,000 paid **Rs 0** in tax.
- An individual earning Rs 7,00,010 was taxed at the full 10% bracket, paying **Rs 20,001** (plus cess) for earning just Rs 10 extra!

### How It Was Caught
1. **Independent Test Oracle:** The test suite generator (`generate_cases.py`) was written independently using statutory lookup tables (`tests/cases/oracle.py`), with test cases intentionally placed at small positive offsets (`rebate_new_marginal_10`, `rebate_new_marginal_100`).
2. **Automated Assertion Failure:** When running `pytest project_a/tests/test_compiled.py`, the test failed immediately:
   `AssertionError: Expected tax 10, got 20801`.
3. **Statutory Cross-Check:** We consulted the verified Income Tax Department source `sources.md [S7]` (Section 87A first proviso clause (b)):
   > *"Provided further that where the total income of the person exceeds seven hundred thousand rupees, the rebate... shall be equal to the amount of income-tax payable on such total income minus the amount by which total income exceeds seven hundred thousand rupees."*
4. **Resolution:** We amended the compiled code to set `"marginal_relief": True` and implemented the exact statutory formula, documented in `impl_c_llm_compiled/generated/REVIEW_LOG.md`.
