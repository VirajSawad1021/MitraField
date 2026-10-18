"""Turn exceptions into messages a person can act on."""
from .costs import BudgetExceeded


def friendly_error(e):
    s = str(e)
    if isinstance(e, BudgetExceeded):
        return s
    if "spending cap" in s or "spend cap" in s:
        return "The Gemini API key has reached its monthly spending cap. Raise it at ai.studio/spend, then try again."
    if "429" in s or "RESOURCE_EXHAUSTED" in s:
        return "Gemini is rate-limiting this project right now. Wait a minute and try again."
    return s[:400]
