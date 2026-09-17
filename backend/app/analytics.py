from .models import EnvironmentalReading


def estimated_aqi_from_pm25(pm25: float) -> int:
    """Simulation-oriented AQI estimate.

    This intentionally uses a smooth approximation for the virtual system and is
    not presented as an official regulatory AQI calculation.
    """
    if pm25 <= 12:
        score = pm25 / 12 * 50
    elif pm25 <= 35.4:
        score = 50 + (pm25 - 12) / 23.4 * 50
    elif pm25 <= 55.4:
        score = 100 + (pm25 - 35.4) / 20 * 50
    elif pm25 <= 150.4:
        score = 150 + (pm25 - 55.4) / 95 * 50
    elif pm25 <= 250.4:
        score = 200 + (pm25 - 150.4) / 100 * 100
    else:
        score = 300 + min((pm25 - 250.4) / 250 * 200, 200)
    return max(0, min(500, round(score)))


def environmental_health_score(*, pm25: float, co2: float, noise: float, temperature: float, humidity: float) -> float:
    penalty = 0.0
    penalty += min(pm25 / 120 * 38, 38)
    penalty += min(max(co2 - 420, 0) / 1600 * 22, 22)
    penalty += min(max(noise - 45, 0) / 55 * 18, 18)
    penalty += min(abs(temperature - 24) / 20 * 12, 12)
    penalty += min(abs(humidity - 50) / 50 * 10, 10)
    return round(max(0.0, min(100.0, 100.0 - penalty)), 1)


def summarize(readings: list[EnvironmentalReading]) -> dict:
    if not readings:
        return {"stations": 0, "average_health_score": None, "worst_station": None, "best_station": None}
    best = max(readings, key=lambda item: item.environmental_health_score)
    worst = min(readings, key=lambda item: item.environmental_health_score)
    average = round(sum(item.environmental_health_score for item in readings) / len(readings), 1)
    return {
        "stations": len(readings),
        "average_health_score": average,
        "best_station": {"id": best.station_id, "name": best.station_name, "score": best.environmental_health_score},
        "worst_station": {"id": worst.station_id, "name": worst.station_name, "score": worst.environmental_health_score},
    }
