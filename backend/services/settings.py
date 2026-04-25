"""User-settings service.

Single-row table (`user_settings.id = 1`). First read auto-creates the row
with the default payload; subsequent PATCHes deep-merge. Explicit `None` in
a leaf clears that leaf (writes null). Missing keys preserve the old value.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from sqlalchemy.orm import Session

from backend.db.models import UserSettings

_SINGLETON_ID = 1

DEFAULT_SETTINGS: dict[str, Any] = {
    "profile": {
        "fullName": "",
        "preferredName": "",
        "email": "",
        "timezone": "Asia/Tokyo",
        "defaultCurrency": "JPY",
    },
    "appearance": {
        "theme": "light",
    },
    "apiKeys": {},
}


def get_settings(session: Session) -> dict[str, Any]:
    row = session.get(UserSettings, _SINGLETON_ID)
    if row is None:
        row = UserSettings(id=_SINGLETON_ID, data=deepcopy(DEFAULT_SETTINGS))
        session.add(row)
        session.flush()
    return deepcopy(row.data)


def update_settings(session: Session, patch: dict[str, Any]) -> dict[str, Any]:
    current = get_settings(session)
    merged = _deep_merge(current, patch)

    row = session.get(UserSettings, _SINGLETON_ID)
    assert row is not None, "get_settings must have created the singleton"
    row.data = merged
    session.flush()
    return deepcopy(merged)


def _deep_merge(base: Any, override: Any) -> Any:
    """Recursive dict merge. Non-dict values (including `None`) replace wholesale.

    Rules match PHASE_1.md §Settings:
    - Missing key in `override` → keep `base` value.
    - Key present with dict value → recurse.
    - Key present with any non-dict value (including `None`) → replace `base`.
    """
    if isinstance(base, dict) and isinstance(override, dict):
        out = dict(base)
        for k, v in override.items():
            if k in out:
                out[k] = _deep_merge(out[k], v)
            else:
                out[k] = deepcopy(v)
        return out
    return deepcopy(override)
