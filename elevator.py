from enum import Enum
from elevatorState import ElevatorState
from sortedcontainers import SortedList
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
        # two sorted queues for SCAN: floors above and below current
        self._up_queue: SortedList[int] = SortedList()
        self._down_queue: SortedList[int] = SortedList(key=lambda x: -x)
        self._door_open_ticks_remaining = 0
        self.on_arrival: callable | None = None  # controller hooks in here
    
    def add_destination(self, floor: int) -> None:
        if not (self.min_floor <= floor <= self.max_floor):
            raise ValueError(f"Floor {floor} out of range [{self.min_floor}, {self.max_floor}]")
        if floor == self.current_floor:
            return
        if floor > self.current_floor:
            self._up_queue.add(floor)
        else:
            self._down_queue.add(floor)

    def step(self) -> bool:
        """Advance one floor toward the next destination. Returns True if moved."""
        next_floor = self._next_destination()
        if next_floor is None:
            self.direction = Direction.IDLE
            self.state = ElevatorState.STOPPED
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
            self._remove_destination(next_floor)
            self._arrive()

        return True

    def _next_destination(self) -> int | None:
        """SCAN: serve current direction first, then reverse."""
        if self.direction == Direction.UP or self.direction == Direction.IDLE:
            if self._up_queue:
                return self._up_queue[0]
            if self._down_queue:
                return self._down_queue[0]
        else:
            if self._down_queue:
                return self._down_queue[0]
            if self._up_queue:
                return self._up_queue[0]
        return None

    def _remove_destination(self, floor: int) -> None:
        if floor in self._up_queue:
            self._up_queue.remove(floor)
        elif floor in self._down_queue:
            self._down_queue.remove(floor)

    def _arrive(self) -> None:
        self.state = ElevatorState.STOPPED
        self.door.state = DoorState.OPENING
        self.door.state = DoorState.OPEN
        self._door_open_ticks_remaining = self.DOOR_OPEN_TICKS

        if self.on_arrival:
            self.on_arrival(self.id, self.current_floor, self.direction)

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
        self._up_queue.clear()
        self._down_queue.clear()

    @property
    def is_available(self) -> bool:
        return self.state != ElevatorState.MAINTENANCE

    @property
    def queue_length(self) -> int:
        return len(self._up_queue) + len(self._down_queue)

    def __repr__(self):
        return (
            f"Elevator(id={self.id}, floor={self.current_floor}, "
            f"direction={self.direction.value}, state={self.state.value}, "
            f"door={self.door}, queue={list(self._up_queue) + list(self._down_queue)})"
        )
