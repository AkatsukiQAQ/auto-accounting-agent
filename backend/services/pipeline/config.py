from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from backend.core.config_loader import load_yaml_config

_CURRENCY_CONFIG_FILE = "OcrResultParserConfigs.yaml"


@dataclass(frozen=True)
class PipelineConfig:
    """Static per-request configuration passed into every pipeline stage."""

    accepted_currencies: tuple[str, ...]
    symbol_defaults: Mapping[str, str] = field(default_factory=dict)


def load_default_pipeline_config() -> PipelineConfig:
    """Load accepted currencies + symbol defaults from the legacy YAML.

    M4 will wrap this with env-var overrides; for now a plain read from the
    checked-in YAML is enough — the values match what the legacy parser used.
    """
    cfg = load_yaml_config(_CURRENCY_CONFIG_FILE)
    currency_cfg = cfg.get("currency", {}) or {}
    return PipelineConfig(
        accepted_currencies=tuple(currency_cfg.get("accepted_currencies", []) or []),
        symbol_defaults=dict(currency_cfg.get("symbol_defaults", {}) or {}),
    )
