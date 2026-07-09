"""Unit tests for the Policy Server's deterministic layers
(app/guardrails/policy.py).

The semantic layer calls an LLM, so it is stubbed here; these tests cover the
structural guarantees the policy server makes on its own: the SIMULATION label,
the length cap, and how a semantic VIOLATION is reframed across the scammer and
report outputs.
"""

import pytest

import app.guardrails.policy as policy
from app.schemas import EscalationStage, ReportOutput, VerdictInfo


@pytest.fixture
def semantic_ok(monkeypatch):
    """Force the semantic layer to allow everything."""
    monkeypatch.setattr(policy, "validate_text_semantic", lambda *a, **k: True)


@pytest.fixture
def semantic_block(monkeypatch):
    """Force the semantic layer to block everything."""
    monkeypatch.setattr(policy, "validate_text_semantic", lambda *a, **k: False)


def _report():
    return ReportOutput(
        verdict=VerdictInfo(is_scam=True, confidence=0.9, category="phishing"),
        warning="This looks like a bank-impersonation scam.",
        how_to_protect=["Never share your OTP.", "Call the bank directly."],
        kb_stat="tactics catalogued: 5",
        escalation_forecast=[
            EscalationStage(
                stage=1,
                what_to_expect="They will ask you to move to WhatsApp.",
                red_flag="Request to leave the official channel.",
            )
        ],
    )


# --- validate_scammer_output: structural layer -----------------------------


def test_scammer_output_empty_is_labelled(semantic_ok):
    assert policy.validate_scammer_output("") == "SIMULATION: [Empty]"


def test_scammer_output_gets_simulation_prefix(semantic_ok):
    out = policy.validate_scammer_output("They pose as your bank.")
    assert out.startswith("SIMULATION:")


def test_scammer_output_keeps_existing_prefix(semantic_ok):
    text = "SIMULATION: They pose as your bank."
    assert policy.validate_scammer_output(text) == text


def test_scammer_output_is_length_capped(semantic_ok):
    out = policy.validate_scammer_output("A" * 700)
    assert len(out) == 600
    assert out.startswith("SIMULATION:")
    assert out.endswith("...")


def test_scammer_output_blocked_when_semantic_violates(semantic_block):
    out = policy.validate_scammer_output("Enter your PIN at this link now.")
    assert "Refused" in out
    assert out.startswith("SIMULATION:")


# --- validate_report_output ------------------------------------------------


def test_report_unchanged_when_semantic_ok(semantic_ok):
    report = policy.validate_report_output(_report())
    assert report.warning == "This looks like a bank-impersonation scam."
    assert report.how_to_protect == ["Never share your OTP.", "Call the bank directly."]
    assert report.escalation_forecast[0].what_to_expect == (
        "They will ask you to move to WhatsApp."
    )


def test_report_reframed_when_semantic_blocks(semantic_block):
    report = policy.validate_report_output(_report())
    assert "BLOCKED" in report.warning
    assert all("Blocked step" in step for step in report.how_to_protect)
    assert "BLOCKED" in report.escalation_forecast[0].what_to_expect
    assert "BLOCKED" in report.escalation_forecast[0].red_flag
    # Non-text fields are preserved through the reframing.
    assert report.escalation_forecast[0].stage == 1
