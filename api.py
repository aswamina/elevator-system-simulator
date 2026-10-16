"""HTTP API for the elevator simulator.

Run it with:

    uv run uvicorn api:app --reload

then open http://127.0.0.1:8000/ for the building view, or
http://127.0.0.1:8000/docs for the interactive OpenAPI docs.
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from direction import Direction
from simulation import Simulation

# The React building view (web/), once built with `npm run build`.
WEB_DIST = Path(__file__).parent / "web" / "dist"

UI_NOT_BUILT = """<!doctype html><meta charset="utf-8"><title>Elevator Simulator</title>
<body style="font-family: system-ui, sans-serif; max-width: 40rem; margin: 3rem auto; padding: 0 1rem">
<h1>The building view hasn't been built yet</h1>
<p>Build it once with:</p>
<pre>cd web
npm install
npm run build</pre>
<p>then reload this page. The API itself is running: see <a href="/docs">/docs</a>.</p>
</body>"""


# ── Schemas ───────────────────────────────────────────────────────────────────

class ElevatorView(BaseModel):
    id: int
    current_floor: int
    direction: Literal["UP", "DOWN", "IDLE"]
    state: Literal["MOVING", "STOPPED", "MAINTENANCE"]
    door: Literal["OPEN", "CLOSED", "OPENING", "CLOSING"]
    in_maintenance: bool
    stops: list[int] = Field(description="Floors the car still has to stop at")


class EventView(BaseModel):
    id: int
    kind: Literal["hall", "cabin"]
    floor: int
    direction: Literal["UP", "DOWN"] | None = Field(description="Hall calls only")
    car_id: int | None = Field(
        description="Cabin presses: the car pressed in. Hall calls: the car sent, once there is one"
    )
    pressed_at: str = Field(description="ISO 8601 time the button was pressed")
    pressed_tick: int
    status: Literal["waiting", "served", "cancelled"]
    served_at: str | None
    served_tick: int | None


class ClockView(BaseModel):
    running: bool = Field(description="Background clock thread is alive")
    paused: bool
    tick_interval: float = Field(description="Seconds between automatic ticks")


class AssignedCall(BaseModel):
    floor: int
    direction: Literal["UP", "DOWN"]
    elevator_id: int


class PendingCall(BaseModel):
    floor: int
    direction: Literal["UP", "DOWN"]


class HallCalls(BaseModel):
    assigned: list[AssignedCall]
    pending: list[PendingCall] = Field(description="Calls waiting for an available car")


class BuildingView(BaseModel):
    name: str
    floors: int
    tick: int
    clock: ClockView
    idle: bool
    elevators: list[ElevatorView]
    hall_calls: HallCalls


class HallCallRequest(BaseModel):
    floor: int = Field(ge=1)
    direction: Literal["UP", "DOWN"]


class DestinationRequest(BaseModel):
    floor: int = Field(ge=1)


class MaintenanceRequest(BaseModel):
    in_maintenance: bool


class ClockUpdate(BaseModel):
    tick_interval: float | None = Field(default=None, gt=0)
    paused: bool | None = None


class BuildingConfig(BaseModel):
    name: str = "Main building"
    floors: int = Field(default=10, ge=2, le=200)
    elevators: int = Field(default=3, ge=1, le=50)


class BuildingUpdate(BaseModel):
    elevators: int = Field(ge=1, le=50, description="How many cars the building should have")


# ── App ───────────────────────────────────────────────────────────────────────

def create_app(simulation: Simulation | None = None, autostart: bool = True) -> FastAPI:
    """Build the API around `simulation`; `autostart` runs its background clock."""
    sim = simulation or Simulation(
        name=os.environ.get("ELEVATOR_BUILDING_NAME", "Main building"),
        floors=int(os.environ.get("ELEVATOR_FLOORS", "10")),
        elevators=int(os.environ.get("ELEVATOR_COUNT", "3")),
        tick_interval=float(os.environ.get("ELEVATOR_TICK_INTERVAL", "1.0")),
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if autostart:
            sim.start()
        try:
            yield
        finally:
            sim.stop()

    app = FastAPI(
        title="Elevator System Simulator",
        version="0.1.0",
        description=(
            "Drive a simulated multi-elevator building: press hall and cabin "
            "buttons, take cars in and out of maintenance, and read where every "
            "car is. The simulation advances on a background clock; time is "
            "measured in ticks, and a car moves one floor per tick."
        ),
        lifespan=lifespan,
    )
    app.state.simulation = sim

    origins = os.environ.get("ELEVATOR_CORS_ORIGINS", "*")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins.split(",")],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def guarded(fn, *args):
        """Turn the simulator's ValueErrors into HTTP errors."""
        try:
            return fn(*args)
        except ValueError as exc:
            message = str(exc)
            status = 404 if message.startswith("No elevator") else 422
            raise HTTPException(status_code=status, detail=message) from exc

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/building", response_model=BuildingView, tags=["state"])
    def get_building():
        """Full simulation state: every car, outstanding hall calls and the clock."""
        return sim.snapshot()

    @app.put("/api/building", response_model=BuildingView, tags=["state"])
    def reset_building(config: BuildingConfig):
        """Replace the building with a fresh one of the given size."""
        guarded(sim.reset, config.name, config.floors, config.elevators)
        return sim.snapshot()

    @app.patch("/api/building", response_model=BuildingView, tags=["state"])
    def resize_building(update: BuildingUpdate):
        """Add or remove cars without restarting: new cars start on the ground
        floor, and removed cars (highest ids first) hand their hall calls on."""
        guarded(sim.set_elevator_count, update.elevators)
        return sim.snapshot()

    @app.get("/api/elevators", response_model=list[ElevatorView], tags=["elevators"])
    def list_elevators():
        return sim.snapshot()["elevators"]

    @app.get("/api/elevators/{elevator_id}", response_model=ElevatorView, tags=["elevators"])
    def get_elevator(elevator_id: int):
        return guarded(sim.get_elevator, elevator_id)

    @app.post(
        "/api/elevators/{elevator_id}/destinations",
        response_model=ElevatorView,
        status_code=202,
        tags=["elevators"],
    )
    def press_cabin_button(elevator_id: int, body: DestinationRequest):
        """Cabin button: a passenger inside the car picks a floor."""
        guarded(sim.board, elevator_id, body.floor)
        return sim.get_elevator(elevator_id)

    @app.put(
        "/api/elevators/{elevator_id}/maintenance",
        response_model=ElevatorView,
        tags=["elevators"],
    )
    def set_maintenance(elevator_id: int, body: MaintenanceRequest):
        """Take a car out of service (its hall calls go to other cars) or bring it back."""
        guarded(sim.set_maintenance, elevator_id, body.in_maintenance)
        return sim.get_elevator(elevator_id)

    @app.post("/api/hall-calls", response_model=BuildingView, status_code=202, tags=["calls"])
    def press_hall_button(body: HallCallRequest):
        """Hall button: someone on `floor` wants to go `direction`."""
        guarded(sim.request, body.floor, Direction(body.direction))
        return sim.snapshot()

    @app.get("/api/events", response_model=list[EventView], tags=["calls"])
    def list_events(limit: int = Query(default=50, ge=1, le=200)):
        """Hall calls and cabin button presses, newest first, with the car that
        served each one. Pressing a button that is already lit isn't logged again."""
        return sim.recent_events(limit)

    @app.get("/api/simulation", response_model=ClockView, tags=["simulation"])
    def get_clock():
        return sim.snapshot()["clock"]

    @app.patch("/api/simulation", response_model=ClockView, tags=["simulation"])
    def update_clock(body: ClockUpdate):
        """Pause or resume the background clock, or change its speed."""
        sim.configure(tick_interval=body.tick_interval, paused=body.paused)
        return sim.snapshot()["clock"]

    @app.post("/api/simulation/tick", response_model=BuildingView, tags=["simulation"])
    def step(steps: int = Query(default=1, ge=1, le=1000)):
        """Advance the simulation by hand, e.g. while the clock is paused."""
        sim.tick(steps)
        return sim.snapshot()

    # Mounted last so the API routes above take precedence over the static files.
    if (WEB_DIST / "index.html").exists():
        app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="ui")
    else:
        @app.get("/", include_in_schema=False, response_class=HTMLResponse)
        def ui_not_built():
            return UI_NOT_BUILT

    return app


app = create_app()
