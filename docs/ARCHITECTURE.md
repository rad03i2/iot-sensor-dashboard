# EcoPulse AI Architecture

## Milestone 1

```text
Environmental Simulator
        │
        ├── correlated station profiles
        ├── scenario engine
        └── provenance = simulated
        │
        ▼
FastAPI Application
        │
        ├── REST endpoints
        ├── WebSocket stream
        ├── alert rules
        ├── environmental analytics
        └── optional Adafruit IO publisher
        │
        ▼
Live Web Dashboard
```

## Design principles

1. **Transparent provenance** — synthetic data must never masquerade as physical measurements.
2. **Replaceable data sources** — simulated, external API and physical sensor readings should converge on one data model.
3. **Fault isolation** — optional cloud integrations cannot stop the local monitoring engine.
4. **Progressive scientific rigor** — regulatory standards and health claims are not hard-coded without versioned sources and documentation.
5. **Expert + public UX** — future UI layers will expose both simple summaries and raw technical evidence.

## Planned architecture

```text
Physical Sensors ─┐
External APIs ────┼─> Ingestion Gateway ─> Validation ─> Time-Series Store
Simulator ────────┘                               │
                                                  ├─> Analytics
                                                  ├─> Data Quality
                                                  ├─> Anomaly Detection
                                                  ├─> Forecasting
                                                  └─> AI Explanation
                                                           │
                         ┌─────────────────────────────────┼──────────────┐
                         ▼                                 ▼              ▼
                    Public Dashboard                  Expert Lab      Reports/API
```

## Milestone 2 targets

- PostgreSQL/TimescaleDB persistence
- Historical charts and playback
- Geospatial station map and heatmaps
- Versioned environmental standards profiles
- Data quality scoring and missing-data diagnostics
- Alert deduplication and lifecycle tracking
- Authentication and role separation

## Milestone 3 targets

- Statistical anomaly detection
- Multi-horizon forecasting with evaluation metrics
- Explainability layer
- AI analyst grounded strictly in project data and documented standards
- Automated bilingual environmental reports
- Real ESP32 sensor adapter
