import yaml

from importlib.resources import files

PKG = "backend.configs"

def load_config(config_name: str) -> dict:
    text = (files(PKG) / config_name).read_text(encoding="utf-8")
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise RuntimeError(f"Error parsing {config_name}: {e}")