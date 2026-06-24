from abc import ABC, abstractmethod
from dataclasses import dataclass
from direction import Direction
from elevator import Elevator
from elevatorState import ElevatorState
from building import Building


@dataclass
class Request:
    floor: int
    direction: Direction      # hall button (UP/DOWN)
    target_floor: int | None = None  # set once passenger boards


class DispatchStrategy(ABC):
    """Pluggable algorithm — swap without touching the controller."""
    @abstractmethod
    def select(self, request: Request, elevators: list[Elevator]) -> Elevator | None:
        ...


class NearestCarStrategy(DispatchStrategy):
    """
    Cost = distance + direction_penalty + load_penalty
    Picks the elevator with the lowest cost.
    """
    DIRECTION_PENALTY = 10   # discourages dispatching a moving-away elevator
    LOAD_PENALTY = 2         # cost per queued stop

    def select(self, request: Request, elevators: list[Elevator]) -> Elevator | None:
        candidates = [e for e in elevators if e.is_available]
        if not candidates:
            return None
        candidateElevator =  min(candidates, key=lambda e: self._cost(e, request))
        print(candidateElevator)
        return candidateElevator

    def _cost(self, elevator: Elevator, request: Request) -> int:
        distance = abs(elevator.current_floor - request.floor)
        direction_penalty = self._direction_penalty(elevator, request)
        load_penalty = elevator.queue_length * self.LOAD_PENALTY
        return distance + direction_penalty + load_penalty

    def _direction_penalty(self, elevator: Elevator, request: Request) -> int:
        if elevator.direction == Direction.IDLE:
            return 0
        # elevator moving toward the request floor AND in the same direction → no penalty
        moving_toward = (
            elevator.direction == Direction.UP and elevator.current_floor < request.floor
            or
            elevator.direction == Direction.DOWN and elevator.current_floor > request.floor
        )
        same_direction = elevator.direction.value == request.direction.value
        if moving_toward and same_direction:
            return 0
        return self.DIRECTION_PENALTY


class ElevatorController:
    def __init__(self, building: Building, strategy: DispatchStrategy | None = None):
        self.building = building
        self.strategy = strategy or NearestCarStrategy()
        self._pending: list[Request] = []   # requests not yet assigned

    # ── Public API ────────────────────────────────────────────────────────────

    def request(self, floor: int, direction: Direction) -> None:
        req = Request(floor=floor, direction=direction)
        elevator = self.strategy.select(req, self.building.available_elevators())
        if elevator:
            elevator.add_destination(floor)
        else:
            # all elevators unavailable — hold for retry
            self._pending.append(req)

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

    def _retry_pending(self) -> None:
        """Re-dispatch any requests that couldn't be assigned earlier."""
        still_pending = []
        for req in self._pending:
            elevator = self.strategy.select(req, self.building.available_elevators())
            if elevator:
                elevator.add_destination(req.floor)
            else:
                still_pending.append(req)
        self._pending = still_pending

    def is_idle(self) -> bool:
        """True when every elevator is stopped with empty queues and closed doors."""
        return all(
            e.queue_length == 0
            and e.state != ElevatorState.MOVING
            and not e.door.is_open()
            for e in self.building.available_elevators()
        )