from datetime import datetime, timedelta, timezone

from backend.app.history import HistoryStore
from backend.app.simulator import EnvironmentalSimulator


def test_history_store_round_trip(tmp_path):
    store = HistoryStore(str(tmp_path / "history.db"))
    simulator = EnvironmentalSimulator(seed=7)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    readings = simulator.tick(now=now)

    inserted = store.insert_many(readings)
    assert inserted == 5
    assert store.count() == 5

    series = store.series("industrial", "pm25_ug_m3", minutes=10)
    assert len(series) == 1
    assert series[0]["value"] >= 0


def test_playback_groups_station_tick_into_one_frame(tmp_path):
    store = HistoryStore(str(tmp_path / "history.db"))
    simulator = EnvironmentalSimulator(seed=11)
    now = datetime.now(timezone.utc).replace(microsecond=0)

    store.insert_many(simulator.tick(now=now - timedelta(minutes=1)))
    store.insert_many(simulator.tick(now=now))

    frames = store.playback(minutes=5, max_frames=10)
    assert len(frames) == 2
    assert all(len(frame["readings"]) == 5 for frame in frames)


def test_invalid_metric_rejected(tmp_path):
    store = HistoryStore(str(tmp_path / "history.db"))
    try:
        store.series("traffic", "DROP TABLE readings", minutes=10)
    except ValueError:
        pass
    else:
        raise AssertionError("Unsupported metrics must be rejected")
