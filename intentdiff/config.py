import os
from pathlib import Path
from typing import Optional


def get_config_path() -> Path:
    # Check for project-local config first
    local_config = Path(".intentdiff.toml")
    if local_config.exists():
        return local_config

    # Fallback to user config
    user_config_dir = Path.home() / ".intentdiff"
    return user_config_dir / "config.toml"


def load_config() -> dict:
    config_path = get_config_path()
    if not config_path.exists():
        return {}

    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    with open(config_path, "rb") as f:
        return tomllib.load(f)


def save_config(config: dict, global_config: bool = True):
    if global_config:
        config_dir = Path.home() / ".intentdiff"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.toml"
    else:
        config_path = Path(".intentdiff.toml")

    api_key = config.get("anthropic", {}).get("api_key", "")
    with open(config_path, "w") as f:
        f.write("[anthropic]\n")
        f.write(f'api_key = "{api_key}"\n')


def get_api_key() -> Optional[str]:
    # Check environment variable first
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return api_key

    config = load_config()
    return config.get("anthropic", {}).get("api_key")


def set_api_key(api_key: str, global_config: bool = True):
    config = load_config()
    if "anthropic" not in config:
        config["anthropic"] = {}
    config["anthropic"]["api_key"] = api_key
    save_config(config, global_config)
