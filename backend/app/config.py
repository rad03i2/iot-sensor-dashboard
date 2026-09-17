from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EcoPulse AI"
    simulation_interval_seconds: float = 5.0
    adafruit_io_enabled: bool = False
    adafruit_io_username: str = ""
    adafruit_io_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
