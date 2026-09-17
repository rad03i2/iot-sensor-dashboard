from backend.app.simulator import STATIONS, EnvironmentalSimulator


def test_tick_returns_all_stations():
    simulator = EnvironmentalSimulator()
    readings = simulator.tick()
    assert len(readings) == len(STATIONS) == 5
    assert {item.station_id for item in readings} == {station.id for station in STATIONS}


def test_readings_stay_inside_sane_bounds():
    simulator = EnvironmentalSimulator()
    for _ in range(20):
        for reading in simulator.tick():
            assert -20 <= reading.temperature_c <= 60
            assert 5 <= reading.humidity_pct <= 100
            assert reading.pm25_ug_m3 >= 0
            assert reading.pm10_ug_m3 >= reading.pm25_ug_m3
            assert reading.co2_ppm >= 350
            assert 25 <= reading.noise_db <= 120
            assert 0 <= reading.estimated_aqi <= 500
            assert 0 <= reading.environmental_health_score <= 100


def test_dust_storm_increases_particulate_pressure():
    simulator = EnvironmentalSimulator()
    baseline = simulator.tick()
    baseline_pm10 = sum(item.pm10_ug_m3 for item in baseline) / len(baseline)
    simulator.set_scenario("dust_storm", 1.5)
    for _ in range(8):
        storm = simulator.tick()
    storm_pm10 = sum(item.pm10_ug_m3 for item in storm) / len(storm)
    assert storm_pm10 > baseline_pm10
