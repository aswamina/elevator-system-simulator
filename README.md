# elevator-system-simulator

Elevator System Simulation — A Python simulation of a multi-elevator dispatch system featuring the SCAN scheduling algorithm, a pluggable dispatch strategy interface, and a cost-based nearest-car dispatcher. Models realistic elevator behavior including door state transitions, passenger boarding, and concurrent hall call deduplication across multiple elevators.

## Running the tests

```
uv run python -m pytest
```

## HTTP API

The simulator is exposed as a JSON API (FastAPI). Start it with:

```
uv run uvicorn api:app --reload
```

Interactive docs are at http://127.0.0.1:8000/docs. The simulation advances on a
background clock; a car moves one floor per tick.

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/api/building` | Full state: every car, outstanding hall calls, the clock |
| PUT | `/api/building` | Replace the building (`name`, `floors`, `elevators`) |
| GET | `/api/elevators`, `/api/elevators/{id}` | Car floor, direction, state, door, maintenance flag, stops |
| POST | `/api/hall-calls` | Hall button: `{"floor": 5, "direction": "UP"}` |
| POST | `/api/elevators/{id}/destinations` | Cabin button: `{"floor": 3}` |
| PUT | `/api/elevators/{id}/maintenance` | `{"in_maintenance": true}` takes a car out of service |
| GET/PATCH | `/api/simulation` | Read the clock, or set `paused` / `tick_interval` (seconds) |
| POST | `/api/simulation/tick?steps=N` | Advance by hand |

Startup settings come from environment variables: `ELEVATOR_BUILDING_NAME`,
`ELEVATOR_FLOORS` (default 10), `ELEVATOR_COUNT` (default 3),
`ELEVATOR_TICK_INTERVAL` (default 1.0) and `ELEVATOR_CORS_ORIGINS`
(comma-separated, default `*`).
