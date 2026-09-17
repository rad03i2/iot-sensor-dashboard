import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone

from .analytics import environmental_health_score, estimated_aqi_from_pm25
from .models import EnvironmentalReading, ScenarioName, Station


STATIONS = [
    Station(id="residential", name="Residential District", profile="residential", latitude=36.35, longitude=43.12),
    Station(id="traffic", name="Traffic Corridor", profile="traffic", latitude=36.34, longitude=43.14),
    Station(id="industrial", name="Industrial Zone", profile="industrial", latitude=36.31, longitude=43.18),
    Station(id="green", name="Green Zone", profile="green", latitude=36.36, longitude=43.10),
    Station(id="campus", name="University Campus", profile="campus", latitude=36.37, longitude=43.15),
]


@dataclass(frozen=True)
class Profile:
    temperature_offset: float
    humidity_offset: float
    pm25: float
    pm10: float
    co2: float
    noise: float


PROFILES = {
    "residential": Profile(0.0, 0.0, 18, 35, 520, 50),
    "traffic": Profile(1.2, -4.0, 34, 58, 720, 69),
    "industrial": Profile(1.8, -6.0, 46, 82, 820, 66),
    "green": Profile(-1.6, 7.0, 10, 22, 440, 41),
    "campus": Profile(0.3, 1.5, 20, 38, 560, 57),
}


SCENARIO_EFFECTS = {
    "baseline": dict(temp=0, humidity=0, pm25=1.0, pm10=1.0, co2=1.0, noise=0),
    "traffic_surge": dict(temp=0.8, humidity=-2, pm25=1.55, pm10=1.35, co2=1.32, noise=9),
    "dust_storm": dict(temp=2.0, humidity=-10, pm25=2.5, pm10=4.2, co2=1.04, noise=3),
    "industrial_event": dict(temp=1.5, humidity=-4, pm25=2.1, pm10=1.8, co2=1.45, noise=7),
    "heat_wave": dict(temp=8.0, humidity=-13, pm25=1.22, pm10=1.18, co2=1.05, noise=1),
}


class EnvironmentalSimulator:
    def __init__(self) -> None:
        self.scenario: ScenarioName = "baseline"
        self.intensity: float = 1.0
        self.tick_count = 0
        self.previous: dict[str, EnvironmentalReading] = {}

    def set_scenario(self, scenario: ScenarioName, intensity: float = 1.0) -> None:
        self.scenario = scenario
        self.intensity = intensity

    def _daily_cycle(self, hour: float) -> tuple[float, float]:
        temperature_wave = 7.5 * math.sin((hour - 8) / 24 * 2 * math.pi)
        humidity_wave = -10.0 * math.sin((hour - 8) / 24 * 2 * math.pi)
        return temperature_wave, humidity_wave

    @staticmethod
    def _smooth(previous: float | None, target: float, inertia: float = 0.72) -> float:
        if previous is None:
            return target
        return previous * inertia + target * (1 - inertia)

    def generate(self, station: Station, now: datetime | None = None) -> EnvironmentalReading:
        now = now or datetime.now(timezone.utc)
        profile = PROFILES[station.profile]
        effect = SCENARIO_EFFECTS[self.scenario]
        hour = now.hour + now.minute / 60
        temp_wave, humidity_wave = self._daily_cycle(hour)
        activity = 1.0 + 0.18 * math.sin((hour - 7) / 24 * 4 * math.pi)

        scenario_weight = self.intensity
        target_temp = 27 + temp_wave + profile.temperature_offset + effect["temp"] * scenario_weight + random.gauss(0, 0.45)
        target_humidity = 48 + humidity_wave + profile.humidity_offset + effect["humidity"] * scenario_weight + random.gauss(0, 1.4)
        target_pm25 = profile.pm25 * activity * (1 + (effect["pm25"] - 1) * scenario_weight) + random.gauss(0, 2.0)
        target_pm10 = profile.pm10 * activity * (1 + (effect["pm10"] - 1) * scenario_weight) + target_pm25 * 0.18 + random.gauss(0, 3.0)
        target_co2 = profile.co2 * activity * (1 + (effect["co2"] - 1) * scenario_weight) + random.gauss(0, 18)
        target_noise = profile.noise + effect["noise"] * scenario_weight + 4 * math.sin(hour / 24 * 2 * math.pi) + random.gauss(0, 1.5)

        old = self.previous.get(station.id)
        temperature = self._smooth(old.temperature_c if old else None, target_temp)
        humidity = self._smooth(old.humidity_pct if old else None, target_humidity)
        pm25 = self._smooth(old.pm25_ug_m3 if old else None, target_pm25, 0.66)
        pm10 = self._smooth(old.pm10_ug_m3 if old else None, target_pm10, 0.66)
        co2 = self._smooth(old.co2_ppm if old else None, target_co2, 0.68)
        noise = self._smooth(old.noise_db if old else None, target_noise, 0.6)

        temperature = round(max(-20, min(60, temperature)), 1)
        humidity = round(max(5, min(100, humidity)), 1)
        pm25 = round(max(0, pm25), 1)
        pm10 = round(max(pm25, pm10), 1)
        co2 = round(max(350, co2), 0)
        noise = round(max(25, min(120, noise)), 1)

        reading = EnvironmentalReading(
            station_id=station.id,
            station_name=station.name,
            timestamp=now,
            source="simulated",
            scenario=self.scenario,
            temperature_c=temperature,
            humidity_pct=humidity,
            pm25_ug_m3=pm25,
            pm10_ug_m3=pm10,
            co2_ppm=co2,
            noise_db=noise,
            estimated_aqi=estimated_aqi_from_pm25(pm25),
            environmental_health_score=environmental_health_score(
                pm25=pm25, co2=co2, noise=noise, temperature=temperature, humidity=humidity
            ),
        )
        self.previous[station.id] = reading
        return reading

    def tick(self) -> list[EnvironmentalReading]:
        self.tick_count += 1
        return [self.generate(station) for station in STATIONS]
