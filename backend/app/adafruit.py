import httpx

from .config import settings
from .models import EnvironmentalReading


class AdafruitPublisher:
    """Optional bridge from the virtual platform to Adafruit IO.

    Credentials remain local through environment variables. Failures here should
    never stop the simulation engine.
    """

    def __init__(self) -> None:
        self.enabled = bool(
            settings.adafruit_io_enabled
            and settings.adafruit_io_username
            and settings.adafruit_io_key
        )

    async def publish(self, reading: EnvironmentalReading) -> None:
        if not self.enabled:
            return

        feeds = {
            "temperature": reading.temperature_c,
            "humidity": reading.humidity_pct,
            "pm25": reading.pm25_ug_m3,
            "co2": reading.co2_ppm,
            "aqi": reading.estimated_aqi,
            "noise": reading.noise_db,
        }
        headers = {"X-AIO-Key": settings.adafruit_io_key}
        async with httpx.AsyncClient(timeout=5.0) as client:
            for feed, value in feeds.items():
                url = f"https://io.adafruit.com/api/v2/{settings.adafruit_io_username}/feeds/{feed}/data"
                try:
                    await client.post(url, json={"value": value}, headers=headers)
                except httpx.HTTPError:
                    # External cloud transport must not take down the local engine.
                    continue
