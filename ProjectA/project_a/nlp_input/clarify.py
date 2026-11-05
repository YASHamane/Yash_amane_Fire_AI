"""nlp_input/clarify.py

WHAT:  Determines what clarifying questions to ask when input is missing, ambiguous, or contradictory.
WHY:   The system must "ask, don't guess". It never fabricates mandatory parameters.
HOW:   Takes error or missing field diagnostics and generates natural, polite clarifying prompts.
"""
from __future__ import annotations

from core.errors import AmbiguousInputError, ContradictionError, MissingFieldError, TaxEngineError

CLARIFICATION_TEMPLATES = {
    "gross_salary": "Could you please specify your annual gross salary (e.g., in Lakhs or Rupees)?",
    "age_band": "What is your age, or which age category do you fall into (below 60, senior 60-79, or super-senior 80+)?",
    "basic_salary": "To calculate your HRA tax exemption, what is your annual basic salary (plus DA)?",
    "rent_paid_annual": "What is the total annual rent you paid for accommodation?",
}


def build_clarification_question(error: TaxEngineError) -> str:
    """Returns a user-facing clarifying question based on the validation error."""
    if isinstance(error, MissingFieldError):
        questions = [CLARIFICATION_TEMPLATES.get(f, f"Please provide your {f}.") for f in error.fields]
        return " ".join(questions)

    if isinstance(error, ContradictionError):
        return f"There seems to be a contradiction in your details: {error.reason} Could you clarify?"

    if isinstance(error, AmbiguousInputError):
        return f"We could not clearly determine '{error.field}': {error.reason} Please provide more details."

    return "Could you please clarify your financial details so we can compute your tax accurately?"
