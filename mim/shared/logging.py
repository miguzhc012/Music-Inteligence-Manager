import logging
import sys
from typing import Optional
from .config import Config

def configure_logging(config: Optional[Config] = None) -> None:
    if config is None:
        config = Config()

    level_name = config.get("log_level", "INFO").upper()
    log_format = config.get(
        "log_format",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logging.basicConfig(
        level=getattr(logging, level_name, logging.INFO),
        format=log_format,
        stream=sys.stdout,
        force=True,
    )