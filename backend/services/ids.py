"""ID minting helpers.

Transaction IDs: `txn_` + base62(uuid4). Short, URL-safe, roughly 22 chars.
"""
from __future__ import annotations

import uuid

_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def _base62(n: int) -> str:
    if n == 0:
        return "0"
    out: list[str] = []
    while n:
        n, rem = divmod(n, 62)
        out.append(_ALPHABET[rem])
    return "".join(reversed(out))


def new_transaction_id() -> str:
    """Return a fresh `txn_...` identifier derived from a random UUID4."""
    return "txn_" + _base62(uuid.uuid4().int)
