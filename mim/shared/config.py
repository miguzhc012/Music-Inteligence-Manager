import os
from pathlib import Path
from typing import Any, Dict, Optional

class Config:
    def __init__(self, env_file: Optional[Path] = None):
        self._data: Dict[str, Any] = {}
        if env_file and env_file.exists():
            self._load_dotenv(env_file)
        self._load_env()

    def _load_dotenv(self, path: Path) -> None:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

    def _load_env(self) -> None:
        self._data["environment"] = os.getenv("MIM_ENV", "development")
        self._data["log_level"] = os.getenv("MIM_LOG_LEVEL", "INFO")
        self._data["log_format"] = os.getenv(
            "MIM_LOG_FORMAT",
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def as_dict(self) -> Dict[str, Any]:
        return dict(self._data)

def load_config(env_file: Optional[Path] = None) -> Config:
    return Config(env_file)