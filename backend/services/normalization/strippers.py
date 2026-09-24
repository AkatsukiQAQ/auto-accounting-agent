"""Location / store-suffix strippers — pure regex, no DB access.

Deliberately importable from Alembic migrations (0005 backfills historical
rows with exactly these rules; at migration time the alias/brand tables are
empty, so strip+fallback IS the full engine).
"""
from __future__ import annotations

import re

# Applied in order, repeatedly, until the name stops changing (a receipt can
# stack suffixes: "STARBUCKS #3341 (Shibuya)"). Order mirrors PHASE_2.md.
_SUFFIX_RULES: tuple[re.Pattern[str], ...] = (
    # CJK parenthesized location: "（南京西路店）", "(渋谷号)"
    re.compile(r"\s*[（(][^（()）]*[店号铺馆厅][)）]\s*$"),
    # CJK branch suffixes: "徐家汇店", "渋谷分店"
    re.compile(r"\s*\S+?分店\s*$"),
    re.compile(r"\s*\S+?店\s*$"),
    # Store numbers: "#3341", "No. 12"
    re.compile(r"\s*#?\d{2,}\s*$"),
    re.compile(r"\s*No\.?\s*\d+\s*$", re.IGNORECASE),
    # "- Shibuya branch" style tags
    re.compile(r"\s*[-–—]\s*.+?\s*(branch|store|outlet|location)\s*$", re.IGNORECASE),
)

# Generic trailing parens — most aggressive, so it runs last and is skipped
# when the remainder would drop under 3 characters (PHASE_2.md guard).
_GENERIC_PARENS = re.compile(r"\s*[（(].+?[)）]\s*$")

_MAX_PASSES = 5


def strip_location(name: str) -> str:
    """Strip store/location suffixes; never strips a name to (near-)nothing."""
    current = name.strip()
    for _ in range(_MAX_PASSES):
        previous = current
        for rule in _SUFFIX_RULES:
            candidate = rule.sub("", current).strip()
            if candidate and candidate != current:
                current = candidate
        candidate = _GENERIC_PARENS.sub("", current).strip()
        if len(candidate) >= 3 and candidate != current:
            current = candidate
        if current == previous:
            break
    return current or name.strip()


def title_case_if_shouty(name: str) -> str:
    """'STARBUCKS' → 'Starbucks'; mixed-case and CJK names pass through."""
    if name.isupper() and any(c.isalpha() for c in name):
        return name.title()
    return name
