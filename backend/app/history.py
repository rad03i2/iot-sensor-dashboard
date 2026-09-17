from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .models import EnvironmentalReading


METRICS = {
    "temperature_c": {"label": "Temperature", "unit": "°C"},
    "humidity_pct": {"label": "Humidity", "unit": "%"},
    "pm25_ug_m3": {"label": "PM2.5", "unit": "µg/m³"},
    "pm10_ug_m3": {"label": "PM10", "unit": "µg/m³"},
    "co2_ppm": {"label": "CO₂", "unit": "ppm"},
    "noise_db": {"label": "Noise", "unit": "dB"},
    "estimated_aqi": {"label": "Estimated AQI", "unit": ""},
    "environmental_health_score": {"label": "Environmental health", "unit": "/100"},
}

_COLUMNS = (
    "station_id",
    "station_name",
    "timestamp",
    "source",
    "scenario",
    "temperature_c",
    "humidity_pct",
    "pm25_ug_m3",
    "pm10_ug_m3",
    "co2_ppm",
    "noise_db",
    "estimated_aqi",
    "environmental_health_score",
)


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class HistoryStore:
    """Small, durable time-series store for the demo.

    SQLite is intentionally the default so the project runs on a laptop or in a
    single Docker container with zero external services. The API is isolated
    behind this class so a TimescaleDB adapter can replace it later.
    """

    def __init__(self, database_path: str) -> None:
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    station_id TEXT NOT NULL,
                    station_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    scenario TEXT NOT NULL,
                    temperature_c REAL NOT NULL,
                    humidity_pct REAL NOT NULL,
                    pm25_ug_m3 REAL NOT NULL,
                    pm10_ug_m3 REAL NOT NULL,
                    co2_ppm REAL NOT NULL,
                    noise_db REAL NOT NULL,
                    estimated_aqi INTEGER NOT NULL,
                    environmental_health_score REAL NOT NULL,
                    UNIQUE(station_id, timestamp)
                );

                CREATE INDEX IF NOT EXISTS idx_readings_timestamp
                    ON readings(timestamp);
                CREATE INDEX IF NOT EXISTS idx_readings_station_timestamp
                    ON readings(station_id, timestamp);
                """
            )

    def count(self) -> int:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM readings").fetchone()
            return int(row["count"])

    def insert_many(self, readings: Iterable[EnvironmentalReading]) -> int:
        rows = []
        for reading in readings:
            data = reading.model_dump(mode="json")
            rows.append(tuple(data[column] for column in _COLUMNS))
        if not rows:
            return 0

        placeholders = ",".join("?" for _ in _COLUMNS)
        columns = ",".join(_COLUMNS)
        with self._lock, self._connect() as connection:
            before = connection.total_changes
            connection.executemany(
                f"INSERT OR IGNORE INTO readings ({columns}) VALUES ({placeholders})",
                rows,
            )
            return connection.total_changes - before

    def prune(self, retention_days: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, retention_days))
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM readings WHERE timestamp < ?",
                (_utc_iso(cutoff),),
            )
            return cursor.rowcount

    def series(
        self,
        station_id: str,
        metric: str,
        minutes: int,
        limit: int = 1200,
    ) -> list[dict]:
        if metric not in METRICS:
            raise ValueError(f"Unsupported metric: {metric}")
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=max(1, minutes))
        safe_limit = max(10, min(limit, 5000))
        query = f"""
            SELECT timestamp, {metric} AS value, scenario, source
            FROM readings
            WHERE station_id = ? AND timestamp >= ?
            ORDER BY timestamp ASC
            LIMIT ?
        """
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                query, (station_id, _utc_iso(cutoff), safe_limit)
            ).fetchall()
        return [dict(row) for row in rows]

    def playback(self, minutes: int, max_frames: int = 180) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=max(1, minutes))
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT station_id, station_name, timestamp, source, scenario,
                       temperature_c, humidity_pct, pm25_ug_m3, pm10_ug_m3,
                       co2_ppm, noise_db, estimated_aqi,
                       environmental_health_score
                FROM readings
                WHERE timestamp >= ?
                ORDER BY timestamp ASC, station_id ASC
                """,
                (_utc_iso(cutoff),),
            ).fetchall()

        frames: list[dict] = []
        current_ts: str | None = None
        current: list[dict] = []
        for row in rows:
            item = dict(row)
            timestamp = item["timestamp"]
            if current_ts is not None and timestamp != current_ts:
                frames.append({"timestamp": current_ts, "readings": current})
                current = []
            current_ts = timestamp
            current.append(item)
        if current_ts is not None:
            frames.append({"timestamp": current_ts, "readings": current})

        if len(frames) <= max_frames:
            return frames

        stride = (len(frames) - 1) / (max_frames - 1)
        indexes = sorted({round(i * stride) for i in range(max_frames)})
        return [frames[index] for index in indexes]

    def overview(self, minutes: int) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=max(1, minutes))
        with self._lock, self._connect() as connection:
            station_rows = connection.execute(
                """
                SELECT station_id, station_name,
                       ROUND(AVG(environmental_health_score), 1) AS avg_health,
                       ROUND(AVG(pm25_ug_m3), 1) AS avg_pm25,
                       ROUND(MAX(pm25_ug_m3), 1) AS max_pm25,
                       ROUND(AVG(co2_ppm), 1) AS avg_co2,
                       ROUND(AVG(noise_db), 1) AS avg_noise,
                       COUNT(*) AS samples
                FROM readings
                WHERE timestamp >= ?
                GROUP BY station_id, station_name
                ORDER BY avg_health DESC
                """,
                (_utc_iso(cutoff),),
            ).fetchall()
            row = connection.execute(
                """
                SELECT COUNT(*) AS samples,
                       COUNT(DISTINCT station_id) AS stations,
                       MIN(timestamp) AS from_timestamp,
                       MAX(timestamp) AS to_timestamp
                FROM readings
                WHERE timestamp >= ?
                """,
                (_utc_iso(cutoff),),
            ).fetchone()

        return {
            "window_minutes": minutes,
            "samples": int(row["samples"] or 0),
            "stations": int(row["stations"] or 0),
            "from_timestamp": row["from_timestamp"],
            "to_timestamp": row["to_timestamp"],
            "station_summary": [dict(item) for item in station_rows],
        }
