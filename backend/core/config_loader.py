from __future__ import annotations

from importlib.resources import files

import yaml

PKG = "backend.configs"


def load_yaml_config(config_name: str) -> dict:
    """Load a YAML config bundled as package data in ``backend.configs``."""
    text = (files(PKG) / config_name).read_text(encoding="utf-8")
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise RuntimeError(f"Error parsing {config_name}: {e}")
