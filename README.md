# EcoPulse Mosul

> مرصد الموصل البيئي المباشر — Mosul Live Environmental Observatory

EcoPulse Mosul is a public, one-screen environmental wallboard designed for a continuous 1920×1080 OBS/Facebook Live broadcast. The public view focuses on Mosul, Nineveh, Iraq and uses real external data services instead of synthetic values.

## What is live now

- Mosul weather and five-day forecast from Open-Meteo
- PM2.5, PM10, US/EU AQI, NO₂, SO₂, O₃, dust, UV and AOD from Copernicus CAMS Global via Open-Meteo
- Tigris river-discharge estimate from GloFAS v4 via Open-Meteo Flood
- OpenStreetMap city map
- Automatic Arabic environmental brief generated deterministically from the fetched data
- Source-health monitoring, stale-data fallback and automatic retry
- One-screen RTL wallboard that requires no scrolling at 1920×1080
- FastAPI backend with a cached live snapshot endpoint

## Scientific transparency

Not all values are ground observations.

| Section | Public label | Meaning |
|---|---|---|
| Weather | Weather model | Forecast/model data for the Mosul coordinate |
| Air & dust | CAMS atmospheric model | Gridded atmospheric model, not a Mosul ground sensor |
| Tigris | GloFAS hydrological model | River-discharge model cell near Mosul, not a local gauging station |
| Map | OpenStreetMap | Geographic basemap |

The wallboard never presents CAMS or GloFAS values as calibrated local regulatory measurements.

## Run on Windows

    git switch feature/ecopulse-ai-foundation
    py -3.12 -m venv .venv
    .venv\Scripts\activate.bat
    pip install -r requirements.txt
    uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

Open the wallboard at http://127.0.0.1:8000/ and API docs at http://127.0.0.1:8000/docs.

For OBS, use Window Capture or Browser Source at 1920×1080. The page is designed to fit in one frame without scrolling.

## Update behavior

The backend refreshes upstream sources every 5 minutes by default. The browser reads the locally cached snapshot every 30 seconds. If an upstream source fails, the last successful data for that section remains visible and is marked as stale rather than disappearing.

## Legacy virtual lab

The original digital-twin simulator remains in the repository for research/testing but is disabled by default and is no longer used on the public Mosul wallboard. Set SIMULATION_ENABLED=true only when you intentionally want the synthetic lab.

## Current API

    GET  /health
    GET  /api/mosul/live
    POST /api/mosul/refresh

Legacy lab endpoints remain available for research.

## Next live-source milestones

1. NASA FIRMS active-fire/thermal-anomaly layer for Nineveh
2. NASA GIBS satellite imagery rotation
3. Rain/radar layer where coverage is available
4. University of Mosul environmental-research feed
5. Curated Mosul/Nineveh environmental news ticker
6. Sentinel-2 vegetation/NDVI monitoring
7. Real MQTT/ESP32 ground sensors when hardware becomes available

## Data-source links

- Open-Meteo: https://open-meteo.com/
- Air Quality API: https://open-meteo.com/en/docs/air-quality-api
- Flood API / GloFAS: https://open-meteo.com/en/docs/flood-api
- OpenStreetMap: https://www.openstreetmap.org/

## Official project links

- Portfolio: https://rdwan.dev
- Repository: https://github.com/rad03i2/iot-sensor-dashboard
