"""impl_a_rules/regime_choice.py

WHAT:  Picks the cheaper regime and explains the choice in rupees.
WHY:   The user's real question is "which regime?", not just "how much tax?".
HOW:   Ties go to the new regime because it is the default regime in law (S1).
"""
from __future__ import annotations

from core.schema import Regime, RegimeResult, TraceLine

CLAUSE = "Sec 115BAC (new regime is the default; old regime is opt-in)"


def choose_regime(old: RegimeResult, new: RegimeResult) -> tuple[Regime, int, tuple[TraceLine, ...]]:
    """Compares old and new regime tax liabilities, recommending the cheaper regime."""
    if old.total_tax < new.total_tax:
        rec, saving = "old", new.total_tax - old.total_tax
        text = f"Old regime tax {old.total_tax} is lower than new regime tax {new.total_tax}."
    elif new.total_tax < old.total_tax:
        rec, saving = "new", old.total_tax - new.total_tax
        text = f"New regime tax {new.total_tax} is lower than old regime tax {old.total_tax}."
    else:
        rec, saving = "new", 0
        text = f"Both regimes give {new.total_tax}; the default (new) regime is chosen."
    return rec, saving, (TraceLine("regime_choice", saving, CLAUSE, text),)
