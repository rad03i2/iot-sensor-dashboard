import asyncio
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .adafruit import AdafruitPublisher
from .alerts import detect_alerts
from .analytics import summarize
from .config import settings
from .history import METRICS, HistoryStore
from .models import Alert, EnvironmentalReading, ScenarioName, ScenarioRequest
from .mosul_live import MosulLiveService
from .seed import seed_demo_history
from .simulator import STATIONS, EnvironmentalSimulator

simulator = EnvironmentalSimulator()
publisher = AdafruitPublisher()
history = HistoryStore(settings.database_path)
mosul_live = MosulLiveService(
    latitude=settings.mosul_latitude,
    longitude=settings.mosul_longitude,
    timezone_name=settings.mosul_timezone,
    timeout_seconds=settings.upstream_timeout_seconds,
)

latest: dict[str, EnvironmentalReading] = {}
alert_history: deque[Alert] = deque(maxlen=300)
clients: set[WebSocket] = set()
simulation_task: asyncio.Task | None = None
mosul_task: asyncio.Task | None = None


async def broadcast(payload: dict) -> None:
    disconnected: list[WebSocket] = []
    for client in clients:
        try:
            await client.send_json(payload)
        except Exception:
            disconnected.append(client)
    for client in disconnected:
        clients.discard(client)


async def perform_tick() -> list[EnvironmentalReading]:
    readings = simulator.tick()
    new_alerts: list[Alert] = []

    for reading in readings:
        latest[reading.station_id] = reading
        station_alerts = detect_alerts(reading)
        new_alerts.extend(station_alerts)
        for alert in station_alerts:
            alert_history.appendleft(alert)

    await asyncio.to_thread(history.insert_many, readings)
    if readings:
        await publisher.publish(readings[0])

    await broadcast(
        {
            "type": "environment_update",
            "scenario": simulator.scenario,
            "readings": [item.model_dump(mode="json") for item in readings],
            "alerts": [item.model_dump(mode="json") for item in new_alerts],
            "summary": summarize(readings),
        }
    )
    return readings


async def simulation_loop() -> None:
    prune_counter = 0
    while True:
        await perform_tick()
        prune_counter += 1
        if prune_counter >= 720:
            await asyncio.to_thread(history.prune, settings.history_retention_days)
            prune_counter = 0
        await asyncio.sleep(max(settings.simulation_interval_seconds, 1.0))


async def mosul_refresh_loop() -> None:
    while True:
        try:
            await mosul_live.refresh()
        except Exception:
            pass
        await asyncio.sleep(max(settings.live_refresh_seconds, 60))


@asynccontextmanager
async def lifespan(_: FastAPI):
    global simulation_task, mosul_task

    try:
        await mosul_live.refresh()
    except Exception:
        pass
    mosul_task = asyncio.create_task(mosul_refresh_loop())

    if settings.simulation_enabled:
        if settings.seed_demo_history:
            await asyncio.to_thread(
                seed_demo_history,
                history,
                settings.demo_history_hours,
                settings.demo_history_step_minutes,
            )
        await perform_tick()
        simulation_task = asyncio.create_task(simulation_loop())

    yield

    for task in (simulation_task, mosul_task):
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="EcoPulse Mosul API",
    version="0.3.0",
    description=(
        "Mosul-focused environmental public wallboard. Live sections use external "
        "weather, atmospheric and hydrological models with explicit provenance."
    ),
    lifespan=lifespan,
)

frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
async def dashboard():
    index = frontend_dir / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"name": settings.app_name, "docs": "/docs"}


@app.get("/health")
async def health():
    snapshot = mosul_live.snapshot()
    return {
        "status": "ok",
        "service": settings.app_name,
        "mode": "mosul_live_wallboard",
        "simulation_enabled": settings.simulation_enabled,
        "sources": {
            key: (snapshot.get(key) or {}).get("status")
            for key in ("weather", "air", "river")
        },
        "last_refresh": snapshot.get("last_refresh"),
        "database": "sqlite",
    }


@app.get("/api/mosul/live")
async def mosul_snapshot():
    return mosul_live.snapshot()


@app.post("/api/mosul/refresh")
async def mosul_manual_refresh():
    return await mosul_live.refresh()


@app.get("/api/stations")
async def stations():
    return STATIONS


@app.get("/api/metrics")
async def metrics():
    return METRICS


@app.get("/api/latest")
async def all_latest():
    return list(latest.values())


@app.get("/api/stations/{station_id}/latest")
async def station_latest(station_id: str):
    reading = latest.get(station_id)
    if not reading:
        raise HTTPException(status_code=404, detail="Station not found")
    return reading


@app.get("/api/alerts")
async def alerts(limit: int = 50):
    return list(alert_history)[: max(1, min(limit, 300))]


@app.get("/api/summary")
async def summary():
    return summarize(list(latest.values())) | {"scenario": simulator.scenario}


@app.get("/api/history")
async def history_series(
    station_id: str,
    metric: str = "pm25_ug_m3",
    minutes: int = Query(default=360, ge=1, le=43200),
    limit: int = Query(default=1200, ge=10, le=5000),
):
    if station_id not in {station.id for station in STATIONS}:
        raise HTTPException(status_code=404, detail="Station not found")
    if metric not in METRICS:
        raise HTTPException(
            status_code=400,
            detail={"message": "Unsupported metric", "supported": list(METRICS)},
        )
    points = await asyncio.to_thread(
        history.series, station_id, metric, minutes, limit
    )
    return {
        "station_id": station_id,
        "metric": metric,
        "meta": METRICS[metric],
        "window_minutes": minutes,
        "points": points,
    }


@app.get("/api/history/overview")
async def history_overview(
    minutes: int = Query(default=1440, ge=1, le=43200),
):
    return await asyncio.to_thread(history.overview, minutes)


@app.get("/api/playback")
async def playback(
    minutes: int = Query(default=1440, ge=10, le=43200),
    max_frames: int = Query(default=144, ge=10, le=720),
):
    frames = await asyncio.to_thread(history.playback, minutes, max_frames)
    return {
        "window_minutes": minutes,
        "frames": frames,
        "source_notice": (
            "Legacy playback contains simulated observations unless a reading "
            "explicitly declares another source."
        ),
    }


@app.post("/api/simulation/tick")
async def manual_tick():
    if not settings.simulation_enabled:
        raise HTTPException(status_code=409, detail="Simulation mode is disabled")
    return await perform_tick()


@app.post("/api/scenarios/{scenario}")
async def set_scenario(scenario: ScenarioName, request: ScenarioRequest):
    if not settings.simulation_enabled:
        raise HTTPException(status_code=409, detail="Simulation mode is disabled")
    simulator.set_scenario(scenario, request.intensity)
    readings = await perform_tick()
    return {
        "scenario": scenario,
        "intensity": request.intensity,
        "readings": readings,
        "message": "Scenario applied to the legacy digital-twin lab.",
    }


@app.websocket("/ws/environment")
async def environment_stream(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.discard(websocket)
