from __future__ import annotations

from typing import List

from backend.core.classifier import _compile_regex_pattern
from backend.core.config_loader import load_yaml_config
from backend.core.schemas import Category, Subcategory

_SEED_FILENAME = "CategoryConfigs.yaml"


def load_seed_categories() -> List[Category]:
    """Load the default category set from YAML with compiled keyword regex.

    Phase 1's DB seeder calls this on first boot and writes each Category row
    with its keywords (the regex is recomputed at classification time).
    """
    cfg = load_yaml_config(_SEED_FILENAME)
    categories: List[Category] = []

    for cat in cfg["categories"]:
        subs = cat.get("subCategories") or []
        sub_models: List[Subcategory] = []
        for subcat in subs:
            sub_models.append(
                Subcategory(
                    name=subcat["name"],
                    parent_name=cat["name"],
                    keywords=subcat["keywords"],
                    regex=_compile_regex_pattern(subcat["keywords"]),
                )
            )

        categories.append(
            Category(
                name=cat["name"],
                keywords=cat["keywords"],
                sub_categories=sub_models or None,
                regex=_compile_regex_pattern(cat["keywords"]),
            )
        )

    return categories
