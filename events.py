from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from itertools import count
from typing import Callable

from building import Building
from direction import Direction
from door import DoorState
from elevatorController import ElevatorController
from hallcall import HallCall


@dataclass
class Event:
    """One button press and, once it happens, the car that answered it."""

    id: int
    kind: str  # "hall" or "cabin"
    floor: int
    direction: str | None  # hall calls only
    car_id: int | None  # cabin: the car pressed in; hall: the car sent (so far)
    pressed_at: str
    pressed_tick: int
    status: str = "waiting"  # "waiting", "served" or "cancelled"
    served_at: str | None = None
    served_tick: int | None = None


class EventLog:
    """Records hall calls and cabin presses, and which car served each one.

    The controller doesn't announce when a call is served, so `sync` compares
    the open events against the controller's state after every change: a hall
    call is served once no car is assigned to it and it isn't waiting, and a
    cabin press once the car drops that floor from its stops while standing on
    it. A stop that vanishes anywhere else (maintenance, a removed car) was
    cancelled, not served.
    """

    def __init__(self, limit: int = 200, now: Callable[[], datetime] | None = None):
        self._events: deque[Event] = deque(maxlen=limit)
        self._open: dict[tuple, Event] = {}
        self._ids = count(1)
        self._now = now or (lambda: datetime.now().astimezone())

    def clear(self) -> None:
        self._events.clear()
        self._open.clear()

    def hall_call(self, floor: int, direction: Direction, tick: int) -> None:
        self._record(("hall", floor, direction.value), "hall", floor, direction.value, None, tick)

    def cabin_press(self, elevator_id: int, floor: int, tick: int) -> None:
        self._record(("cabin", elevator_id, floor), "cabin", floor, None, elevator_id, tick)

    def sync(self, building: Building, controller: ElevatorController, tick: int) -> None:
        assigned = controller._assigned
        pending = set(controller._pending)
        cars = {e.id: e for e in building.elevators}

        for key, event in list(self._open.items()):
            if event.kind == "hall":
                call = HallCall(event.floor, Direction(event.direction))
                if call in assigned:
                    event.car_id = assigned[call]
                    continue
                if call in pending:
                    event.car_id = None
                    continue
                if event.car_id is None or event.car_id not in cars:
                    # answered on the spot by a car already standing there
                    event.car_id = _car_at(building, event.floor)
                car = cars.get(event.car_id)
                served = car is not None and car.current_floor == event.floor
            else:
                car = cars.get(event.car_id)
                if car is not None and event.floor in car.stops:
                    continue
                served = car is not None and car.current_floor == event.floor
            self._close(key, event, tick, served)

    def recent(self, limit: int) -> list[dict]:
        """Newest first."""
        return [asdict(e) for e in list(self._events)[::-1][:limit]]

    def _record(self, key, kind, floor, direction, car_id, tick) -> None:
        if key in self._open:
            return  # the button is already lit; pressing it again changes nothing
        event = Event(
            id=next(self._ids),
            kind=kind,
            floor=floor,
            direction=direction,
            car_id=car_id,
            pressed_at=self._stamp(),
            pressed_tick=tick,
        )
        self._events.append(event)
        self._open[key] = event

    def _close(self, key, event: Event, tick: int, served: bool) -> None:
        event.status = "served" if served else "cancelled"
        event.served_at = self._stamp() if served else None
        event.served_tick = tick if served else None
        del self._open[key]

    def _stamp(self) -> str:
        return self._now().isoformat(timespec="seconds")


def _car_at(building: Building, floor: int) -> int | None:
    for car in building.elevators:
        if car.current_floor == floor and car.door.state == DoorState.OPEN:
            return car.id
    return None
