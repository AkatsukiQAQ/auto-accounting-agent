# Backend Phase 0 — "Extract what's worth keeping"

**Scope:** the legacy `auto-accounting-agent` pipeline works, but it's framework-coupled (LangChain tools, LangGraph agent), framework-instantiated LLMs scattered across three files, and has no storage layer. Before rebuilding in Phase 1, lift the **algorithmic core** out into pure, framework-free Python modules that the new pipeline can import unchanged.

**Estimated effort:** half a day to a day.

**Output:** a new `backend/core/` package, fully unit-tested, with no dependency on `langchain`, `langgraph`, or the filesystem. Phase 1 will wrap these with storage + HTTP + orchestration.

**Read alongside:** [`HANDOFF.md`](./HANDOFF.md). You don't need `PHASE_1.md` yet — this phase is pre-product.

---

## Why this phase exists

The legacy pipeline mixes four concerns in every file:

1. **Business logic** — currency detection rules, category keyword matching, receipt normalization.
2. **LLM calls** — `ChatOpenAI(model="gpt-5-nano").with_structured_output(...)` inline in three different tools.
3. **Framework glue** — `@tool(...)` decorators, `ToolInput` pydantic schemas for LangChain.
4. **I/O** — YAML loading, base64 image encoding, env-var API keys.

For Phase 1 we want (1) preserved, (2) behind an interface, (3) deleted, (4) owned by the service layer. This phase is just (1) → a `core/` package.

If you skip Phase 0 you'll end up rewriting this logic inline in Phase 1's FastAPI routes, then fighting to test it without spinning up the whole app. One afternoon here saves two days later.

---

## What to extract

Work file-by-file against the legacy repo. For each legacy module, extract the listed functions into new-home modules with **no LangChain / LangGraph / `ChatOpenAI` imports**.

### From `backend/tools/ocr_result_parser.py`

#### New home: `backend/core/currency.py`

Extract:

- `CURRENCY_TABLE` (dict of symbol → ISO code)
- `CURRENCY_HINTS` (regex list)
- `Normalizer._normalize_text` → module-level `normalize_text(text: str) -> str`
- `Normalizer._split_lines` → module-level `split_lines(text: str) -> list[str]`
- `CurrencyParser.detect_currency` → `detect_currency(text: str, symbol_defaults: dict[str, str] | None = None) -> Optional[str]`

The new `detect_currency` takes `symbol_defaults` as an argument instead of reading `cfg` at import time. The YAML loading moves to the service layer.

```python
# backend/core/currency.py
from __future__ import annotations
import re, unicodedata
from typing import Optional

CURRENCY_TABLE = { ... }   # lifted verbatim
CURRENCY_HINTS = [ ... ]   # lifted verbatim

def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\u200b\u3000]+", " ", text)
    return text.strip()

def split_lines(text: str) -> list[str]:
    return [line.strip() for line in text.split("\n") if line.strip()]

def detect_currency(text: str, symbol_defaults: dict[str, str] | None = None) -> Optional[str]:
    # Same logic as CurrencyParser.detect_currency, but symbol_defaults is injected.
    ...
```

#### Unit tests: `tests/core/test_currency.py`

Port the `if __name__ == "__main__":` test block at the bottom of the legacy file into real pytest cases. Add cases for:

- `¥` with CJK context (should resolve to CNY or JPY from hints)
- `$` with "USD" / "US" context vs bare `$` with `symbol_defaults={"$": "USD"}`
- No currency token → returns `None`
- Mixed text (e.g. `"Total 500 JPY · Subtotal $4"` → first hit wins)

### From `backend/tools/receipt_classifier.py`

#### New home: `backend/core/classifier.py`

Extract:

- `_compile_regex_pattern(keywords: list[str]) -> Optional[re.Pattern]` — lifted verbatim.
- `regex(text, pattern)` → rename to `regex_match_keyword(text: str, pattern: re.Pattern | None) -> tuple[bool, Optional[str]]` (current name shadows `re` module).
- `Classifier.regex_search_one` → `regex_classify_one(merchant: str, categories: list[Category]) -> tuple[Optional[Category], Optional[str]]` (pure: returns matched category + keyword, or both None).
- `Classifier.regex_search` → `regex_classify_batch(idx_merchants, categories) -> ClassifyBuckets` where `ClassifyBuckets` is a new dataclass with three lists: `matched`, `needs_subcategory_llm`, `needs_top_category_llm`.

The two `model_search_*` methods that call the LLM **do not belong in core**. They move to the service layer in Phase 1 behind a `PipelineLLM` interface. Phase 0's job is only to extract the regex half.

Also extract the dataclasses themselves:

#### New home: `backend/core/schemas.py`

Move `Category`, `subCategory`, `ReceiptCategory`, `ClassificationResult`, `ParsedReceipt`, `ParsedOcrResult`, `OCR_Receipt`, `OCR_Results` here, rewritten as plain Pydantic v2 models (or dataclasses — your call, but Pydantic is already a dep and gives you free JSON serialization).

Rename to consistent casing:

- `subCategory` → `Subcategory`
- `ReceiptCategory` → `ReceiptClassification`
- `ClassificationResult` → `ClassificationResult` (unchanged)
- Others unchanged

Fix the bug in the legacy `Category` model where `sub_categories` in `__init__` is spelled `subCategories` in one place (see `_load_categories` passing `subCategories=...` to `Category(sub_categories=...)` — it silently ends up None).

### From `backend/tools/config_loader.py` + `backend/configs/*.yaml`

#### New home: `backend/core/categories_seed.py` (data) + keep the YAML

Keep `CategoryConfigs.yaml` and `OcrResultParserConfigs.yaml` where they are — they're fine as bundled data. But:

- Rename `load_config(filename)` → `load_yaml_config(filename: str) -> dict`, move to `backend/core/config_loader.py`.
- Add `load_seed_categories() -> list[Category]` in `backend/core/categories_seed.py` that reads `CategoryConfigs.yaml` and returns a list of `Category` objects (built with `_compile_regex_pattern`). This is what Phase 1's DB seeder will call.

### From `backend/tools/ocr_tool.py`

#### New home: `backend/core/image_utils.py`

Extract only:

- `image_to_data_url(path: str) -> str` — lifted verbatim.

The `ocr_tool` function itself is half business logic (the prompt template) and half LLM call. Phase 0 extracts the prompt as a module-level constant, but leaves the LLM invocation for Phase 1 to redo behind the `PipelineLLM` interface.

#### New home: `backend/core/prompts.py`

Lift the three prompt templates verbatim:

- `OCR_PROMPT_TEMPLATE` from `ocr_tool.py`
- `PARSER_PROMPT_TEMPLATE` from `ocr_result_parser.py` (the `text = "Extract receipt information..."` block)
- `CLASSIFY_PROMPT_TEMPLATE` and `SUBCLASSIFY_PROMPT_TEMPLATE` from `receipt_classifier.py`

Expose them as functions that take the dynamic bits as arguments, returning the rendered prompt string:

```python
def render_parser_prompt(ocr_receipts: list[OCR_Receipt], accepted_currencies: list[str]) -> str: ...
def render_classify_prompt(categories: list[Category], pending: list[tuple[int, str]]) -> str: ...
def render_subclassify_prompt(sub_cat_pending: list[tuple[int, str, Category]]) -> str: ...
```

Phase 1's service layer calls these, then hands the rendered prompt to `PipelineLLM`. Prompt text stays in `core/`, LLM transport stays in `services/`.

---

## Target structure after Phase 0

```
backend/
├── core/                          # NEW — framework-free, pure functions
│   ├── __init__.py
│   ├── schemas.py                 # ParsedReceipt, Category, ReceiptClassification, ...
│   ├── currency.py                # detect_currency, normalize_text, ...
│   ├── classifier.py              # regex_classify_one, regex_classify_batch, _compile_regex_pattern
│   ├── image_utils.py             # image_to_data_url
│   ├── prompts.py                 # render_ocr_prompt, render_parser_prompt, ...
│   ├── config_loader.py           # load_yaml_config
│   └── categories_seed.py         # load_seed_categories
│
├── configs/                       # Unchanged
│   ├── CategoryConfigs.yaml
│   └── OcrResultParserConfigs.yaml
│
├── tools/                         # LEGACY — mark for deletion after Phase 1 ships
│   ├── ocr_tool.py
│   ├── ocr_result_parser.py
│   ├── receipt_classifier.py
│   └── config_loader.py
│
└── tests/                         # NEW
    └── core/
        ├── test_currency.py
        ├── test_classifier.py
        └── test_schemas.py
```

Keep the legacy `tools/` alongside — don't delete it in Phase 0. Phase 1 is where you cut the cord, once you've verified the new pipeline produces the same outputs.

---

## Acceptance criteria for Phase 0

- [ ] `backend/core/` has zero imports of `langchain`, `langgraph`, `langchain_openai`, `langchain_core`.
- [ ] `pip install -r requirements.txt` produces a new `requirements-core.txt` listing only: `pydantic`, `PyYAML`, `regex` (if used), and nothing else. `core/` runs against this minimal set.
- [ ] `pytest tests/core/` passes with at least 15 assertions across `test_currency.py` and `test_classifier.py`.
- [ ] The legacy `backend/tools/*.py` files can be rewritten to import from `backend/core/` — currency detection, regex classification, prompts — and still produce identical outputs on the test images. **You don't actually have to rewrite them.** You just have to prove it's possible by running one end-to-end image through both codepaths and diffing the JSON output.
- [ ] `CategoryConfigs.yaml` loads via `load_seed_categories()` and returns 9 `Category` objects with compiled regex patterns.

---

## Fixes to make while you're in there

A few latent bugs in the legacy code. Fix them now — they'll bite Phase 1 otherwise:

1. **`receipt_classifier.py` line ~70**: `Category(name=..., keywords=..., subCategories=subCategories, ...)` passes `subCategories=` but the field is `sub_categories`. Pydantic silently ignores the extra kwarg and leaves `sub_categories=None`. **This means the two-stage subclassification flow is currently dead code.** Fix: rename everywhere to `sub_categories`.

2. **`receipt_classifier.py` in `regex_search`**: the non-matched branch builds `ReceiptCategory(idx=idx, category=merchant, sub_category=None, matched=True, keyword=keyword)` — sets `matched=True` and shoves the raw merchant name into `category`. Should be `matched=False, category='Others'` (or leave for the LLM fallback to fill in, which is what the comment says it's supposed to do). Fix: return the pending tuple to the LLM stage untouched, don't pre-fill a misleading `ReceiptCategory`.

3. **`classify()` final return**: `return ClassificationResult(classification_result=classified)` but the field is `classification_results` (plural). Another pydantic-swallows-the-typo bug.

4. **`ocr_result_parser.py` `@tool` decorator**: `@tool('model_ocr_result_parser', args_schema=OCR_Results, ...)` — `OCR_Results` isn't really a tool-args schema, it's the output of the previous tool. LangChain happens to accept it because it's a BaseModel with a `list` field. Doesn't matter for Phase 1 (we're replacing the decorator), but flag it so you don't carry the mistake forward when rewriting.

Document these as commit messages when you fix them. Phase 1's orchestrator will depend on the subcategory flow actually working.

---

## What Phase 0 does **not** include

- No HTTP layer. No FastAPI. No Uvicorn.
- No database. No SQLAlchemy. No Alembic.
- No new pipeline orchestrator. The `Classifier.classify()` top-level flow stays in legacy-land for now; Phase 1 rebuilds it.
- No LLM abstraction. `PipelineLLM` interface is a Phase 1 concern.
- No merchant normalization (that's Phase 2).
- No user-facing changes. The existing `test.py` LangGraph agent keeps working after Phase 0 — you've only added a new `core/` package alongside.

Phase 0 is purely **preparation**. The product still does exactly what it did before. But now Phase 1 has clean Lego pieces to build with.

---

## Stack questions to answer before starting

1. **Pydantic v1 or v2?** Legacy uses v2 (`pydantic==2.12.0`). Stay on v2. If you ever need v1 compat, use `pydantic.v1` import path.
2. **Python version?** Legacy conda env is 3.11. Phase 1 FastAPI is comfortable on 3.11 or 3.12 — pick one and stick with it.
3. **Test runner?** Pytest recommended (zero config, `pytest tests/` just works). The legacy repo has no tests, so you're starting fresh.
4. **Should the new `core/` live in a separate git repo?** No — same repo, just a new top-level package. You'll want it co-located with the services that use it.
