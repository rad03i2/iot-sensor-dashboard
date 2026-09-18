from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ScenarioName = Literal["baseline", "traffic_surge", "dust_storm", "industrial_event", "heat_wave"]
Severity = Literal["info", "warning", "critical"]


class Station(BaseModel):
    id: str
    name: str
    profile: str
    latitude: float
    longitude: float


class EnvironmentalReading(BaseModel):
    station_id: str
    station_name: str
    timestamp: datetime
    source: Literal["simulated", "physical_sensor", "external_api"] = "simulated"
    scenario: ScenarioName = "baseline"
    temperature_c: float
    humidity_pct: float
    pm25_ug_m3: float
    pm10_ug_m3: float
    co2_ppm: float
    noise_db: float
    estimated_aqi: int = Field(ge=0, le=500)
    environmental_health_score: float = Field(ge=0, le=100)


class Alert(BaseModel):
    id: str
    station_id: str
    created_at: datetime
    severity: Severity
    metric: str
    value: float
    title: str
    message: str


class ScenarioRequest(BaseModel):
    intensity: float = Field(default=1.0, ge=0.1, le=2.0)
