import os
from mim.shared.config import Config, load_config

def test_default_config():
    config = load_config()
    assert config.get("environment") == "development"
    assert config.get("log_level") == "INFO"

def test_custom_env_variable(monkeypatch):
    monkeypatch.setenv("MIM_ENV", "production")
    config = Config()
    assert config.get("environment") == "production"