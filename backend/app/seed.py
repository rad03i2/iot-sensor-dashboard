from datetime import datetime, timedelta, timezone

from .history import HistoryStore
from .simulator import EnvironmentalSimulator


def seed_demo_history(
    store: HistoryStore,
    hours: int = 24,
    step_minutes: int = 10,
) -> int:
    """Populate a new database with synthetic historical context.

    The timeline intentionally contains clearly simulated scenario windows so
    the dashboard has meaningful history on first launch. Existing databases
    are never overwritten.
    """
    if store.count() > 0:
        return 0

    simulator = EnvironmentalSimulator(seed=20260918)
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    total_steps = max(1, int(hours * 60 / step_minutes))
    inserted = 0

    for index in range(total_steps, -1, -1):
        timestamp = now - timedelta(minutes=index * step_minutes)
        age_hours = (now - timestamp).total_seconds() / 3600

        if 15 <= age_hours <= 18:
            simulator.set_scenario("dust_storm", 0.9)
        elif 5 <= age_hours <= 7:
            simulator.set_scenario("traffic_surge", 0.85)
        elif 1.5 <= age_hours <= 2.5:
            simulator.set_scenario("industrial_event", 0.65)
        else:
            simulator.set_scenario("baseline", 1.0)

        inserted += store.insert_many(simulator.tick(now=timestamp))

    return inserted
