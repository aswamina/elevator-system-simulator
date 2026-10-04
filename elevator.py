from door import Door, DoorState
from direction import Direction
from elevatorState import ElevatorState


class Elevator:
    DOOR_OPEN_TICKS = 3  # how many ticks to keep the door open after arrival

    def __init__(self, elevator_id: int, min_floor: int, max_floor: int):
        self.id = elevator_id
        self.min_floor = min_floor
        self.max_floor = max_floor
        self.current_floor = min_floor
        self.direction = Direction.IDLE
        self.state = ElevatorState.STOPPED
        self.door = Door()
        # SCAN stops, keyed by the direction the car must be travelling to serve them
        self._up_stops: set[int] = set()     # UP hall calls
        self._down_stops: set[int] = set()   # DOWN hall calls
        self._cabin_stops: set[int] = set()  # cabin buttons: served in either direction
        self._door_open_ticks_remaining = 0
        self.on_arrival: callable | None = None  # controller hooks in here

    def add_destination(self, floor: int) -> None:
        """Cabin button: stop at this floor whichever way the car is going."""
        self._check_floor(floor)
        if floor == self.current_floor:
            return
        self._cabin_stops.add(floor)

    def add_hall_call(self, floor: int, direction: Direction) -> None:
        """Hall button: stop at this floor only while travelling in `direction`."""
        self._check_floor(floor)
        self._stops(direction).add(floor)

    def step(self) -> bool:
        """Advance one floor toward the next stop. Returns True if moved."""
        stop = self._next_stop()
        if stop is None:
            self.direction = Direction.IDLE
            self.state = ElevatorState.STOPPED
            return False

        next_floor, service_direction = stop
        if next_floor == self.current_floor:
            # a call waiting right here — serve it without moving
            self._arrive(service_direction)
            return False

        self.door.close()  # ensure door is closed before moving
        self.state = ElevatorState.MOVING
        if next_floor > self.current_floor:
            self.direction = Direction.UP
            self.current_floor += 1
        else:
            self.direction = Direction.DOWN
            self.current_floor -= 1

        if self.current_floor == next_floor:
            self._arrive(service_direction)

        return True

    def _next_stop(self) -> tuple[int, Direction] | None:
        """SCAN: sweep the current heading first, then reverse.

        Returns the next floor to stop at and the direction the car will be
        serving there, or None when there is nothing left to do.
        """
        if not self.queue_length:
            return None
        heading = self.direction
        if heading == Direction.IDLE:
            nearest = min(self._all_stops(), key=lambda f: abs(f - self.current_floor))
            heading = Direction.DOWN if nearest < self.current_floor else Direction.UP
        return self._sweep(heading) or self._sweep(_opposite(heading))

    def _sweep(self, heading: Direction) -> tuple[int, Direction] | None:
        """Next stop when travelling in `heading` from the current floor."""
        cur = self.current_floor
        if heading == Direction.UP:
            # stops along the way: UP calls and cabin buttons at or above us
            ahead = [f for f in self._up_stops | self._cabin_stops if f >= cur]
            if ahead:
                return min(ahead), Direction.UP
            # otherwise run up to the highest DOWN call and turn around there
            turn = [f for f in self._down_stops if f > cur]
            if turn:
                return max(turn), Direction.DOWN
        else:
            ahead = [f for f in self._down_stops | self._cabin_stops if f <= cur]
            if ahead:
                return max(ahead), Direction.DOWN
            turn = [f for f in self._up_stops if f < cur]
            if turn:
                return min(turn), Direction.UP
        return None

    def _has_stops_beyond(self, heading: Direction) -> bool:
        if heading == Direction.UP:
            return any(f > self.current_floor for f in self._all_stops())
        return any(f < self.current_floor for f in self._all_stops())

    def _serve(self, direction: Direction) -> None:
        self._cabin_stops.discard(self.current_floor)
        self._stops(direction).discard(self.current_floor)

    def _stops(self, direction: Direction) -> set[int]:
        if direction == Direction.UP:
            return self._up_stops
        if direction == Direction.DOWN:
            return self._down_stops
        raise ValueError(f"Hall call needs a direction, got {direction}")

    def _all_stops(self) -> set[int]:
        return self._up_stops | self._down_stops | self._cabin_stops

    def _check_floor(self, floor: int) -> None:
        if not (self.min_floor <= floor <= self.max_floor):
            raise ValueError(f"Floor {floor} out of range [{self.min_floor}, {self.max_floor}]")

    def _arrive(self, service_direction: Direction) -> None:
        self.state = ElevatorState.STOPPED
        self.direction = service_direction
        self._serve(service_direction)
        served = [service_direction]

        # end of the run: also pick up anyone here waiting to go the other way
        opposite = _opposite(service_direction)
        if (
            not self._has_stops_beyond(service_direction)
            and self.current_floor in self._stops(opposite)
        ):
            self.direction = opposite
            self._serve(opposite)
            served.append(opposite)

        self.door.state = DoorState.OPENING
        self.door.state = DoorState.OPEN
        self._door_open_ticks_remaining = self.DOOR_OPEN_TICKS

        if self.on_arrival:
            for direction in served:
                self.on_arrival(self.id, self.current_floor, direction)

    def tick_doors(self) -> None:
        """Called by controller each tick. Counts down and closes doors."""
        if self.door.state == DoorState.OPEN:
            self._door_open_ticks_remaining -= 1
            if self._door_open_ticks_remaining <= 0:
                self.door.state = DoorState.CLOSING
                self.door.state = DoorState.CLOSED

    def mark_maintenance(self) -> None:
        self.state = ElevatorState.MAINTENANCE
        self.direction = Direction.IDLE
        self._up_stops.clear()
        self._down_stops.clear()
        self._cabin_stops.clear()

    @property
    def is_available(self) -> bool:
        return self.state != ElevatorState.MAINTENANCE

    @property
    def queue_length(self) -> int:
        return len(self._up_stops) + len(self._down_stops) + len(self._cabin_stops)

    def __repr__(self):
        return (
            f"Elevator(id={self.id}, floor={self.current_floor}, "
            f"direction={self.direction.value}, state={self.state.value}, "
            f"door={self.door}, queue={sorted(self._all_stops())})"
        )


def _opposite(direction: Direction) -> Direction:
    return Direction.DOWN if direction == Direction.UP else Direction.UP
