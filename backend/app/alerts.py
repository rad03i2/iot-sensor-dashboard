from datetime import datetime, timezone
from uuid import uuid4

from .models import Alert, EnvironmentalReading


def detect_alerts(reading: EnvironmentalReading) -> list[Alert]:
    alerts: list[Alert] = []

    rules = [
        ("pm25_ug_m3", reading.pm25_ug_m3, 55.0, 120.0, "PM2.5 elevation"),
        ("co2_ppm", reading.co2_ppm, 1000.0, 1800.0, "CO2 elevation"),
        ("noise_db", reading.noise_db, 75.0, 90.0, "High noise level"),
        ("temperature_c", reading.temperature_c, 40.0, 48.0, "High temperature"),
    ]

    for metric, value, warning, critical, title in rules:
        if value < warning:
            continue
        severity = "critical" if value >= critical else "warning"
        alerts.append(
            Alert(
                id=str(uuid4()),
                station_id=reading.station_id,
                created_at=datetime.now(timezone.utc),
                severity=severity,
                metric=metric,
                value=value,
                title=title,
                message=f"{reading.station_name}: {metric} reached {value} during {reading.scenario} scenario.",
            )
        )
    return alerts
