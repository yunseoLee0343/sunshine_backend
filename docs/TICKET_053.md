# TICKET-053: MQTT Sensor to UI Visibility

## Overview

Connects the MQTT ingest pipeline to the UI-facing environment API by triggering
snapshot aggregation after each successful sensor reading insert.

## MQTT Topic Formats

Two topic shapes are accepted. Both must carry a matching `device_id` in the payload.

| Shape | Example |
|---|---|
| `sensor/readings/{device_id}` | `sensor/readings/rpi-edge-node-01` |
| `sunshine/{device_id}/readings` | `sunshine/rpi-edge-node-01/readings` |

## Sensor-to-UI Flow

```
MQTT publish
  -> mqtt-ingest worker (subscribes both topic shapes)
  -> MqttSensorIngestService.process()
     -> parse_device_id(topic)           # accepts both shapes
     -> JSON decode + Pydantic validate
     -> device_id cross-check
     -> SensorIngestService.ingest()     # INSERT sensor_readings, returns plant_id
     -> SnapshotService.aggregate(plant_id)  # upsert latest/24h/7d snapshots
  -> MqttIngestResult(outcome=inserted, snapshot_refreshed=true)

GET /plants/{plant_id}/environment?user_id={user_id}
  -> EnvironmentDetailService.get_detail()
     -> read environment_snapshots WHERE window=latest
     -> fallback: read latest sensor_readings row (no DB write)
  -> EnvironmentDetailResponse(latest=WindowSnapshot(...))
```

## Snapshot Windows

After every successful MQTT insert, three windows are refreshed:

- `latest` — single most recent reading at or before `now`
- `24h` — aggregate of readings in [now-24h, now]
- `7d` — aggregate of readings in [now-7d, now]

The `1h` window is **not** written; the demo seed was corrected from `"1h"` to `"latest"`.

## Fallback Behaviour

If `environment_snapshots.latest` is missing for a plant, `EnvironmentDetailService`
falls back to the most recent row in `sensor_readings` and synthesises a `WindowSnapshot`
with `source="raw_sensor_reading_fallback"`. No DB writes occur in the fallback path.

## Smoke Commands

```bash
# Start services
docker compose up -d postgres mqtt backend mqtt-ingest

# Publish legacy topic
mosquitto_pub -h localhost -p 1883 \
  -t sensor/readings/device-001 \
  -m '{"reading_id":"smoke-001","device_id":"device-001","plant_id":"plant-001","measured_at":"2026-05-14T12:00:00+09:00","temperature_c":24.2,"humidity_pct":51.0,"light_lux":830.0,"soil_moisture_pct":38.0}'

# Publish sunshine topic
mosquitto_pub -h localhost -p 1883 \
  -t sunshine/device-001/readings \
  -m '{"reading_id":"smoke-002","device_id":"device-001","plant_id":"plant-001","measured_at":"2026-05-14T12:05:00+09:00","temperature_c":24.4,"humidity_pct":50.0,"light_lux":840.0,"soil_moisture_pct":37.0}'

# Verify snapshots
psql -c "SELECT plant_id, window, soil_moisture_avg_pct FROM environment_snapshots WHERE window IN ('latest','24h','7d') ORDER BY window;"

# Verify no 1h rows
psql -c "SELECT COUNT(*) FROM environment_snapshots WHERE window = '1h';"

# Verify API
curl -fsS "http://localhost:8000/plants/{plant_id}/environment?user_id={user_id}" | jq '.latest'
```
