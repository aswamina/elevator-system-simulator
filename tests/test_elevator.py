import pytest

from direction import Direction
from door import DoorState
from elevator import Elevator
from elevatorState import ElevatorState


@pytest.fixture
def elevator():
    return Elevator(elevator_id=0, min_floor=1, max_floor=10)


def drain(elevator, max_steps=100):
    """Run an elevator to completion, closing doors between steps.

    Returns the floors where it stopped, in order.
    """
    stops = []
    for _ in range(max_steps):
        if elevator.door.is_open():
            stops.append(elevator.current_floor)
            for _ in range(Elevator.DOOR_OPEN_TICKS):
                elevator.tick_doors()
        if not elevator.step():
            return stops
    raise AssertionError("elevator did not finish")


class TestInitialState:
    def test_starts_idle_at_min_floor_with_doors_closed(self, elevator):
        assert elevator.current_floor == 1
        assert elevator.direction == Direction.IDLE
        assert elevator.state == ElevatorState.STOPPED
        assert elevator.door.is_closed()
        assert elevator.queue_length == 0
        assert elevator.is_available


class TestAddDestination:
    @pytest.mark.parametrize("floor", [0, 11, -3])
    def test_rejects_out_of_range_floor(self, elevator, floor):
        with pytest.raises(ValueError):
            elevator.add_destination(floor)

    def test_current_floor_is_ignored(self, elevator):
        elevator.add_destination(1)
        assert elevator.queue_length == 0

    @pytest.mark.xfail(
        strict=True,
        reason="bug: SortedList keeps duplicates, so a second press of the same "
        "floor leaves a stale entry and the car bounces away and back",
    )
    def test_pressing_same_floor_twice_stops_there_once(self, elevator):
        elevator.add_destination(4)
        elevator.add_destination(4)
        visited = []
        while elevator.step():
            visited.append(elevator.current_floor)
            for _ in range(Elevator.DOOR_OPEN_TICKS):
                elevator.tick_doors()
        assert visited == [2, 3, 4]

    def test_floors_split_into_up_and_down_queues(self, elevator):
        elevator.current_floor = 5
        elevator.add_destination(8)
        elevator.add_destination(2)
        assert list(elevator._up_queue) == [8]
        assert list(elevator._down_queue) == [2]


class TestStep:
    def test_idle_with_no_destinations_does_not_move(self, elevator):
        assert elevator.step() is False
        assert elevator.current_floor == 1
        assert elevator.direction == Direction.IDLE
        assert elevator.state == ElevatorState.STOPPED

    def test_moves_one_floor_per_step(self, elevator):
        elevator.add_destination(4)
        assert elevator.step() is True
        assert elevator.current_floor == 2
        assert elevator.direction == Direction.UP
        assert elevator.state == ElevatorState.MOVING
        assert elevator.door.is_closed()

    def test_arrival_stops_and_opens_doors(self, elevator):
        elevator.add_destination(3)
        elevator.step()
        elevator.step()
        assert elevator.current_floor == 3
        assert elevator.state == ElevatorState.STOPPED
        assert elevator.door.is_open()
        assert elevator.queue_length == 0

    def test_moves_down(self, elevator):
        elevator.current_floor = 6
        elevator.add_destination(4)
        elevator.step()
        assert elevator.current_floor == 5
        assert elevator.direction == Direction.DOWN

    def test_becomes_idle_once_queue_is_empty(self, elevator):
        elevator.add_destination(2)
        elevator.step()
        assert elevator.step() is False
        assert elevator.direction == Direction.IDLE

    def test_on_arrival_callback_receives_id_floor_and_direction(self, elevator):
        calls = []
        elevator.on_arrival = lambda *args: calls.append(args)
        elevator.add_destination(3)
        elevator.step()
        assert calls == []
        elevator.step()
        assert calls == [(0, 3, Direction.UP)]


class TestScan:
    def test_serves_up_requests_in_ascending_order(self, elevator):
        for floor in (7, 3, 5):
            elevator.add_destination(floor)
        assert drain(elevator) == [3, 5, 7]

    def test_serves_down_requests_in_descending_order(self, elevator):
        elevator.current_floor = 10
        for floor in (2, 8, 5):
            elevator.add_destination(floor)
        assert drain(elevator) == [8, 5, 2]

    def test_finishes_current_direction_before_reversing(self, elevator):
        elevator.current_floor = 5
        elevator.add_destination(2)   # below
        elevator.add_destination(8)   # above
        elevator.add_destination(7)   # above
        # idle prefers UP first, then sweeps down
        assert drain(elevator) == [7, 8, 2]

    def test_keeps_going_down_when_already_moving_down(self, elevator):
        elevator.current_floor = 8
        elevator.add_destination(3)
        elevator.step()                  # now at 7, heading DOWN
        elevator.add_destination(9)      # behind us
        elevator.add_destination(5)      # ahead of us
        assert drain(elevator) == [5, 3, 9]

    def test_picks_up_request_added_ahead_mid_travel(self, elevator):
        elevator.add_destination(8)
        elevator.step()
        elevator.step()                  # at 3, heading UP
        elevator.add_destination(5)
        assert drain(elevator) == [5, 8]

    def test_does_not_pass_a_queued_floor(self, elevator):
        elevator.add_destination(9)
        elevator.add_destination(4)
        floors = []
        while not elevator.door.is_open():
            elevator.step()
            floors.append(elevator.current_floor)
        assert floors == [2, 3, 4]


class TestDoorTiming:
    def test_door_stays_open_for_door_open_ticks(self, elevator):
        elevator.add_destination(2)
        elevator.step()
        assert elevator.door.is_open()
        for _ in range(Elevator.DOOR_OPEN_TICKS - 1):
            elevator.tick_doors()
            assert elevator.door.is_open()
        elevator.tick_doors()
        assert elevator.door.is_closed()

    def test_tick_doors_is_a_noop_when_closed(self, elevator):
        elevator.tick_doors()
        assert elevator.door.state == DoorState.CLOSED

    def test_door_closes_before_moving(self, elevator):
        elevator.add_destination(2)
        elevator.add_destination(4)
        elevator.step()
        assert elevator.door.is_open()
        elevator.step()  # step forces the door shut even if ticks remain
        assert elevator.door.is_closed()
        assert elevator.current_floor == 3


class TestMaintenance:
    def test_maintenance_clears_queue_and_makes_unavailable(self, elevator):
        elevator.add_destination(5)
        elevator.add_destination(8)
        elevator.mark_maintenance()
        assert elevator.queue_length == 0
        assert elevator.direction == Direction.IDLE
        assert not elevator.is_available
