from abc import ABC, abstractmethod
from dataclasses import dataclass
from direction import Direction
import direction
from elevator import Elevator
from elevatorState import ElevatorState
from building import Building
from hallcall import HallCall

@dataclass
class Request:
    floor: int
    direction: Direction      # hall button (UP/DOWN)
    target_floor: int | None = None  # set once passenger boards


class DispatchStrategy(ABC):
    """Pluggable algorithm — swap without touching the controller."""
    @abstractmethod
    def select(self, call: HallCall, elevators: list[Elevator]) -> Elevator | None:
        ...


class NearestCarStrategy(DispatchStrategy):
    DIRECTION_PENALTY = 5
    MOVING_AGAINST_PENALTY = 15
    LOAD_PENALTY = 2

    def select(self, call: HallCall, elevators: list[Elevator]) -> Elevator | None:
        candidates = [e for e in elevators if e.is_available]
        if not candidates:
            return None
        return min(candidates, key=lambda e: self._cost(e, call))

    def _cost(self, elevator: Elevator, call: HallCall) -> int:
        distance = abs(elevator.current_floor - call.floor)
        direction_penalty = self._direction_penalty(elevator, call)
        load_penalty = elevator.queue_length * self.LOAD_PENALTY
        return distance + direction_penalty + load_penalty

    def _direction_penalty(self, elevator: Elevator, call: HallCall) -> int:
        if elevator.direction == Direction.IDLE:
            return 0
        moving_toward = (
            elevator.direction == Direction.UP and elevator.current_floor < call.floor
            or
            elevator.direction == Direction.DOWN and elevator.current_floor > call.floor
        )
        if not moving_toward:
            return self.MOVING_AGAINST_PENALTY
        same_direction = elevator.direction == call.direction
        return 0 if same_direction else self.DIRECTION_PENALTY


class ElevatorController:
    def __init__(self, building: Building, strategy: DispatchStrategy | None = None):
        self.building = building
        self.strategy = strategy or NearestCarStrategy()
        self._pending: list[HallCall] = []
        self._assigned: dict[HallCall, int] = {}  # HallCall → elevator_id

        # wire up arrival callbacks
        for elevator in self.building.elevators:
            elevator.on_arrival = self._on_elevator_arrival

    # ── Public API ────────────────────────────────────────────────────────────

    def request(self, floor: int, direction: Direction) -> None:
        """Hall button press — passenger waiting on a floor."""
        call = HallCall(floor=floor, direction=direction)

        if self._already_covered(call):
            return  # an elevator is already coming for this call

        elevator = self.strategy.select(call, self.building.available_elevators())
        if elevator:
            self._dispatch(elevator, call)
        else:
            self._pending.append(call)

    def board(self, elevator_id: int, target_floor: int) -> None:
        """Cabin button press — passenger inside elevator selects a floor."""
        elevator = self.building.get_elevator(elevator_id)
        elevator.add_destination(target_floor)

    def tick(self) -> None:
        for elevator in self.building.available_elevators():
            if elevator.door.is_open():
                elevator.tick_doors()   # let passengers out, count down
            else:
                elevator.step()         # only move when doors are closed
        self._retry_pending()
        

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _try_close_doors(self, elevator: Elevator) -> None:
        """Close doors once elevator has stopped and doors are open."""
        if elevator.state == ElevatorState.STOPPED and elevator.door.is_open():
            elevator.door.close()

    def is_idle(self) -> bool:
        return (
            not self._pending
            and not self._assigned
            and all(
                e.queue_length == 0
                and e.state != ElevatorState.MOVING
                and not e.door.is_open()
                for e in self.building.available_elevators()
            )
        )
    
    def _dispatch(self, elevator: Elevator, call: HallCall) -> None:
        if elevator.current_floor == call.floor:
            # already there — open doors immediately, no need to track in _assigned
            elevator.door.open()
            elevator._door_open_ticks_remaining = elevator.DOOR_OPEN_TICKS
            return
        elevator.add_destination(call.floor)
        self._assigned[call] = elevator.id

    def _already_covered(self, call: HallCall) -> bool:
        """True if an elevator is already assigned to this hall call."""
        return call in self._assigned
    
    def _on_elevator_arrival(self, elevator_id: int, floor: int, direction: Direction) -> None:
        to_remove = [
            call for call, eid in self._assigned.items()
            if eid == elevator_id and call.floor == floor
        ]
        for call in to_remove:
            self._assigned.pop(call)

    def _retry_pending(self) -> None:
        still_pending = []
        for call in self._pending:
            if self._already_covered(call):
                continue  # got covered by another dispatch in the meantime
            elevator = self.strategy.select(call, self.building.available_elevators())
            if elevator:
                self._dispatch(elevator, call)
            else:
                still_pending.append(call)
        self._pending = still_pending