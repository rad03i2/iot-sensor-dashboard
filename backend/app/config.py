from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EcoPulse Mosul"
    simulation_enabled: bool = False
    simulation_interval_seconds: float = 5.0

    database_path: str = "data/ecopulse.db"
    history_retention_days: int = 30
    seed_demo_history: bool = False
    demo_history_hours: int = 24
    demo_history_step_minutes: int = 10

    mosul_latitude: float = 36.335
    mosul_longitude: float = 43.118889
    mosul_timezone: str = "Asia/Baghdad"
    live_refresh_seconds: int = 300
    upstream_timeout_seconds: float = 12.0

    adafruit_io_enabled: bool = False
    adafruit_io_username: str = ""
    adafruit_io_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
