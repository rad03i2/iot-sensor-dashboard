from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import httpx


WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
FLOOD_URL = "https://flood-api.open-meteo.com/v1/flood"


class UpstreamSourceError(RuntimeError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _value_at(values: list[Any], index: int) -> Any:
    return values[index] if index < len(values) else None


class OpenMeteoMosulSource:
    def __init__(
        self,
        latitude: float,
        longitude: float,
        timezone_name: str,
        timeout_seconds: float = 12.0,
    ) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.timezone_name = timezone_name
        self.timeout_seconds = timeout_seconds

    async def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "User-Agent": "EcoPulse-Mosul/0.3 (+environmental-public-wallboard)",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                headers=headers,
                follow_redirects=True,
            ) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise UpstreamSourceError(str(exc)) from exc

        if not isinstance(payload, dict) or payload.get("error"):
            raise UpstreamSourceError(str(payload.get("reason", "Invalid upstream response")))
        return payload

    async def weather(self) -> dict[str, Any]:
        payload = await self._get_json(
            WEATHER_URL,
            {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "timezone": self.timezone_name,
                "current": ",".join(
                    [
                        "temperature_2m",
                        "relative_humidity_2m",
                        "apparent_temperature",
                        "precipitation",
                        "weather_code",
                        "cloud_cover",
                        "pressure_msl",
                        "wind_speed_10m",
                        "wind_direction_10m",
                        "wind_gusts_10m",
                        "visibility",
                        "is_day",
                    ]
                ),
                "hourly": ",".join(
                    [
                        "temperature_2m",
                        "relative_humidity_2m",
                        "precipitation_probability",
                        "weather_code",
                        "wind_speed_10m",
                        "wind_direction_10m",
                    ]
                ),
                "daily": ",".join(
                    [
                        "weather_code",
                        "temperature_2m_max",
                        "temperature_2m_min",
                        "precipitation_probability_max",
                        "sunrise",
                        "sunset",
                    ]
                ),
                "forecast_days": 5,
            },
        )

        current = payload.get("current") or {}
        hourly = payload.get("hourly") or {}
        daily = payload.get("daily") or {}

        hourly_rows = []
        times = hourly.get("time") or []
        for index, timestamp in enumerate(times[:24]):
            hourly_rows.append(
                {
                    "time": timestamp,
                    "temperature_c": _value_at(hourly.get("temperature_2m") or [], index),
                    "humidity_pct": _value_at(hourly.get("relative_humidity_2m") or [], index),
                    "precipitation_probability_pct": _value_at(
                        hourly.get("precipitation_probability") or [], index
                    ),
                    "weather_code": _value_at(hourly.get("weather_code") or [], index),
                    "wind_speed_kmh": _value_at(hourly.get("wind_speed_10m") or [], index),
                    "wind_direction_deg": _value_at(
                        hourly.get("wind_direction_10m") or [], index
                    ),
                }
            )

        daily_rows = []
        daily_times = daily.get("time") or []
        for index, day in enumerate(daily_times[:5]):
            daily_rows.append(
                {
                    "date": day,
                    "weather_code": _value_at(daily.get("weather_code") or [], index),
                    "temperature_max_c": _value_at(
                        daily.get("temperature_2m_max") or [], index
                    ),
                    "temperature_min_c": _value_at(
                        daily.get("temperature_2m_min") or [], index
                    ),
                    "precipitation_probability_max_pct": _value_at(
                        daily.get("precipitation_probability_max") or [], index
                    ),
                    "sunrise": _value_at(daily.get("sunrise") or [], index),
                    "sunset": _value_at(daily.get("sunset") or [], index),
                }
            )

        visibility = current.get("visibility")
        return {
            "observed_at": current.get("time"),
            "fetched_at": _now_iso(),
            "grid": {
                "latitude": payload.get("latitude"),
                "longitude": payload.get("longitude"),
                "elevation_m": payload.get("elevation"),
            },
            "current": {
                "temperature_c": current.get("temperature_2m"),
                "humidity_pct": current.get("relative_humidity_2m"),
                "apparent_temperature_c": current.get("apparent_temperature"),
                "precipitation_mm": current.get("precipitation"),
                "weather_code": current.get("weather_code"),
                "cloud_cover_pct": current.get("cloud_cover"),
                "pressure_msl_hpa": current.get("pressure_msl"),
                "wind_speed_kmh": current.get("wind_speed_10m"),
                "wind_direction_deg": current.get("wind_direction_10m"),
                "wind_gusts_kmh": current.get("wind_gusts_10m"),
                "visibility_km": round(float(visibility) / 1000, 1)
                if visibility is not None
                else None,
                "is_day": current.get("is_day"),
            },
            "hourly_24h": hourly_rows,
            "daily_5d": daily_rows,
        }

    async def air_quality(self) -> dict[str, Any]:
        payload = await self._get_json(
            AIR_URL,
            {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "timezone": self.timezone_name,
                "domains": "cams_global",
                "current": ",".join(
                    [
                        "pm10",
                        "pm2_5",
                        "carbon_monoxide",
                        "nitrogen_dioxide",
                        "sulphur_dioxide",
                        "ozone",
                        "dust",
                        "uv_index",
                        "us_aqi",
                        "european_aqi",
                        "aerosol_optical_depth",
                    ]
                ),
                "hourly": ",".join(
                    [
                        "pm10",
                        "pm2_5",
                        "dust",
                        "us_aqi",
                        "european_aqi",
                        "uv_index",
                    ]
                ),
                "forecast_hours": 24,
            },
        )

        current = payload.get("current") or {}
        hourly = payload.get("hourly") or {}
        rows = []
        times = hourly.get("time") or []
        for index, timestamp in enumerate(times[:24]):
            rows.append(
                {
                    "time": timestamp,
                    "pm10_ug_m3": _value_at(hourly.get("pm10") or [], index),
                    "pm25_ug_m3": _value_at(hourly.get("pm2_5") or [], index),
                    "dust_ug_m3": _value_at(hourly.get("dust") or [], index),
                    "us_aqi": _value_at(hourly.get("us_aqi") or [], index),
                    "european_aqi": _value_at(hourly.get("european_aqi") or [], index),
                    "uv_index": _value_at(hourly.get("uv_index") or [], index),
                }
            )

        return {
            "observed_at": current.get("time"),
            "fetched_at": _now_iso(),
            "grid": {
                "latitude": payload.get("latitude"),
                "longitude": payload.get("longitude"),
            },
            "current": {
                "pm10_ug_m3": current.get("pm10"),
                "pm25_ug_m3": current.get("pm2_5"),
                "carbon_monoxide_ug_m3": current.get("carbon_monoxide"),
                "nitrogen_dioxide_ug_m3": current.get("nitrogen_dioxide"),
                "sulphur_dioxide_ug_m3": current.get("sulphur_dioxide"),
                "ozone_ug_m3": current.get("ozone"),
                "dust_ug_m3": current.get("dust"),
                "uv_index": current.get("uv_index"),
                "us_aqi": current.get("us_aqi"),
                "european_aqi": current.get("european_aqi"),
                "aerosol_optical_depth": current.get("aerosol_optical_depth"),
            },
            "hourly_24h": rows,
        }

    async def tigris_discharge(self) -> dict[str, Any]:
        payload = await self._get_json(
            FLOOD_URL,
            {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "daily": "river_discharge",
                "past_days": 7,
                "forecast_days": 7,
                "cell_selection": "nearest",
            },
        )

        daily = payload.get("daily") or {}
        dates = daily.get("time") or []
        values = daily.get("river_discharge") or []
        series = [
            {"date": day, "river_discharge_m3_s": _value_at(values, index)}
            for index, day in enumerate(dates)
        ]

        today = date.today().isoformat()
        current_index = 0
        for index, row in enumerate(series):
            if row["date"] <= today and row["river_discharge_m3_s"] is not None:
                current_index = index

        current = (
            series[current_index]
            if series
            else {"date": None, "river_discharge_m3_s": None}
        )
        previous = series[current_index - 1] if current_index > 0 else None
        trend_pct = None
        if (
            previous
            and previous.get("river_discharge_m3_s")
            and current.get("river_discharge_m3_s") is not None
        ):
            old = float(previous["river_discharge_m3_s"])
            new = float(current["river_discharge_m3_s"])
            trend_pct = round(((new - old) / old) * 100, 1) if old else None

        return {
            "observed_at": current.get("date"),
            "fetched_at": _now_iso(),
            "grid": {
                "latitude": payload.get("latitude"),
                "longitude": payload.get("longitude"),
            },
            "current": {
                "river_discharge_m3_s": current.get("river_discharge_m3_s"),
                "daily_change_pct": trend_pct,
            },
            "series_14d": series,
        }
