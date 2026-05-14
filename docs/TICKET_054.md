# TICKET-054: Sensor Snapshot Transaction Fix

## Root Cause

`SensorIngestService.ingest()` committed the `sensor_readings` INSERT immediately.
`SnapshotService.aggregate()` then upserted `environment_snapshots` rows — but never
committed. When the session closed, the snapshot upsert was silently rolled back,
leaving the UI read model stale.

## Transaction Ownership

**Rule: services flush; callers commit.**

| Layer | Responsibility |
|---|---|
| `SensorIngestService.ingest()` | INSERT + `session.flush()`. Sets `resolved_plant_id`. |
| `POST /sensor-readings` (REST) | `session.commit()` after flush. `session.rollback()` on error. |
| `MqttSensorIngestService.process()` | Ingest + aggregate, then single `session.commit()`. |
| `SnapshotService.aggregate()` | Upsert + `session.flush()` (no commit). |
| `EnvironmentDetailService` | Read-only. Never writes. |

## MQTT All-or-Nothing Policy

The MQTT path is atomic: sensor insert and snapshot refresh commit together.

```text
MQTT message
  -> SensorIngestService.ingest()   # INSERT, flush only
  -> SnapshotService.aggregate()    # UPSERT, flush only
  -> session.commit()               # single commit, both tables visible
```

If aggregate fails after insert:
  - `session.rollback()` — insert is also rolled back
  - outcome = `error`
  - `snapshot_refreshed = false`

## Stale Snapshot Detection

`EnvironmentDetailService.get_detail()` fetches both the latest snapshot **and**
the latest raw sensor reading. If the raw reading's `measured_at` is newer than the
snapshot's `window_end`, the raw reading is returned as the `latest` response
(`source="raw_sensor_reading_fallback"`). This prevents demo seed values from
blocking real MQTT readings.

```text
GET /plants/{plant_id}/environment
  -> read environment_snapshots.latest
  -> read latest sensor_readings row
  -> if raw.measured_at > snapshot.window_end:
       return raw fallback
     else:
       return snapshot
```

## Smoke SQL

```sql
-- Check raw reading inserted
SELECT reading_id, measured_at, soil_moisture_pct
FROM sensor_readings
WHERE reading_id = 'rdg-ticket054-smoke-001';

-- Check snapshot refreshed
SELECT window, window_end, soil_moisture_avg_pct, temperature_avg_c
FROM environment_snapshots
WHERE window = 'latest'
ORDER BY window_end DESC
LIMIT 1;

-- Confirm no 1h window
SELECT COUNT(*) FROM environment_snapshots WHERE window = '1h';
```
