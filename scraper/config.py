"""
Configuration module for the YouTube Library Scraper.
Handles defaults, configuration file loading, and path resolution.
"""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


DEFAULT_CONFIG_FILENAME = "config.json"
DEFAULT_COOKIES_FILENAME = "cookies.txt"
DEFAULT_DATA_DIR = "data"


@dataclass
class ScraperConfig:
    data_dir: Path = field(default_factory=lambda: Path(DEFAULT_DATA_DIR))
    cookies_file: Path = field(default_factory=lambda: Path(DEFAULT_COOKIES_FILENAME))
    cookies_from_browser: Optional[str] = None
    log_level: str = "info"
    rate_limit_delay_seconds: float = 0.5
    save_checkpoints: bool = True
    checkpoint_interval: int = 100
    schema_version: int = 1

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def checkpoints_dir(self) -> Path:
        return self.data_dir / "checkpoints"

    @property
    def watch_later_raw_path(self) -> Path:
        return self.raw_dir / "watch_later.json"

    @property
    def liked_raw_path(self) -> Path:
        return self.raw_dir / "liked.json"

    @property
    def videos_processed_path(self) -> Path:
        return self.processed_dir / "videos.json"

    @property
    def errors_log_path(self) -> Path:
        return self.logs_dir / "errors.json"

    def ensure_directories(self) -> None:
        """Create necessary directories if they do not exist."""
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        if self.save_checkpoints:
            self.checkpoints_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load(
        cls,
        config_path: Optional[str] = None,
        cookies_path_override: Optional[str] = None,
        cookies_from_browser_override: Optional[str] = None,
        data_dir_override: Optional[str] = None,
        log_level_override: Optional[str] = None,
    ) -> "ScraperConfig":
        """
        Load configuration from file and/or apply overrides.
        """
        config_data: Dict[str, Any] = {}

        # Determine config file location
        path_to_try = Path(config_path) if config_path else Path(DEFAULT_CONFIG_FILENAME)
        if path_to_try.exists() and path_to_try.is_file():
            try:
                with open(path_to_try, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
            except Exception as e:
                print(f"[!] Warning: Failed to parse config file '{path_to_try}': {e}. Using defaults.")

        # Environment variable overrides
        env_cookies = os.environ.get("YTLIB_COOKIES_FILE")
        if env_cookies:
            config_data["cookies_file"] = env_cookies
        env_browser = os.environ.get("YTLIB_COOKIES_BROWSER")
        if env_browser:
            config_data["cookies_from_browser"] = env_browser
        env_data_dir = os.environ.get("YTLIB_DATA_DIR")
        if env_data_dir:
            config_data["output_directory"] = env_data_dir

        # CLI overrides
        if cookies_path_override:
            config_data["cookies_file"] = cookies_path_override
        if cookies_from_browser_override:
            config_data["cookies_from_browser"] = cookies_from_browser_override
        if data_dir_override:
            config_data["output_directory"] = data_dir_override
        if log_level_override:
            config_data["log_level"] = log_level_override

        raw_data_dir = config_data.get("output_directory", DEFAULT_DATA_DIR)
        raw_cookies_file = config_data.get("cookies_file", DEFAULT_COOKIES_FILENAME)

        config = cls(
            data_dir=Path(raw_data_dir),
            cookies_file=Path(raw_cookies_file),
            cookies_from_browser=config_data.get("cookies_from_browser"),
            log_level=config_data.get("log_level", "info"),
            rate_limit_delay_seconds=float(config_data.get("rate_limit_delay_seconds", 0.5)),
            save_checkpoints=bool(config_data.get("save_checkpoints", True)),
            checkpoint_interval=int(config_data.get("checkpoint_interval", 100)),
            schema_version=int(config_data.get("schema_version", 1)),
        )


        config.ensure_directories()
        return config
