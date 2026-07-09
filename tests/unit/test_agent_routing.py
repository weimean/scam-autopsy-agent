"""Unit tests for the graph's routing gate (app/agent.py::check_scam).

check_scam is the conditional edge that decides whether a message enters the
adversarial loop or skips straight to the report. It is pure and deterministic,
and it also stashes a JSON-serializable copy of the classifier output in state
for downstream nodes, so both the route and the state write are worth pinning.
"""

from app.agent import check_scam
from app.schemas import ClassifierOutput


def _event(is_scam: bool, confidence: float):
    return check_scam(
        ClassifierOutput(
            is_scam=is_scam,
            confidence=confidence,
            category="phishing",
            masked_text="verify at [[URL]]",
        )
    )


def test_high_confidence_scam_routes_to_scam():
    assert _event(True, 0.8).actions.route == "scam"


def test_threshold_is_inclusive_at_half():
    # confidence >= 0.5 is the documented gate.
    assert _event(True, 0.5).actions.route == "scam"


def test_just_below_threshold_routes_to_no_scam():
    assert _event(True, 0.49).actions.route == "no_scam"


def test_not_scam_routes_to_no_scam_even_if_confident():
    assert _event(False, 0.99).actions.route == "no_scam"


def test_classifier_output_is_stashed_as_plain_dict():
    ev = _event(True, 0.8)
    stored = ev.actions.state_delta["classifier_output"]
    # Must be JSON-serializable state, not the Pydantic object itself.
    assert isinstance(stored, dict)
    assert stored["is_scam"] is True
    assert stored["category"] == "phishing"


def test_output_is_passed_through_on_both_branches():
    assert _event(True, 0.8).output.category == "phishing"
    assert _event(False, 0.1).output.category == "phishing"
