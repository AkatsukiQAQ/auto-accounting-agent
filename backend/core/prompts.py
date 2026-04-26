from __future__ import annotations

from typing import List, Tuple

from backend.core.currency import normalize_text
from backend.core.schemas import Category, OCR_Receipt


def render_ocr_prompt() -> str:
    """Return the static prompt string fed alongside the image to the OCR model."""
    return (
        "Extract receipt information from a screenshot and return it as JSON "
        "(strictly matching fields). Rules:\n"
        "1) First, transcribe full raw_text verbatim (preserving line breaks).\n"
        "2) Then, Divide the full raw_text into each receipts.\n"
        "3) Don't make it up.\n"
    )


def render_parser_prompt(
    ocr_receipts: List[OCR_Receipt], accepted_currencies: List[str]
) -> str:
    """Render the prompt that asks the LLM to extract structured fields from OCR text.

    Matches the legacy ``model_ocr_result_parser`` exactly: each receipt's
    ``raw_text`` is normalized (NFKC, CRLF→LF, whitespace collapse) before
    being pasted into the prompt. ``accepted_currencies`` is joined into the
    rule list so the LLM drops receipts in other currencies.
    """
    text = (
        "Extract receipt information from the OCR result and return it as JSON "
        "(strictly matching fields). Rules:\n"
        "1) Extract information for each receipt in the OCR result. You should "
        "process each receipt separately.\n"
        "2) For each receipt, detect the currency type and amount. If you can't "
        "find it, return null.\n"
        "3) For each receipt, detect the date in YYYY-MM-DD format. If you can't "
        "find it, return null. Do not report time here.\n"
        "4) For each receipt, detect the time in HH:MM format. If you can't find "
        "it, return null. Do not report date here.\n"
        "5) For each receipt, detect the merchant name. Do not translate it. You "
        "should report it in the origin language. If you can't find it, return null.\n"
        "6) We only accept the following currency types: "
        + ", ".join(accepted_currencies)
        + ". If you detect other currency types, ignore that receipt and do not "
        "reply anything.\n"
        "7) Do not report points, taxes, or any other information.\n"
        "8) Do not make it up.\n"
        "\n"
        "Here is the OCR result:\n"
    )

    for i, receipt in enumerate(ocr_receipts):
        normalized = normalize_text(receipt.raw_text)
        text += f"Receipt {i + 1}:\n{normalized}\n\n"

    return text


def render_classify_prompt(
    categories: List[Category], pending: List[Tuple[int, str]]
) -> str:
    """Render the prompt that asks the LLM to pick a top-level category per merchant."""
    cat_lines: List[str] = []
    for cat in categories:
        if cat.sub_categories:
            sub_names = ", ".join(s.name for s in cat.sub_categories)
            cat_lines.append(f"{cat.name}: {sub_names}")
        else:
            cat_lines.append(f"{cat.name}: No sub_category")
    cat_texts = "\n".join(cat_lines) + "\n"

    pending_lines = [f"Receipt {idx}: {merchant}" for idx, merchant in pending]
    pending_texts = "\n".join(pending_lines) + "\n" if pending_lines else ""

    return (
        "Classify the receipts into pre-defined category. The rules are provided as below:\n"
        "1. The categories are defined in format <category>: <sub_category_1>, ..., "
        "<sub_category_n>. Categories with no sub_categories are defined as "
        "<category>: No sub_category.\n"
        "2. The receipts are defined in format Receipt <idx>: <merchant_name>. You "
        "should classify them based on the merchant_name and also return the idx. Be "
        "aware that the idx of the receipt may not be continues or in ascending order.\n"
        "3. You should process each receipt separately and return the result one by one.\n"
        "4. You should return idx, category, sub_category, matched and keyword for each "
        "receipt. Notice that the idx here is the pre-set idx, not the order of receipts "
        "in the list.\n"
        "5. If a receipt only matched the category and didn't matched any sub_category, "
        "return the matched category and keep sub_category as None.\n"
        "6. If a receipt didn't matched any category, return the category as others and "
        "keep sub_category as None.\n"
        "7. If a receipt matched a category or sub_category, set matched to True. "
        "Otherwise, it should be False.\n"
        "8. If a receipt matched a category or sub_category, return the keyword string "
        "that can be the evidence for classification.\n"
        "\n"
        "The pre-defined categories are provided as below:"
        f"{cat_texts}\n"
        "\n"
        "Here are the receipts:\n"
        f"{pending_texts}"
    )


def render_subclassify_prompt(
    sub_cat_pending: List[Tuple[int, str, Category]]
) -> str:
    """Render the prompt that asks the LLM to pick a subcategory given a known top category."""
    blocks: List[str] = []
    for idx, keyword, cat in sub_cat_pending:
        sub_names = (
            ", ".join(s.name for s in cat.sub_categories) if cat.sub_categories else ""
        )
        blocks.append(
            f"Receipt {idx}\n"
            f"Keyword: {keyword}\n"
            f"Main category is {cat.name}\n"
            f"Pre-defined sub_categories are {sub_names}"
        )
    texts = "\n\n".join(blocks) + "\n" if blocks else ""

    return (
        "Classify the receipts into pre-defined sub_category. The rules are provided as below:\n"
        "1. The receipt with be provided with idx, keyword, main category name, and a "
        "list of sub_category candidates.\n"
        "2. You should process each receipt separately and return the result one by one.\n"
        "3. You should classify the receipt based on the provided keyword and return "
        "the matched sub_category name.\n"
        "4. You should also return the idx of the receipt. Notice that the idx here is "
        "the pre-set idx, not the order of receipts in the list.\n"
        "5. You should return the main category as it is, and return the matched "
        "sub_category. If the receipt dose not match any sub_category, return None.\n"
        "Here are the receipts:\n"
        f"{texts}"
    )
