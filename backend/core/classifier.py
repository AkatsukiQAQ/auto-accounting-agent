from __future__ import annotations

import re
import unicodedata
from typing import List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from backend.core.schemas import Category, ReceiptClassification, Subcategory


class ClassifyBuckets(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    matched: List[ReceiptClassification] = Field(
        default_factory=list,
        description="Receipts fully classified by regex (with subcategory when applicable).",
    )
    needs_subcategory_llm: List[Tuple[int, str, Category]] = Field(
        default_factory=list,
        description="Receipts that hit a top category but no subcategory — LLM must resolve the subcategory.",
    )
    needs_top_category_llm: List[Tuple[int, str]] = Field(
        default_factory=list,
        description="Receipts that matched no top-level category — LLM must pick one from the full list.",
    )


def _compile_regex_pattern(keywords: List[str]) -> Optional[re.Pattern]:
    """Compile a list of keywords into a single regex with word boundaries for Latin tokens."""
    if not keywords:
        return None
    parts: List[str] = []
    for kw in keywords:
        kw = unicodedata.normalize("NFKC", kw)
        kw = re.escape(kw)
        kw = kw.replace(r"\ ", r"\s+")
        if re.fullmatch(r"[A-Za-z\s\+\'\-]+", kw):
            parts.append(rf"\b{kw}\b")
        else:
            parts.append(kw)
    pattern_str = "|".join(parts)
    return re.compile(pattern_str, re.IGNORECASE)


def regex_match_keyword(
    text: str, pattern: Optional[re.Pattern]
) -> Tuple[bool, Optional[str]]:
    """Apply a compiled keyword regex to text. Returns (matched, first_hit_keyword_or_None)."""
    if pattern is None:
        return False, None
    m = pattern.search(text)
    if m:
        return True, m.group(0)
    return False, None


def regex_classify_one(
    merchant: str, categories: List[Category] | List[Subcategory]
) -> Tuple[Optional[Category | Subcategory], Optional[str]]:
    """Find the first category whose compiled regex matches the merchant string.

    Returns (category, keyword) on hit, or (None, None) on miss. Pure function —
    no LLM, no side effects. Accepts either top-level Category objects or
    Subcategory objects so the two-stage flow can reuse it.
    """
    for cat in categories:
        matched, keyword = regex_match_keyword(merchant, cat.regex)
        if matched:
            return cat, keyword
    return None, None


def regex_classify_batch(
    idx_merchants: List[Tuple[int, str]], categories: List[Category]
) -> ClassifyBuckets:
    """Split a batch of (idx, merchant) rows into three buckets based on regex hits.

    - Fully matched (top category, and subcategory if applicable) → ClassifyBuckets.matched
    - Matched top category but subcategories exist and none hit → needs_subcategory_llm
    - Matched no top category → needs_top_category_llm

    Phase 1's service layer feeds the two *_llm buckets to the LLM classifier.
    """
    buckets = ClassifyBuckets()

    for idx, merchant in idx_merchants:
        top_cat, top_keyword = regex_classify_one(merchant, categories)
        if top_cat is None:
            buckets.needs_top_category_llm.append((idx, merchant))
            continue

        # top_cat is a Category here; try to resolve a subcategory when declared.
        assert isinstance(top_cat, Category)
        if top_cat.sub_categories:
            sub_cat, sub_keyword = regex_classify_one(merchant, top_cat.sub_categories)
            if sub_cat is not None:
                assert isinstance(sub_cat, Subcategory)
                buckets.matched.append(
                    ReceiptClassification(
                        idx=idx,
                        category=top_cat.name,
                        sub_category=sub_cat.name,
                        matched=True,
                        keyword=sub_keyword,
                    )
                )
            else:
                # Top matched but no subcategory hit — LLM must resolve the leaf.
                buckets.needs_subcategory_llm.append((idx, top_keyword or merchant, top_cat))
        else:
            buckets.matched.append(
                ReceiptClassification(
                    idx=idx,
                    category=top_cat.name,
                    sub_category=None,
                    matched=True,
                    keyword=top_keyword,
                )
            )

    return buckets
