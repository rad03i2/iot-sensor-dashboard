import asyncio
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .adafruit import AdafruitPublisher
from .alerts import detect_alerts
from .analytics import summarize
from .config import settings
from .models import Alert, EnvironmentalReading, ScenarioName, ScenarioRequest
from .simulator import STATIONS, EnvironmentalSimulator

simulator = EnvironmentalSimulator()
publisher = AdafruitPublisher()
latest: dict[str, EnvironmentalReading] = {}
alert_history: deque[Alert] = deque(maxlen=200)
clients: set[WebSocket] = set()
loop_task: asyncio.Task | None = None


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
    while True:
        await perform_tick()
        await asyncio.sleep(max(settings.simulation_interval_seconds, 1.0))


@asynccontextmanager
async def lifespan(_: FastAPI):
    global loop_task
    await perform_tick()
    loop_task = asyncio.create_task(simulation_loop())
    yield
    if loop_task:
        loop_task.cancel()
        try:
            await loop_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="EcoPulse AI API",
    version="0.1.0",
    description="Virtual environmental intelligence and digital-twin platform.",
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
    return {
        "status": "ok",
        "service": settings.app_name,
        "scenario": simulator.scenario,
        "stations": len(STATIONS),
        "source": "simulated",
    }


@app.get("/api/stations")
async def stations():
    return STATIONS


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
    return list(alert_history)[: max(1, min(limit, 200))]


@app.get("/api/summary")
async def summary():
    return summarize(list(latest.values())) | {"scenario": simulator.scenario}


@app.post("/api/simulation/tick")
async def manual_tick():
    return await perform_tick()


@app.post("/api/scenarios/{scenario}")
async def set_scenario(scenario: ScenarioName, request: ScenarioRequest):
    simulator.set_scenario(scenario, request.intensity)
    readings = await perform_tick()
    return {
        "scenario": scenario,
        "intensity": request.intensity,
        "readings": readings,
        "message": "Scenario applied to the virtual environmental network.",
    }


@app.websocket("/ws/environment")
async def environment_stream(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        if latest:
            await websocket.send_json(
                {
                    "type": "environment_update",
                    "scenario": simulator.scenario,
                    "readings": [item.model_dump(mode="json") for item in latest.values()],
                    "alerts": [],
                    "summary": summarize(list(latest.values())),
                }
            )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.discard(websocket)
