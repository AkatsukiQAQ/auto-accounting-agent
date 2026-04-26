from __future__ import annotations

import re
import unicodedata
from typing import List, Optional

CURRENCY_TABLE = {
    "¥": "¥",  # Ambiguous between CNY and JPY without context
    "CNY": "CNY", "元": "CNY", "RMB": "CNY", "块": "CNY", "￥": "CNY", "人民币": "CNY",
    "HKD": "HKD", "HK$": "HKD",
    "JPY": "JPY", "円": "JPY", "YEN": "JPY", "〒": "JPY",
    "USD": "USD", "$": "USD", "US$": "USD",
    "EUR": "EUR", "€": "EUR", "euro": "EUR",
    "GBP": "GBP", "£": "GBP", "pound": "GBP",
    "KRW": "KRW", "₩": "KRW",
}

# First-hit-wins: the ¥ entry is intentionally first because bare ¥ is the most
# ambiguous symbol and must fall through to the CNY/JPY disambiguation logic in
# detect_currency. Do not reorder without updating the disambiguation paths.
CURRENCY_HINTS: List[str] = [
    r"¥",
    r"CNY|元|RMB|块|￥|人民币",
    r"HKD|HK\$",
    r"JPY|円|YEN|〒",
    r"USD|US\$|\$",
    r"EUR|€|euro",
    r"GBP|£|pound",
    r"KRW|₩",
]


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t​　]+", " ", text)
    return text.strip()


def split_lines(text: str) -> List[str]:
    return [line.strip() for line in text.split("\n") if line.strip()]


def detect_currency(
    text: str, symbol_defaults: Optional[dict[str, str]] = None
) -> Optional[str]:
    """Detect an ISO currency code in free text.

    First-hit-wins over ``CURRENCY_HINTS``. If a bare ambiguous symbol (``$`` or
    ``¥``) is found, consult ``symbol_defaults`` first, then fall back to
    context-based disambiguation (looking for ``US``/``USD`` for ``$`` and
    ``CNY``/``元``/``人民币``/``JPY``/``円``/``YEN`` for ``¥``). Returns ``None``
    when no hint matches, or when an ambiguous symbol cannot be disambiguated.

    ``symbol_defaults`` is injected at call time rather than being read from a
    module-level config — the service layer owns YAML loading.
    """
    symbol_defaults = symbol_defaults or {}

    for pat in CURRENCY_HINTS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if not m:
            continue
        token = m.group(0)

        # Exact table hit (case-insensitive)
        for k, iso in CURRENCY_TABLE.items():
            if k.lower() == token.lower():
                matched_key = k
                matched_iso = iso
                break
        else:
            matched_key = None
            matched_iso = None

        # Disambiguate bare '$'
        if token == "$":
            if symbol_defaults.get("$"):
                return symbol_defaults["$"]
            if "US" in text or "USD" in text.upper():
                return "USD"
            return None

        # Disambiguate bare '¥' (the table entry maps it to itself)
        if token == "¥":
            if symbol_defaults.get("¥"):
                return symbol_defaults["¥"]
            if "CNY" in text.upper() or "元" in text or "人民币" in text:
                return "CNY"
            if "JPY" in text.upper() or "円" in text or "YEN" in text:
                return "JPY"
            return None

        if matched_iso is not None:
            return matched_iso

        return CURRENCY_TABLE.get(token, None)

    return None
