"""Unit tests for the Pydantic contracts (app/schemas.py).

These schemas are the typed boundaries between nodes. The tests pin the
required fields and the defaults the rest of the graph relies on.
"""

import pytest
from pydantic import ValidationError

from app.schemas import ClassifierOutput, ReportOutput, VerdictInfo


def test_classifier_output_defaults():
    out = ClassifierOutput(
        is_scam=True,
        confidence=0.87,
        category="phishing",
        masked_text="Verify at [[URL]]",
    )
    assert out.red_flag_hints == []
    assert out.detected_language == "en"


def test_classifier_output_requires_masked_text():
    with pytest.raises(ValidationError):
        ClassifierOutput(is_scam=True, confidence=0.5, category="phishing")


def test_confidence_accepts_int_and_coerces_to_float():
    out = ClassifierOutput(
        is_scam=False, confidence=1, category="unknown", masked_text="hi"
    )
    assert isinstance(out.confidence, float)
    assert out.confidence == 1.0


def test_report_output_defaults():
    report = ReportOutput(
        verdict=VerdictInfo(is_scam=True, confidence=0.9, category="phishing"),
        warning="Looks like a scam.",
        kb_stat="tactics catalogued: 3",
    )
    assert report.tactics == []
    assert report.how_to_protect == []
    assert report.reporting_links == []
    assert report.escalation_forecast == []
    assert report.language == "en"
    assert report.disclaimer == "educational, not legal/financial advice"


def test_report_output_requires_verdict():
    with pytest.raises(ValidationError):
        ReportOutput(warning="x", kb_stat="tactics catalogued: 0")
