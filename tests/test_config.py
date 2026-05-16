import os
from unittest.mock import patch

from intentdiff.config import get_api_key, get_config_path, load_config, set_api_key


def test_get_config_path_local():
    with patch("pathlib.Path.exists", return_value=True):
        path = get_config_path()
        assert path.name == ".intentdiff.toml"


def test_get_config_path_global():
    with patch("pathlib.Path.exists", return_value=False):
        path = get_config_path()
        assert path.name == "config.toml"


def test_load_config_empty():
    with patch("intentdiff.config.get_config_path") as mock_get_path:
        mock_path = mock_get_path.return_value
        mock_path.exists.return_value = False
        assert load_config() == {}


def test_get_api_key_env():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-env-key"}):
        assert get_api_key() == "test-env-key"


@patch("intentdiff.config.load_config")
def test_get_api_key_config(mock_load):
    mock_load.return_value = {"anthropic": {"api_key": "test-config-key"}}
    with patch.dict(os.environ, {}, clear=True):
        assert get_api_key() == "test-config-key"


@patch("intentdiff.config.load_config")
@patch("intentdiff.config.save_config")
def test_set_api_key(mock_save, mock_load):
    mock_load.return_value = {}
    set_api_key("new-key")
    mock_save.assert_called_once_with({"anthropic": {"api_key": "new-key"}}, True)
