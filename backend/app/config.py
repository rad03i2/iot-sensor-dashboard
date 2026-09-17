from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EcoPulse AI"
    simulation_interval_seconds: float = 5.0

    database_path: str = "data/ecopulse.db"
    history_retention_days: int = 30
    seed_demo_history: bool = True
    demo_history_hours: int = 24
    demo_history_step_minutes: int = 10

    adafruit_io_enabled: bool = False
    adafruit_io_username: str = ""
    adafruit_io_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
