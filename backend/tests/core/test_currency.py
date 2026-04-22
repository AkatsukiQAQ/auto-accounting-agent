from backend.core.currency import (
    CURRENCY_HINTS,
    CURRENCY_TABLE,
    detect_currency,
    normalize_text,
    split_lines,
)


# ---- normalize_text ----

def test_normalize_text_nfkc_fullwidth_digits():
    assert normalize_text("１２３") == "123"


def test_normalize_text_crlf_to_lf():
    assert normalize_text("a\r\nb\rc") == "a\nb\nc"


def test_normalize_text_collapses_spaces_and_zwsp():
    assert normalize_text("foo​　\tbar") == "foo bar"


def test_normalize_text_strips_outer_whitespace():
    assert normalize_text("   hello   ") == "hello"


# ---- split_lines ----

def test_split_lines_drops_blank_lines_and_strips():
    assert split_lines(" a \n\n  b  \nc") == ["a", "b", "c"]


def test_split_lines_empty_input():
    assert split_lines("") == []


# ---- detect_currency happy-path / table hits ----

def test_detect_currency_cny_via_yuan_char():
    assert detect_currency("Amount: 100元") == "CNY"


def test_detect_currency_cny_via_fullwidth_yen_sign():
    assert detect_currency("金额 ￥20.00") == "CNY"


def test_detect_currency_jpy_via_kanji():
    assert detect_currency("Cost: 200円") == "JPY"


def test_detect_currency_jpy_via_yen_keyword():
    assert detect_currency("Amount: 150 YEN") == "JPY"


def test_detect_currency_usd_via_us_dollar_token():
    assert detect_currency("Charge: US$75.00") == "USD"


def test_detect_currency_eur_via_symbol():
    assert detect_currency("Fee: €30.00") == "EUR"


def test_detect_currency_krw_via_symbol():
    assert detect_currency("Price: 400₩") == "KRW"


def test_detect_currency_hkd_via_token():
    assert detect_currency("Amount: 150 HK$") == "HKD"


# ---- detect_currency ambiguity & edge cases ----

def test_detect_currency_no_token_returns_none():
    assert detect_currency("No currency here") is None


def test_detect_currency_empty_string():
    assert detect_currency("") is None


def test_detect_currency_whitespace_only():
    assert detect_currency("   \n\t  ") is None


def test_detect_currency_bare_yen_without_context_is_none():
    # Architectural contract: bare ¥ with no CJK context and no symbol_defaults
    # is ambiguous and must return None. (Legacy returned "¥" literal — fixed here.)
    assert detect_currency("Total: ¥123.45") is None


def test_detect_currency_bare_dollar_without_context_is_none():
    # Bare $ with no "US"/"USD" token and no symbol_defaults is ambiguous.
    assert detect_currency("Payment: $50.00") is None


def test_detect_currency_bare_dollar_resolves_with_symbol_defaults():
    assert detect_currency("Payment: $50.00", symbol_defaults={"$": "USD"}) == "USD"


def test_detect_currency_bare_yen_resolves_with_symbol_defaults():
    assert detect_currency("Total: ¥123.45", symbol_defaults={"¥": "CNY"}) == "CNY"


def test_detect_currency_bare_yen_resolves_via_jpy_context():
    assert detect_currency("¥ 500 JPY") == "JPY"


def test_detect_currency_bare_yen_resolves_via_cjk_cny_context():
    assert detect_currency("¥ 人民币 20") == "CNY"


def test_detect_currency_bare_dollar_resolves_via_us_context():
    assert detect_currency("Pay US please $5") == "USD"


def test_detect_currency_case_insensitive_usd():
    assert detect_currency("paid 4 usd") == "USD"


def test_detect_currency_first_hint_wins_on_mixed_text():
    # ¥ hint is first in CURRENCY_HINTS; when both ¥ and JPY appear, ¥ hits first.
    # JPY context then disambiguates it to JPY.
    assert detect_currency("Total ¥500 JPY · Subtotal $4") == "JPY"


def test_detect_currency_gbp_via_symbol():
    assert detect_currency("Price £10") == "GBP"


# ---- module-level constants sanity ----

def test_currency_table_includes_core_symbols():
    for sym in ["CNY", "JPY", "USD", "EUR", "GBP", "KRW", "HKD"]:
        assert sym in CURRENCY_TABLE


def test_currency_hints_has_yen_first():
    # Load-bearing ordering — see detect_currency docstring.
    assert CURRENCY_HINTS[0] == r"¥"
