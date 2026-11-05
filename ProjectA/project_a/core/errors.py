"""core/errors.py

WHAT:  The small set of exceptions used across Project A.

WHY:   "Ask, don't guess" is a core requirement of Task 3. Using distinct,
       named exceptions lets the parser say exactly WHY it cannot compute a
       number (missing field vs. contradiction) and lets the benchmarks tell
       a deliberate refusal apart from a crash.

HOW:   nlp_input/validate.py and nlp_input/clarify.py raise these. The
       calculators raise RuleDataError / LLMOutputError when something is
       wrong, so failures are never silent.
"""
from __future__ import annotations


class TaxEngineError(Exception):
    """Base class: catch this to catch every Project A error."""


class MissingFieldError(TaxEngineError):
    """A REQUIRED field was not provided (e.g. gross salary).

    `fields` lists the missing names so clarify.py can build a question.
    """

    def __init__(self, fields: list[str]) -> None:
        self.fields = fields
        super().__init__(f"Missing required field(s): {', '.join(fields)}")


class AmbiguousInputError(TaxEngineError):
    """The user's text can be read more than one way (e.g. '12' with no unit)."""

    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"Ambiguous value for '{field}': {reason}")


class ContradictionError(TaxEngineError):
    """Two statements cannot both be true (e.g. 'no rent' but 'claiming HRA')."""

    def __init__(self, fields: list[str], reason: str) -> None:
        self.fields = fields
        self.reason = reason
        super().__init__(f"Contradiction between {fields}: {reason}")


class RuleDataError(TaxEngineError):
    """The rules data file is missing a parameter or has no citation for one."""


class UnsupportedYearError(TaxEngineError):
    """No rules are available for the requested financial year."""


class LLMOutputError(TaxEngineError):
    """An LLM returned something that is not valid JSON / fails the schema.

    Raised (not swallowed) so benchmarks can count it as a loud failure,
    as opposed to a SILENT wrong answer, which is the dangerous kind.
    """
