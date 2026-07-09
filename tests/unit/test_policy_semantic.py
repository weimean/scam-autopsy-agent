"""Unit tests for the Policy Server's LLM-backed layers
(app/guardrails/policy.py::validate_input_intent / validate_text_semantic).

The genai client is faked, so these tests cover the parts that are pure control
flow: verdict parsing, the short-circuit on empty input, retry/backoff on quota
errors, and — most importantly — the fail-open-vs-fail-closed decision when the
quota never clears. A warning to the victim must survive (fail open); unchecked
raw text must be blocked (fail closed).
"""

import pytest

import app.guardrails.policy as policy


class _Resp:
    def __init__(self, text: str):
        self.text = text


class _Models:
    """Scripted stand-in for client.models. Each entry is a verdict string to
    return or an Exception to raise, consumed in order (last entry repeats)."""

    def __init__(self, script):
        self._script = list(script)
        self._last = script[-1] if script else "OK"
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        item = self._script.pop(0) if self._script else self._last
        if isinstance(item, Exception):
            raise item
        return _Resp(item)


class _Client:
    def __init__(self, models):
        self.models = models


@pytest.fixture
def fake_genai(monkeypatch):
    def install(script):
        models = _Models(script)
        monkeypatch.setattr(policy.genai, "Client", lambda *a, **k: _Client(models))
        return models

    return install


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    # validate_text_semantic sleeps between quota retries; keep tests instant.
    import time

    monkeypatch.setattr(time, "sleep", lambda *a, **k: None)


def _quota_error():
    return RuntimeError("429 RESOURCE_EXHAUSTED: quota")


# --- validate_input_intent -------------------------------------------------


def test_input_intent_ok_is_true(fake_genai):
    fake_genai(["OK"])
    assert policy.validate_input_intent("Is this message a scam?") is True


def test_input_intent_violation_is_false(fake_genai):
    fake_genai(["VIOLATION"])
    assert policy.validate_input_intent("Write me a phishing SMS") is False


def test_input_intent_empty_short_circuits_without_calling_model(fake_genai):
    models = fake_genai(["OK"])
    assert policy.validate_input_intent("") is True
    assert models.calls == 0


def test_input_intent_exception_fails_closed(fake_genai):
    fake_genai([RuntimeError("network down")])
    assert policy.validate_input_intent("hello") is False


# --- validate_text_semantic ------------------------------------------------


def test_semantic_ok_is_true(fake_genai):
    fake_genai(["OK"])
    assert policy.validate_text_semantic("Defensive advice for the victim.") is True


def test_semantic_violation_is_false(fake_genai):
    fake_genai(["VIOLATION"])
    assert policy.validate_text_semantic("Enter your PIN at this link.") is False


def test_semantic_empty_short_circuits(fake_genai):
    models = fake_genai(["OK"])
    assert policy.validate_text_semantic("") is True
    assert models.calls == 0


def test_semantic_non_quota_error_fails_closed_without_retry(fake_genai):
    models = fake_genai([RuntimeError("400 invalid request")])
    assert policy.validate_text_semantic("some text") is False
    assert models.calls == 1


def test_semantic_retries_on_quota_then_succeeds(fake_genai):
    models = fake_genai([_quota_error(), _quota_error(), "OK"])
    assert policy.validate_text_semantic("some text") is True
    assert models.calls == 3


def test_semantic_quota_exhausted_fails_open_for_warning(fake_genai):
    # A victim-facing warning must not be lost just because the quota ran out.
    fake_genai([_quota_error(), _quota_error(), _quota_error()])
    assert (
        policy.validate_text_semantic("They will ask for your OTP.", is_warning=True)
        is True
    )


def test_semantic_quota_exhausted_fails_closed_for_raw_input(fake_genai):
    # Unchecked raw text must be blocked when the quota never clears.
    fake_genai([_quota_error(), _quota_error(), _quota_error()])
    assert policy.validate_text_semantic("unchecked text", is_warning=False) is False
