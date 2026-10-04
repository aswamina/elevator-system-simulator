import threading

from building import Building
from direction import Direction
from elevator import Elevator
from elevatorController import ElevatorController
from elevatorState import ElevatorState


class Simulation:
    """A building and its controller, advanced one tick at a time.

    The controller isn't thread-safe, so every read and write goes through
    one lock. `start()` runs a background thread that ticks every
    `tick_interval` seconds while the simulation isn't paused.
    """

    def __init__(
        self,
        name: str = "Main building",
        floors: int = 10,
        elevators: int = 3,
        tick_interval: float = 1.0,
    ):
        self._lock = threading.RLock()
        self._wake = threading.Event()  # interrupts the sleep between ticks
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.tick_interval = _check_interval(tick_interval)
        self.paused = False
        self.reset(name, floors, elevators)

    # ── Building ──────────────────────────────────────────────────────────────

    def reset(self, name: str, floors: int, elevators: int) -> None:
        """Replace the building with a fresh one; the tick count restarts at 0."""
        if elevators < 1:
            raise ValueError("Building must have at least 1 elevator")
        building = Building(name=name, floors=floors, elevators=elevators)
        with self._lock:
            self.building = building
            self.controller = ElevatorController(building)
            self.tick_count = 0

    def request(self, floor: int, direction: Direction) -> None:
        """Hall button press."""
        if direction == Direction.IDLE:
            raise ValueError("Hall call direction must be UP or DOWN")
        with self._lock:
            self._check_floor(floor)
            if floor == self.building.floors and direction == Direction.UP:
                raise ValueError("There is no UP button on the top floor")
            if floor == 1 and direction == Direction.DOWN:
                raise ValueError("There is no DOWN button on the ground floor")
            self.controller.request(floor, direction)

    def board(self, elevator_id: int, floor: int) -> None:
        """Cabin button press."""
        with self._lock:
            elevator = self.building.get_elevator(elevator_id)
            if not elevator.is_available:
                raise ValueError(f"Elevator {elevator_id} is in maintenance")
            self.controller.board(elevator_id, floor)

    def set_maintenance(self, elevator_id: int, on: bool) -> None:
        with self._lock:
            elevator = self.building.get_elevator(elevator_id)
            if on and elevator.is_available:
                elevator.mark_maintenance()
            elif not on:
                elevator.return_to_service()

    def get_elevator(self, elevator_id: int) -> dict:
        with self._lock:
            return _elevator_state(self.building.get_elevator(elevator_id))

    # ── Clock ─────────────────────────────────────────────────────────────────

    def tick(self, steps: int = 1) -> None:
        with self._lock:
            for _ in range(steps):
                self.controller.tick()
                self.tick_count += 1

    def configure(self, tick_interval: float | None = None, paused: bool | None = None) -> None:
        with self._lock:
            if tick_interval is not None:
                self.tick_interval = _check_interval(tick_interval)
            if paused is not None:
                self.paused = paused
        self._wake.set()  # pick up the new settings now, not after the old interval

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="simulation-clock", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join()
            self._thread = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(self.tick_interval)
            self._wake.clear()
            if self._stop.is_set():
                break
            with self._lock:  # so a pause request can't land mid-check
                if not self.paused:
                    self.tick()

    # ── State ─────────────────────────────────────────────────────────────────

    def snapshot(self) -> dict:
        with self._lock:
            building = self.building
            return {
                "name": building.name,
                "floors": building.floors,
                "tick": self.tick_count,
                "clock": {
                    "running": self.running,
                    "paused": self.paused,
                    "tick_interval": self.tick_interval,
                },
                "idle": self.controller.is_idle(),
                "elevators": [_elevator_state(e) for e in building.elevators],
                "hall_calls": {
                    "assigned": [
                        {"floor": c.floor, "direction": c.direction.value, "elevator_id": eid}
                        for c, eid in self.controller._assigned.items()
                    ],
                    "pending": [
                        {"floor": c.floor, "direction": c.direction.value}
                        for c in self.controller._pending
                    ],
                },
            }

    def _check_floor(self, floor: int) -> None:
        if not (1 <= floor <= self.building.floors):
            raise ValueError(f"Floor {floor} out of range [1, {self.building.floors}]")


def _elevator_state(elevator: Elevator) -> dict:
    return {
        "id": elevator.id,
        "current_floor": elevator.current_floor,
        "direction": elevator.direction.value,
        "state": elevator.state.value,
        "door": elevator.door.state.value,
        "in_maintenance": elevator.state == ElevatorState.MAINTENANCE,
        "stops": elevator.stops,
    }


def _check_interval(seconds: float) -> float:
    if seconds <= 0:
        raise ValueError("tick_interval must be greater than 0")
    return seconds
