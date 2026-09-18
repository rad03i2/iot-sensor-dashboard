from backend.app.mosul_live import MosulLiveService


def test_initial_snapshot_declares_real_external_source_mode():
    service = MosulLiveService(
        latitude=36.335,
        longitude=43.118889,
        timezone_name="Asia/Baghdad",
        timeout_seconds=1,
    )
    snapshot = service.snapshot()
    assert snapshot["project"] == "EcoPulse Mosul"
    assert snapshot["city"]["name_en"] == "Mosul"
    assert snapshot["mode"] == "real_external_sources"


def test_initial_sources_are_transparent_about_provenance():
    service = MosulLiveService(
        latitude=36.335,
        longitude=43.118889,
        timezone_name="Asia/Baghdad",
        timeout_seconds=1,
    )
    snapshot = service.snapshot()
    assert snapshot["air"]["source"]["source_type"] == "atmospheric_model"
    assert snapshot["river"]["source"]["source_type"] == "hydrological_model"
    assert snapshot["weather"]["source"]["source_type"] == "weather_model"
