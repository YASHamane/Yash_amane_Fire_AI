"""tests/test_regime_choice.py: the recommendation, the saving and the tie rule."""
from core.schema import TaxpayerInput
from impl_a_rules.engine import calculate


def test_new_regime_wins_for_plain_salary():
    r = calculate(TaxpayerInput(gross_salary=1200000, age_band="below_60"), "2024-25")
    assert r.recommended == "new"
    assert r.savings == r.old.total_tax - r.new.total_tax


def test_old_regime_wins_with_heavy_deductions():
    r = calculate(TaxpayerInput(gross_salary=1500000, age_band="below_60", basic_salary=750000,
                                hra_received=300000, rent_paid_annual=360000, city_type="metro",
                                section_80c=150000, section_80ccd_1b=50000,
                                section_80d_self_family=25000, home_loan_interest=200000), "2024-25")
    assert r.recommended == "old"
    assert r.savings == r.new.total_tax - r.old.total_tax


def test_tie_goes_to_new_regime_with_zero_saving():
    r = calculate(TaxpayerInput(gross_salary=0, age_band="below_60"), "2024-25")
    assert (r.old.total_tax, r.new.total_tax) == (0, 0)
    assert (r.recommended, r.savings) == ("new", 0)
