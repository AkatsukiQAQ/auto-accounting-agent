import pytest

import backend.core.schemas as schemas_mod
from backend.core.schemas import (
    Category,
    ClassificationResult,
    OCR_Receipt,
    OCR_Results,
    ParsedOcrResult,
    ParsedReceipt,
    ReceiptClassification,
    Subcategory,
)


def test_subcategory_constructs_with_parent_name():
    sc = Subcategory(name="Taxi", parent_name="Transportation", keywords=["タクシー"])
    assert sc.name == "Taxi"
    assert sc.parent_name == "Transportation"
    assert sc.regex is None


def test_category_populates_sub_categories_via_snake_case_kwarg():
    # Regression for legacy bug #1: legacy used `subCategories=` which Pydantic v2
    # silently ignored, leaving sub_categories as None. Ensure the correct name works.
    subs = [Subcategory(name="Train", parent_name="Transportation", keywords=["駅"])]
    cat = Category(name="Transportation", keywords=["駅"], sub_categories=subs)
    assert cat.sub_categories is not None
    assert len(cat.sub_categories) == 1
    assert cat.sub_categories[0].name == "Train"


def test_category_sub_categories_defaults_to_none():
    cat = Category(name="Shopping", keywords=[])
    assert cat.sub_categories is None


def test_classification_result_accepts_plural_field_name():
    # Regression for legacy bug #3: legacy called `classification_result=` (singular)
    # which Pydantic silently dropped, leaving the required field unset.
    rc = ReceiptClassification(idx=0, category="Game", sub_category=None, matched=True, keyword="Steam")
    result = ClassificationResult(classification_results=[rc])
    assert len(result.classification_results) == 1
    assert result.classification_results[0].category == "Game"


def test_classification_result_rejects_singular_field_name():
    # Missing the required plural field must raise a ValidationError.
    with pytest.raises(Exception):  # pydantic.ValidationError is fine to catch broadly here
        ClassificationResult(classification_result=[])  # type: ignore[call-arg]


def test_legacy_names_are_gone():
    # subCategory / ReceiptCategory were renamed. Confirm the old symbols are not re-exported.
    assert not hasattr(schemas_mod, "subCategory")
    assert not hasattr(schemas_mod, "ReceiptCategory")


def test_parsed_receipt_optional_fields_default_none():
    pr = ParsedReceipt(raw_text="raw")
    assert pr.currency is None
    assert pr.amount is None
    assert pr.date is None
    assert pr.time is None
    assert pr.merchant is None


def test_ocr_results_wraps_list_of_receipts():
    results = OCR_Results(ocr_results=[OCR_Receipt(raw_text="line a"), OCR_Receipt(raw_text="line b")])
    assert len(results.ocr_results) == 2


def test_parsed_ocr_result_wraps_list():
    por = ParsedOcrResult(parsed_ocr_results=[ParsedReceipt(raw_text="t")])
    assert len(por.parsed_ocr_results) == 1
