from __future__ import annotations

from sqlalchemy.orm import Session

from backend.services.settings import DEFAULT_SETTINGS, get_settings, update_settings


def test_first_get_creates_row_with_defaults(session: Session) -> None:
    s = get_settings(session)
    assert s["profile"]["timezone"] == DEFAULT_SETTINGS["profile"]["timezone"]
    assert s["appearance"]["theme"] == "light"
    assert s["apiKeys"] == {}


def test_second_get_returns_same_persisted_value(session: Session) -> None:
    first = get_settings(session)
    first["profile"]["email"] = "mutation-on-copy-should-not-persist@example.com"
    second = get_settings(session)
    assert second["profile"]["email"] == DEFAULT_SETTINGS["profile"]["email"]


def test_update_deep_merges_nested_profile(session: Session) -> None:
    out = update_settings(session, {"profile": {"email": "a@b.com"}})
    assert out["profile"]["email"] == "a@b.com"
    # Untouched sibling keys survive.
    assert out["profile"]["timezone"] == DEFAULT_SETTINGS["profile"]["timezone"]


def test_update_explicit_null_clears_leaf(session: Session) -> None:
    update_settings(session, {"profile": {"email": "x@y.com"}})
    out = update_settings(session, {"profile": {"email": None}})
    assert out["profile"]["email"] is None


def test_update_adds_new_top_level_key(session: Session) -> None:
    out = update_settings(session, {"experimental": {"flag": True}})
    assert out["experimental"] == {"flag": True}
    # Existing keys preserved.
    assert "profile" in out


def test_update_primitive_replaces_primitive(session: Session) -> None:
    out = update_settings(session, {"appearance": {"theme": "dark"}})
    assert out["appearance"]["theme"] == "dark"


def test_update_api_keys_merges_per_provider(session: Session) -> None:
    update_settings(session, {"apiKeys": {"openai": "sk-1"}})
    out = update_settings(session, {"apiKeys": {"anthropic": "sk-2"}})
    assert out["apiKeys"] == {"openai": "sk-1", "anthropic": "sk-2"}
