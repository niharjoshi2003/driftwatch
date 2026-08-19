from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bright_data_api_token: str = ""
    bright_data_collector_id: str = ""
    database_url: str = "sqlite:///./data/driftwatch.db"
    run_interval_minutes: int = 60
    baseline_window_runs: int = 8
    baseline_ewma_alpha: float = 0.3
    detect_z_threshold: float = 3.0
    detect_min_effect: float = 0.30
    heal_max_attempts: int = 3
    heal_poll_interval_seconds: int = 5
    heal_timeout_seconds: int = 900
    heal_max_concurrent: int = 1
    validator_fill_rate_tolerance: float = 0.10
    fixture_mode: bool = True
    contracts_path: Path = ROOT / "contracts" / "pricing_pages.yaml"
    fixtures_dir: Path = ROOT / "backend" / "tests" / "fixtures"
    day1_urls_path: Path = ROOT / "contracts" / "day1_urls.json"


def get_settings() -> Settings:
    return Settings()
