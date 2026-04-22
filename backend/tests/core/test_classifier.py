from backend.core.classifier import (
    ClassifyBuckets,
    _compile_regex_pattern,
    regex_classify_batch,
    regex_classify_one,
    regex_match_keyword,
)
from backend.core.schemas import Category, Subcategory


# ---- _compile_regex_pattern ----

def test_compile_regex_pattern_empty_returns_none():
    assert _compile_regex_pattern([]) is None


def test_compile_regex_pattern_single_latin_with_space():
    # 'seven eleven' must compile so a space becomes \s+ — load-bearing substitution.
    pat = _compile_regex_pattern(["seven eleven"])
    assert pat is not None
    assert pat.search("went to seven eleven today") is not None
    # \s+ also matches multiple spaces / tabs
    assert pat.search("seven  eleven") is not None


def test_compile_regex_pattern_mixed_cjk_and_latin():
    pat = _compile_regex_pattern(["Steam", "ローソン"])
    assert pat is not None
    assert pat.search("Steam 2,800円") is not None
    assert pat.search("ローソン 410円") is not None


def test_compile_regex_pattern_case_insensitive_latin():
    pat = _compile_regex_pattern(["Steam"])
    assert pat.search("STEAM 100JPY") is not None


def test_compile_regex_pattern_word_boundary_on_latin():
    # 'Bus' should NOT match inside 'Business' because \b word boundary is applied to Latin tokens.
    pat = _compile_regex_pattern(["Bus"])
    assert pat.search("Business center") is None
    assert pat.search("Bus ticket") is not None


def test_compile_regex_pattern_no_word_boundary_on_cjk():
    # CJK keywords skip \b — '駅' inside longer CJK text still matches.
    pat = _compile_regex_pattern(["駅"])
    assert pat.search("新宿駅から") is not None


# ---- regex_match_keyword ----

def test_regex_match_keyword_none_pattern():
    assert regex_match_keyword("anything", None) == (False, None)


def test_regex_match_keyword_hit_returns_keyword():
    pat = _compile_regex_pattern(["lawson"])
    matched, kw = regex_match_keyword("at Lawson", pat)
    assert matched is True
    assert kw.lower() == "lawson"


def test_regex_match_keyword_miss():
    pat = _compile_regex_pattern(["lawson"])
    assert regex_match_keyword("at 7-Eleven", pat) == (False, None)


# ---- regex_classify_one ----

def _transport_category() -> Category:
    subs = [
        Subcategory(
            name="Train", parent_name="Transportation", keywords=["駅", "鉄道"],
            regex=_compile_regex_pattern(["駅", "鉄道"]),
        ),
        Subcategory(
            name="Taxi", parent_name="Transportation", keywords=["タクシー"],
            regex=_compile_regex_pattern(["タクシー"]),
        ),
        Subcategory(
            name="Bus", parent_name="Transportation", keywords=["バス", "Bus"],
            regex=_compile_regex_pattern(["バス", "Bus"]),
        ),
    ]
    top_keywords = ["駅", "タクシー", "バス", "Bus"]
    return Category(
        name="Transportation",
        keywords=top_keywords,
        sub_categories=subs,
        regex=_compile_regex_pattern(top_keywords),
    )


def _game_category() -> Category:
    return Category(
        name="Game",
        keywords=["Steam", "Arknights"],
        sub_categories=None,
        regex=_compile_regex_pattern(["Steam", "Arknights"]),
    )


def test_regex_classify_one_top_category_hit():
    cats = [_transport_category(), _game_category()]
    cat, kw = regex_classify_one("Steam Wallet", cats)
    assert cat is not None
    assert cat.name == "Game"
    assert kw.lower() == "steam"


def test_regex_classify_one_miss_returns_nones():
    cats = [_game_category()]
    cat, kw = regex_classify_one("もとまちユニオン", cats)
    assert cat is None
    assert kw is None


def test_regex_classify_one_subcategory_hit():
    transport = _transport_category()
    cat, kw = regex_classify_one("東京タクシー", transport.sub_categories)
    assert cat is not None
    assert cat.name == "Taxi"


# ---- regex_classify_batch ----

def test_regex_classify_batch_empty_input():
    buckets = regex_classify_batch([], [_game_category()])
    assert isinstance(buckets, ClassifyBuckets)
    assert buckets.matched == []
    assert buckets.needs_subcategory_llm == []
    assert buckets.needs_top_category_llm == []


def test_regex_classify_batch_top_only_no_subs():
    cats = [_game_category()]
    buckets = regex_classify_batch([(0, "Steam"), (1, "Arknights")], cats)
    assert len(buckets.matched) == 2
    for row in buckets.matched:
        assert row.category == "Game"
        assert row.sub_category is None
        assert row.matched is True


def test_regex_classify_batch_subcategory_resolved():
    transport = _transport_category()
    buckets = regex_classify_batch([(0, "新宿駅")], [transport])
    assert len(buckets.matched) == 1
    row = buckets.matched[0]
    assert row.category == "Transportation"
    assert row.sub_category == "Train"
    assert row.matched is True


def test_regex_classify_batch_top_matched_but_no_sub_goes_to_llm():
    # Build a Transportation-shaped category whose top-level keywords are broader
    # than its subcategories, so a merchant hits the top but no sub.
    transport = Category(
        name="Transportation",
        keywords=["交通"],
        sub_categories=[
            Subcategory(
                name="Train", parent_name="Transportation", keywords=["駅"],
                regex=_compile_regex_pattern(["駅"]),
            ),
        ],
        regex=_compile_regex_pattern(["交通"]),
    )
    buckets = regex_classify_batch([(0, "交通費")], [transport])
    assert buckets.matched == []
    assert len(buckets.needs_subcategory_llm) == 1
    idx, keyword, cat = buckets.needs_subcategory_llm[0]
    assert idx == 0
    assert cat.name == "Transportation"


def test_regex_classify_batch_no_match_goes_to_top_llm():
    cats = [_game_category()]
    buckets = regex_classify_batch([(0, "unknown store")], cats)
    assert buckets.matched == []
    assert buckets.needs_top_category_llm == [(0, "unknown store")]


def test_regex_classify_batch_duplicate_merchant_preserved():
    cats = [_game_category()]
    buckets = regex_classify_batch([(0, "Steam"), (1, "Steam")], cats)
    assert len(buckets.matched) == 2
    idxs = sorted(row.idx for row in buckets.matched)
    assert idxs == [0, 1]


def test_regex_classify_batch_mixed_routing():
    transport = _transport_category()
    game = _game_category()
    rows = [
        (0, "Steam"),             # -> matched (Game, no sub)
        (1, "新宿駅"),            # -> matched (Transportation, Train)
        (2, "unknown shop"),      # -> needs_top_category_llm
    ]
    buckets = regex_classify_batch(rows, [transport, game])
    assert len(buckets.matched) == 2
    assert len(buckets.needs_top_category_llm) == 1
    assert buckets.needs_top_category_llm[0] == (2, "unknown shop")
