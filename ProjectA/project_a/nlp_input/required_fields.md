# Field Requirements & Defaulting Policy

## 1. Principles
Under Section 139 and general tax filing requirements, calculating tax liability requires specific factual disclosures. We adhere to **Ask, Don't Guess**:
- If an essential variable has no factual basis, guessing creates a silent, legally wrong tax calculation.
- If a missing parameter represents an optional deduction or exemption that the taxpayer has not stated, the safe, non-presumptive default is **0** (no deduction claimed).

---

## 2. Classification of Fields

| Field Name | Category | Safe Default | Why / Rationale |
| :--- | :--- | :--- | :--- |
| `gross_salary` | **REQUIRED** | None | Without gross income, taxable income cannot be derived. Vague expressions ("decent salary", "earning well") MUST trigger clarification. |
| `age_band` | **REQUIRED** | None | Slabs and 80D deduction ceilings differ significantly across age categories (`below_60`, `60_to_79`, `80_plus`). While new regime slabs are identical across age bands, old regime requires age band for basic exemption and 80D caps. If unspecified, parser must clarify age. |
| `basic_salary` | **CONDITIONAL** | 0 | Only required if HRA exemption is being claimed. Under Rule 2A, HRA exemption relies on basic salary. If rent is paid and HRA claimed, basic salary must be known. |
| `rent_paid_annual`| **CONDITIONAL** | 0 | Only required if HRA exemption is claimed. If 0 or absent and HRA is claimed, this represents a contradiction or missing data. |
| `hra_received` | **CONDITIONAL** | 0 | Only required if HRA exemption is claimed. |
| `city_type` | Safe Default | `"non_metro"` | If rent is paid and HRA is received, but city is not specified, defaulting to `non_metro` (40% ceiling) is conservative and non-inflationary. If city is named (e.g. Mumbai, Delhi), set to `metro`. |
| `section_80c` | Safe Default | `0` | Deductions are voluntary claims. If user does not mention PF, ELSS, or LIC, default is 0. |
| `section_80ccd_1b` | Safe Default | `0` | Voluntary NPS contribution. Default is 0. |
| `section_80d_self` | Safe Default | `0` | Voluntary health insurance. Default is 0. |
| `section_80d_parents`| Safe Default | `0` | Voluntary parental health insurance. Default is 0. |
| `parents_are_senior`| Safe Default | `False` | Conservative default unless explicitly stated. |
| `home_loan_interest`| Safe Default | `0` | Voluntary interest deduction. Default is 0. |

---

## 3. Contradictions & Ambiguities Caught by Validation
1. **HRA without Rent:** Claiming HRA exemption while stating "I live with parents and pay no rent".
2. **Basic Exceeds Gross:** Basic salary entered higher than gross annual salary.
3. **Ambiguous Numbers:** "I earn 12" without specifying Lakhs, Thousands, or Crores.
4. **Vague Salary:** "I have a good package in IT" without a rupee value.
