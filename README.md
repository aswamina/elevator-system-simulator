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

The building view is a React app in `web/` (Vite + TypeScript). Build it once,
and the API server serves it at http://127.0.0.1:8000/:

```
cd web
npm install
npm run build
```

It draws the building in cross-section: each shaft with its car gliding floor
to floor, ropes, counterweights and a floor indicator per shaft, hall buttons
on every floor, and a cabin keypad, readout and maintenance switch per car.
The **Cars − / +** control adds or removes cars while everything keeps
running: new cars start idle on the ground floor, and a removed car (always
the highest-numbered one) hands its waiting hall calls to the others.
Idle cars sit with their cabin light gently pulsing. While working on the UI,
run `npm run dev` in `web/` instead (http://localhost:5173, with API calls
forwarded to the server on :8000) and `npm test` for its tests.

Interactive API docs are at http://127.0.0.1:8000/docs. The simulation advances on a
background clock; a car moves one floor per tick.

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/api/building` | Full state: every car, outstanding hall calls, the clock |
| PUT | `/api/building` | Replace the building (`name`, `floors`, `elevators`) |
| PATCH | `/api/building` | Add or remove cars live: `{"elevators": 5}` |
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
