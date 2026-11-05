"""core/rules_loader.py

WHAT:  Loads the law parameters for a financial year from rules_data/*.yaml and
       checks that every block of law carries a source and a clause.

WHY:   The hand-coded engine (impl a) reads its numbers from here, so a law
       change is a data edit. Failing loudly on a missing citation stops
       uncited numbers from slipping in (Task 4: every rupee traces to a clause).

HOW:   FY 2024-25 is the base file. A later year is the base plus an overlay file
       that contains ONLY the changed parameters (deep-merged; lists are
       replaced whole, so a new slab table fully replaces the old one).
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from core.errors import RuleDataError, UnsupportedYearError

RULES_DIR = Path(__file__).resolve().parent.parent / "rules_data"
BASE_FY = "2024-25"
BASE_FILE = "fy2024_25.yaml"


def _overlay_file(fy: str) -> str:
    return f"fy{fy.replace('-', '_')}.yaml"  # "2025-26" -> "fy2025_26.yaml"


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Return base with overlay applied. Dicts merge key by key; anything else replaces."""
    out = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def _check_citations(node: Any, path: str = "") -> None:
    """Every dict that has `source` or `clause` must have both, and non-empty."""
    if isinstance(node, dict):
        if "source" in node or "clause" in node:
            if not node.get("source") or not node.get("clause"):
                raise RuleDataError(f"Missing source/clause at '{path}'")
        for key, value in node.items():
            _check_citations(value, f"{path}/{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            _check_citations(value, f"{path}[{i}]")


def _read(name: str) -> dict[str, Any]:
    path = RULES_DIR / name
    if not path.exists():
        raise UnsupportedYearError(f"Missing rules file: {name}")
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_rules(fy: str) -> dict[str, Any]:
    """Return the full, merged, citation-checked rules for `fy` (e.g. "2024-25")."""
    rules = _read(BASE_FILE)
    if fy != BASE_FY:
        overlay_path = RULES_DIR / _overlay_file(fy)
        if not overlay_path.exists():
            raise UnsupportedYearError(f"No rules file for FY {fy}")
        rules = _deep_merge(rules, _read(_overlay_file(fy)))
    _check_citations(rules)
    return rules
