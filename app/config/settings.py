from __future__ import annotations

import logging
from pathlib import Path

from platformdirs import user_config_dir, user_log_dir

APP_NAME = "ETL Loader"
APP_AUTHOR = "ETL Loader"


def config_dir() -> Path:
    path = Path(user_config_dir(APP_NAME, APP_AUTHOR))
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_dir() -> Path:
    path = Path(user_log_dir(APP_NAME, APP_AUTHOR))
    path.mkdir(parents=True, exist_ok=True)
    return path


def setup_logging() -> None:
    logfile = log_dir() / "etl-loader.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler(logfile), logging.StreamHandler()],
    )
