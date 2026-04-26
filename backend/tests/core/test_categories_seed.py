from backend.core.categories_seed import load_seed_categories
from backend.core.schemas import Category, Subcategory


def test_load_seed_categories_returns_ten_categories():
    # Spec/BACKEND_PHASE_0.md claims 9; actual YAML ships 10 (Supermarket,
    # Convenience Store, Transportation, Restaurant, Delivery, Shopping, Game,
    # Health, Sports, Others). The YAML is source of truth.
    cats = load_seed_categories()
    assert len(cats) == 10
    for c in cats:
        assert isinstance(c, Category)


def test_load_seed_categories_expected_names():
    cats = load_seed_categories()
    names = {c.name for c in cats}
    expected = {
        "Supermarket",
        "Convenience Store",
        "Transportation",
        "Restaurant",
        "Delivery",
        "Shopping",
        "Game",
        "Health",
        "Sports",
    }
    # Legacy YAML also ships an Others bucket; the test is tolerant to additions
    # but must contain every expected name.
    assert expected.issubset(names)


def test_transportation_has_four_subcategories():
    # Regression for legacy bug #1: subCategories kwarg typo silently left
    # sub_categories=None. With the fix, Transportation must expose its 4 subs.
    cats = load_seed_categories()
    transport = next(c for c in cats if c.name == "Transportation")
    assert transport.sub_categories is not None
    assert len(transport.sub_categories) == 4
    sub_names = {s.name for s in transport.sub_categories}
    assert sub_names == {"Train", "Taxi", "Car", "Bus"}
    for sub in transport.sub_categories:
        assert isinstance(sub, Subcategory)
        assert sub.parent_name == "Transportation"
        assert sub.regex is not None


def test_categories_with_keywords_have_compiled_regex():
    cats = load_seed_categories()
    for c in cats:
        if c.keywords:
            assert c.regex is not None, f"{c.name} has keywords but no compiled regex"
        else:
            assert c.regex is None, f"{c.name} has no keywords but got a regex"


def test_compiled_regex_matches_known_keyword():
    cats = load_seed_categories()
    convenience = next(c for c in cats if c.name == "Convenience Store")
    assert convenience.regex is not None
    assert convenience.regex.search("went to lawson") is not None
