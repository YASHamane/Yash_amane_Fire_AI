# Sources for Project A (official only)

Rule: every number in `fy2024_25.yaml` and `fy2025_26.yaml` must point to an ID in this
file. Nothing is typed from memory. Blog sites (ClearTax, Taxguru, etc.) were used only
to find the official page, never as the source of a number.

Date accessed: 2026-11-05

Access note: several incometaxindia.gov.in pages block automated fetching (bot
detection). For those, the official wording below was read from the official publications
and page excerpts returned by search, not from an unverified secondary summary.
Rows marked "excerpt" are in that category.
Everything must still be confirmed on the official calculator (see
`tests/cases/official_calc_check.csv`).

## Official sources used

| ID | Source | URL | What it gives us |
|----|--------|-----|------------------|
| S1 | Income Tax Dept e-filing portal, "Salaried Individuals for AY 2025-26" (page last reviewed 02-Mar-2026) | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-3 | Slabs for 3 age bands, surcharge rates, marginal-relief rule for surcharge, 24(b), 80C, 80CCD(1B), 80D limits, deductions allowed in new regime (full page read) |
| S2 | Income Tax Dept, "Various deductions under the Income Tax Act" | https://www.incometaxindia.gov.in/w/various-deductions-under-the-income-tax-act | Standard deduction: Rs 50,000 old, Rs 75,000 new (excerpt) |
| S3 | Income Tax Dept, Section 16 text | https://www.incometaxindia.gov.in/w/section-16-63 | Proviso to 16(ia) inserted by Finance (No. 2) Act 2024 w.e.f. 1-4-2025 (excerpt) |
| S4 | Income Tax Dept, Section 115BAC text | https://www.incometaxindia.gov.in/w/section-115bac-4 | New-regime slab structure (statute) |
| S5 | Income Tax Dept, Computation of Tax for Individual | https://wm.incometaxindia.gov.in/w/computation-of-tax-for-individual-1 | FY 2025-26: basic exemption Rs 4,00,000 under 115BAC (excerpt, Phase 6) |
| S6 | Income Tax Dept e-filing portal, "Tax Slabs for AY 2026-27" | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-0 | FY 2025-26 slabs (excerpt, Phase 6) |
| S7 | Income Tax Dept, Section 87A text | https://www.incometaxindia.gov.in/w/section-87a-23 | Rebate statute: old regime and new-regime provisos, marginal relief clause (b), Finance Act 2025 amendments w.e.f. 1-4-2026 (excerpts) |
| S8 | Income Tax Dept, "What is the taxability of House Rent Allowance (HRA)?" | https://www.incometaxindia.gov.in/w/what-is-the-taxability-of-house-rent-allowance-hra- | HRA exemption = least of three; 50% for Kolkata, Chennai, Mumbai, Delhi, else 40% (excerpt) |
| S9 | Income Tax Dept, Sections 288A and 288B and "how to round off" guidance | https://www.incometaxindia.gov.in/w/section-288b-59 | Rounding of total income (Sec 288A) and of tax payable (Sec 288B) to nearest Rs 10 |
| S10 | Ministry of Finance / Finance Act 2025 (Section 115BAC & Section 87A amendments) | https://www.incometaxindia.gov.in/pages/budget-and-bills.aspx | FY 2025-26 (AY 2026-27) revised new regime slabs (0-4L nil, 4-8L 5%, 8-12L 10%, 12-16L 15%, 16-20L 20%, 20-24L 25%, >24L 30%), rebate 87A up to Rs 60,000 for income up to Rs 12,00,000, and marginal relief |

## Facts verified (FY 2024-25 / AY 2025-26)

From S1 (full page):
- Old regime slabs, below 60: nil to 2.5L, 5% to 5L, 20% to 10L, 30% above.
- Old regime slabs, 60 to 79: nil to 3L, 5% to 5L, 20% to 10L, 30% above.
- Old regime slabs, 80+: nil to 5L, 20% to 10L, 30% above.
- New regime slabs (all ages): nil to 3L, 5% to 7L, 10% to 10L, 15% to 12L, 20% to 15L, 30% above.
- Surcharge, old regime: 10% above 50L, 15% above 1Cr, 25% above 2Cr, 37% above 5Cr.
- Surcharge, new regime: 10% above 50L, 15% above 1Cr, 25% above 2Cr (no 37% tier).
- Marginal relief on surcharge: tax plus surcharge may not exceed (tax on the threshold income + income above the threshold). Thresholds 50L, 1Cr, 2Cr, 5Cr (5Cr old regime only).
- Cess 4% on tax plus surcharge, both regimes.
- Sec 24(b), self-occupied, loan on/after 1-4-1999 for purchase/construction: cap Rs 2,00,000. In the new regime only let-out interest is listed as allowed.
- 80C cap Rs 1,50,000. 80CCD(1B) cap Rs 50,000 (over and above 80C/80CCD(1)).
- 80D: Rs 25,000 self/spouse/children (Rs 50,000 if any of them is a senior citizen); Rs 25,000 parents (Rs 50,000 if a parent is a senior citizen); Rs 5,000 preventive check-up sits inside those limits.
- New regime allows only 80CCD(2), 80CCH and let-out 24(b) interest. HRA, 80C, 80CCD(1B), 80D and self-occupied 24(b) are not available.

From S2, S3:
- Standard deduction FY 2024-25: Rs 50,000 old, Rs 75,000 new (115BAC(1A)(ii)); lower of this and salary.

From S7 (Section 87A):
- Old regime: resident individual, total income <= Rs 5,00,000: rebate = 100% of tax or Rs 12,500, whichever is less. No age condition in the text.
- New regime (115BAC(1A)), proviso inserted by Finance Act 2023 w.e.f. 1-4-2024:
  (a) total income <= Rs 7,00,000: rebate = 100% of tax or Rs 25,000, whichever is less.
  (b) total income > Rs 7,00,000 and tax > (total income - 7,00,000): rebate = tax - (total income - 7,00,000). This is the marginal relief.
- The rebate is taken off the tax computed on total income, before cess.
- RESOLVED CONFLICT: S1 prints "Rs 20,000" for the new regime rebate; the statute (S7) says Rs 25,000. We use the statute. For FY 2024-25 slabs the tax at Rs 7,00,000 is exactly Rs 20,000, so the two give the same answer and the Rs 25,000 cap never binds.

From S8 (HRA):
- Exempt HRA = least of (1) actual HRA received, (2) rent paid minus 10% of salary, (3) 50% of salary if the house is in Kolkata, Chennai, Mumbai or Delhi, otherwise 40%. If no rent is paid, the exemption is zero.
- "Salary" for this purpose means basic salary plus dearness allowance (plus commission that is a fixed percentage of turnover).

From S9 (rounding):
- Sec 288A: total income is rounded to the nearest Rs 10 before tax is computed.
- Sec 288B: the amount payable (and refund due) is rounded to the nearest Rs 10. Paise are ignored first, then a last digit of 5 or more rounds up, 4 or less rounds down.
- Consequence for code: "ignore paise" means TRUNCATE, not round half-up.

From S10 (Finance Act 2025 for FY 2025-26):
- Section 115BAC(1A) revised slabs: 0-4L Nil, 4-8L 5%, 8-12L 10%, 12-16L 15%, 16-20L 20%, 20-24L 25%, >24L 30%.
- Section 87A rebate for new regime: threshold raised to Rs 12,00,000; max rebate Rs 60,000. Marginal relief: tax payable <= total income - 12,00,000.
- Standard deduction remains Rs 75,000 (new) / Rs 50,000 (old).

## Decisions (made by the author, not by law)

- Employer NPS 80CCD(2) is OUT of scope. The assignment's scope list does not include it, so the input schema has no field for it.
- 80D: premiums only. The "no premium, medical expenditure of a senior" option is out of scope.
- Metro for HRA: Delhi, Mumbai, Kolkata, Chennai only (S8).
