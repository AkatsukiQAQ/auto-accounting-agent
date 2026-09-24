"""ID minting helpers.

Entity IDs: `<prefix>_` + base62(uuid4). Short, URL-safe, roughly 22 chars.
Merchants are the deliberate exception — their IDs are human slugs
("starbucks"), minted by the normalization service, not here.
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


def _mint(prefix: str) -> str:
    return prefix + "_" + _base62(uuid.uuid4().int)


def new_transaction_id() -> str:
    """Return a fresh `txn_...` identifier derived from a random UUID4."""
    return _mint("txn")


def new_account_id() -> str:
    return _mint("acc")


def new_budget_id() -> str:
    return _mint("bgt")


def new_merchant_alias_id() -> str:
    return _mint("mal")


def new_recurring_rule_id() -> str:
    return _mint("rr")


def new_review_item_id() -> str:
    return _mint("rvw")


def new_transfer_group_id() -> str:
    return _mint("xfr")
