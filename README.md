# EcoPulse AI

> Virtual AI Environmental Intelligence & Digital Twin Platform

EcoPulse AI is an environmental monitoring, simulation and historical-intelligence platform. It transforms the original IoT Sensor Dashboard prototype into a multi-station virtual environmental digital twin that works **without physical sensors today**, while keeping a clean migration path to ESP32/Arduino, MQTT and Adafruit IO later.

## What works now

### Milestone 1 — live environmental intelligence

- Five virtual monitoring stations with different environmental profiles
- Correlated simulation for temperature, humidity, PM2.5, PM10, CO₂ and noise
- Scenario engine: baseline, traffic surge, dust storm, industrial event and heat wave
- Environmental health score and explicitly **estimated** AQI
- Automatic warning/critical event detection
- FastAPI REST API + WebSocket live stream
- Optional Adafruit IO publisher
- Docker support and automated tests

### Milestone 2 — history, map and Time Machine

- Durable SQLite time-series storage with WAL mode and indexed station/timestamp queries
- Automatic 24-hour synthetic demo history on a brand-new database
- Configurable retention and persistent Docker data volume
- Historical metric API for every station
- 24-hour network overview and station summaries
- Interactive Leaflet/OpenStreetMap environmental map
- Selectable map layers: PM2.5, PM10, CO₂, noise, temperature and health score
- **Time Machine** playback that replays historical spatial conditions
- Custom in-browser historical trend chart
- Reproducible seeded history generation for first-run demos
- Every observation preserves its provenance (`simulated`, `physical_sensor`, or `external_api`)

## Monitoring stations

| ID | Station | Profile |
|---|---|---|
| residential | Residential District | Urban residential baseline |
| traffic | Traffic Corridor | High traffic exposure |
| industrial | Industrial Zone | Industrial emission influence |
| green | Green Zone | Vegetation-rich low-emission area |
| campus | University Campus | Mixed pedestrian/traffic activity |

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Open:

- Dashboard: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

On first launch, EcoPulse AI creates `data/ecopulse.db` and seeds a transparent synthetic 24-hour timeline so the historical dashboard is immediately useful.

## Docker

```bash
docker compose up --build
```

`./data` is mounted into the container so time-series history survives container restarts.

## Optional Adafruit IO

Copy `.env.example` to `.env` and provide your own credentials locally:

```env
ADAFRUIT_IO_ENABLED=true
ADAFRUIT_IO_USERNAME=your_username
ADAFRUIT_IO_KEY=your_private_key
```

Never commit an Adafruit IO key to GitHub.

## API snapshot

```text
GET  /health
GET  /api/stations
GET  /api/metrics
GET  /api/latest
GET  /api/stations/{station_id}/latest
GET  /api/alerts
GET  /api/summary

GET  /api/history?station_id=industrial&metric=pm25_ug_m3&minutes=1440
GET  /api/history/overview?minutes=1440
GET  /api/playback?minutes=1440&max_frames=180

POST /api/simulation/tick
POST /api/scenarios/{scenario}
WS   /ws/environment
```

Supported historical metrics:

`temperature_c` · `humidity_pct` · `pm25_ug_m3` · `pm10_ug_m3` · `co2_ppm` · `noise_db` · `estimated_aqi` · `environmental_health_score`

## Scientific transparency

The current monitoring network is a **software simulation**. The model contains station profiles, daily cycles, traffic/activity pressure and scenario effects so the variables move coherently rather than as unrelated random numbers.

It is still synthetic. Current values are for software development, education, environmental-engineering demonstrations and digital-twin experiments. They are **not regulatory measurements, medical advice, exposure assessment, or a substitute for calibrated environmental instruments**.

The architecture preserves `source` on every reading so future real sensors and external APIs remain distinguishable from synthetic data.

## Architecture direction

```text
Simulation / future sensors / external APIs
                  │
                  ▼
          FastAPI ingestion layer
                  │
          ┌───────┴────────┐
          ▼                ▼
   SQLite history     Adafruit IO
   (Timescale-ready)   (optional)
          │
          ├──────────► Historical APIs
          ├──────────► Time Machine
          ├──────────► Map / spatial layers
          └──────────► Analytics / future AI
```

SQLite is the zero-dependency local default. The time-series access is isolated behind `HistoryStore`, making a future PostgreSQL/TimescaleDB adapter straightforward.

## Roadmap

Next milestones add:

1. data-quality center and versioned environmental standards,
2. more advanced geospatial heatmaps and event overlays,
3. anomaly detection and multi-horizon forecasting,
4. explainable model outputs and prediction-vs-actual evaluation,
5. grounded AI environmental analyst with Arabic/English reporting,
6. PDF/CSV/JSON report exports,
7. authentication, roles, rate limiting and production observability,
8. MQTT + ESP32/Arduino physical-sensor gateway and calibration metadata.

## Stack

`Python` · `FastAPI` · `Pydantic` · `SQLite` · `WebSocket` · `Leaflet` · `OpenStreetMap` · `Adafruit IO` · `HTML` · `CSS` · `JavaScript` · `Docker` · `Pytest`

## Official links

- Portfolio: https://rdwan.dev
- Original project page: https://rdwan.dev/projects/11-iot-sensor-dashboard.html
