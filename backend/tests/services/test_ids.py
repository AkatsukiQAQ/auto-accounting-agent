from __future__ import annotations

import re

from backend.services.ids import new_transaction_id


def test_new_transaction_id_has_prefix_and_base62_body() -> None:
    tid = new_transaction_id()
    assert tid.startswith("txn_")
    body = tid.removeprefix("txn_")
    assert re.fullmatch(r"[0-9A-Za-z]+", body), body
    assert 10 < len(body) < 30  # uuid4 in base62 → ~22 chars


def test_new_transaction_id_is_unique() -> None:
    ids = {new_transaction_id() for _ in range(200)}
    assert len(ids) == 200
