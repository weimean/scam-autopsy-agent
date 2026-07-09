"""Unit tests for model routing (app/tools/model_routing.py).

get_model_id maps a logical role to a concrete model id, switching between
Vertex AI and AI Studio based on GOOGLE_GENAI_USE_VERTEXAI. The judge staying
on a different model from the agents is what preserves judge independence, so
that mapping is worth pinning.
"""

import pytest

from app.tools.model_routing import get_model_id


@pytest.fixture
def vertex_on(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "True")


@pytest.fixture
def vertex_off(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "False")


def test_vertex_pro_role(vertex_on):
    assert get_model_id("pro") == "gemini-3.1-pro-preview"


def test_vertex_judge_is_distinct_from_pro(vertex_on):
    # Judge independence: the judge must not be the same model as the pro agent.
    assert get_model_id("judge") == "gemini-2.5-pro"
    assert get_model_id("judge") != get_model_id("pro")


def test_vertex_flash_lite_role(vertex_on):
    assert get_model_id("flash-lite") == "gemini-3.1-flash-lite"


def test_vertex_unknown_role_falls_back(vertex_on):
    assert get_model_id("something-else") == "gemini-3.1-flash-lite"


def test_ai_studio_collapses_all_roles(vertex_off):
    # On the AI Studio free tier every role maps to one model to survive quota.
    for role in ("pro", "judge", "flash-lite", "unknown"):
        assert get_model_id(role) == "gemini-3.1-flash-lite"


def test_defaults_to_vertex_when_unset(monkeypatch):
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    # Default is the Vertex path, so pro resolves to the Vertex pro id.
    assert get_model_id("pro") == "gemini-3.1-pro-preview"
