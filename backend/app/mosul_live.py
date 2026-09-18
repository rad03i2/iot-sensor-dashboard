from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from .sources.open_meteo import OpenMeteoMosulSource


SOURCE_META = {
    "weather": {
        "name": "Open-Meteo Weather",
        "provider": "Open-Meteo",
        "source_type": "weather_model",
        "label": "نموذج طقس",
        "url": "https://open-meteo.com/",
    },
    "air": {
        "name": "Copernicus CAMS via Open-Meteo",
        "provider": "Copernicus CAMS / Open-Meteo",
        "source_type": "atmospheric_model",
        "label": "نموذج جودة هواء",
        "url": "https://open-meteo.com/en/docs/air-quality-api",
    },
    "river": {
        "name": "GloFAS v4 via Open-Meteo",
        "provider": "GloFAS / Open-Meteo",
        "source_type": "hydrological_model",
        "label": "نموذج هيدرولوجي",
        "url": "https://open-meteo.com/en/docs/flood-api",
    },
}

WEATHER_AR = {
    0: "صحو", 1: "صحو غالباً", 2: "غائم جزئياً", 3: "غائم",
    45: "ضباب", 48: "ضباب متجمد", 51: "رذاذ خفيف", 53: "رذاذ",
    55: "رذاذ كثيف", 61: "مطر خفيف", 63: "مطر", 65: "مطر غزير",
    71: "ثلج خفيف", 73: "ثلج", 75: "ثلج غزير", 80: "زخات خفيفة",
    81: "زخات", 82: "زخات غزيرة", 95: "عاصفة رعدية",
    96: "عاصفة رعدية مع برد", 99: "عاصفة رعدية شديدة",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _aqi_label(value: Any) -> str:
    if value is None:
        return "غير متاح"
    value = float(value)
    if value <= 50:
        return "جيد"
    if value <= 100:
        return "متوسط"
    if value <= 150:
        return "غير صحي للفئات الحساسة"
    if value <= 200:
        return "غير صحي"
    if value <= 300:
        return "غير صحي جداً"
    return "خطر"


def _section_error(previous: dict[str, Any] | None, error: Exception) -> dict[str, Any]:
    if previous and previous.get("data"):
        stale = deepcopy(previous)
        stale["status"] = "stale"
        stale["stale"] = True
        stale["error"] = str(error)[:240]
        return stale
    return {
        "status": "unavailable",
        "stale": True,
        "fetched_at": None,
        "data": None,
        "error": str(error)[:240],
    }


class MosulLiveService:
    def __init__(
        self,
        latitude: float,
        longitude: float,
        timezone_name: str,
        timeout_seconds: float,
    ) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.timezone_name = timezone_name
        self.source = OpenMeteoMosulSource(
            latitude=latitude,
            longitude=longitude,
            timezone_name=timezone_name,
            timeout_seconds=timeout_seconds,
        )
        self._lock = asyncio.Lock()
        self._sections: dict[str, dict[str, Any]] = {}
        self._last_refresh: str | None = None

    async def refresh(self) -> dict[str, Any]:
        async with self._lock:
            results = await asyncio.gather(
                self.source.weather(),
                self.source.air_quality(),
                self.source.tigris_discharge(),
                return_exceptions=True,
            )
            for key, result in zip(("weather", "air", "river"), results):
                if isinstance(result, Exception):
                    self._sections[key] = _section_error(
                        self._sections.get(key), result
                    )
                else:
                    self._sections[key] = {
                        "status": "ok",
                        "stale": False,
                        "fetched_at": result.get("fetched_at"),
                        "data": result,
                        "error": None,
                    }
            self._last_refresh = _now()
            return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        weather = deepcopy(self._sections.get("weather") or {})
        air = deepcopy(self._sections.get("air") or {})
        river = deepcopy(self._sections.get("river") or {})

        for key, section in (("weather", weather), ("air", air), ("river", river)):
            section["source"] = SOURCE_META[key]

        payload = {
            "project": "EcoPulse Mosul",
            "city": {
                "name_ar": "الموصل",
                "name_en": "Mosul",
                "governorate_ar": "نينوى",
                "country_ar": "العراق",
                "latitude": self.latitude,
                "longitude": self.longitude,
                "timezone": self.timezone_name,
            },
            "generated_at": _now(),
            "last_refresh": self._last_refresh,
            "mode": "real_external_sources",
            "weather": weather,
            "air": air,
            "river": river,
        }
        payload["alerts"] = self._alerts(payload)
        payload["brief_ar"] = self._brief(payload)
        return payload

    @staticmethod
    def _alerts(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        air = ((snapshot.get("air") or {}).get("data") or {}).get("current") or {}
        weather = ((snapshot.get("weather") or {}).get("data") or {}).get("current") or {}
        river = ((snapshot.get("river") or {}).get("data") or {}).get("current") or {}

        aqi = air.get("us_aqi")
        if aqi is not None and float(aqi) > 100:
            severity = "critical" if float(aqi) > 150 else "warning"
            alerts.append(
                {
                    "severity": severity,
                    "icon": "🌫️",
                    "title": "ارتفاع مؤشر جودة الهواء النموذجي",
                    "message": (
                        f"US AQI = {round(float(aqi))} ({_aqi_label(aqi)}). "
                        "المصدر CAMS وليس محطة أرضية."
                    ),
                    "official": False,
                }
            )

        temperature = weather.get("temperature_c")
        if temperature is not None and float(temperature) >= 40:
            alerts.append(
                {
                    "severity": "warning",
                    "icon": "🌡️",
                    "title": "حرارة مرتفعة",
                    "message": (
                        f"درجة الحرارة النموذجية الحالية تقارب "
                        f"{float(temperature):.1f}°C."
                    ),
                    "official": False,
                }
            )

        river_change = river.get("daily_change_pct")
        if river_change is not None and abs(float(river_change)) >= 15:
            direction = "ارتفاع" if float(river_change) > 0 else "انخفاض"
            alerts.append(
                {
                    "severity": "info",
                    "icon": "🌊",
                    "title": f"{direction} في تصريف دجلة النموذجي",
                    "message": (
                        f"التغير اليومي المقدر {float(river_change):+.1f}% وفق "
                        "GloFAS؛ ليس قياس محطة نهرية محلية."
                    ),
                    "official": False,
                }
            )

        if not alerts:
            alerts.append(
                {
                    "severity": "info",
                    "icon": "●",
                    "title": "لا توجد تنبيهات رقمية بارزة",
                    "message": (
                        "المرصد مستمر في تحديث الطقس والهواء ودجلة "
                        "من المصادر الخارجية."
                    ),
                    "official": False,
                }
            )
        return alerts[:4]

    @staticmethod
    def _brief(snapshot: dict[str, Any]) -> str:
        weather = ((snapshot.get("weather") or {}).get("data") or {}).get("current") or {}
        air = ((snapshot.get("air") or {}).get("data") or {}).get("current") or {}
        river = ((snapshot.get("river") or {}).get("data") or {}).get("current") or {}

        parts: list[str] = []
        temp = weather.get("temperature_c")
        humidity = weather.get("humidity_pct")
        code = weather.get("weather_code")
        if temp is not None:
            condition = WEATHER_AR.get(code, "حالة جوية متغيرة")
            text = (
                f"الطقس في الموصل {condition} ودرجة الحرارة نحو "
                f"{float(temp):.1f}°C"
            )
            if humidity is not None:
                text += f" مع رطوبة {round(float(humidity))}%"
            parts.append(text + ".")

        aqi = air.get("us_aqi")
        pm25 = air.get("pm25_ug_m3")
        if aqi is not None:
            text = (
                f"مؤشر جودة الهواء الأميركي وفق نموذج CAMS هو "
                f"{round(float(aqi))} ({_aqi_label(aqi)})"
            )
            if pm25 is not None:
                text += f"، وPM2.5 نحو {float(pm25):.1f} µg/m³"
            parts.append(text + ".")

        discharge = river.get("river_discharge_m3_s")
        if discharge is not None:
            parts.append(
                f"نموذج GloFAS يقدّر تصريف دجلة قرب خلية الموصل بنحو "
                f"{float(discharge):.1f} م³/ث، وهو تقدير هيدرولوجي "
                "وليس قياساً أرضياً."
            )

        if not parts:
            return "جارٍ انتظار أول تحديث ناجح من المصادر البيئية الخارجية."
        return " ".join(parts)
