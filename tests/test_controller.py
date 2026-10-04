import pytest

from building import Building
from direction import Direction
from elevator import Elevator
from elevatorController import DispatchStrategy, ElevatorController
from elevatorState import ElevatorState
from hallcall import HallCall


def run_until_idle(controller, max_ticks=200):
    for tick in range(1, max_ticks + 1):
        controller.tick()
        if controller.is_idle():
            return tick
    raise AssertionError(f"controller not idle after {max_ticks} ticks")


@pytest.fixture
def building():
    return Building(name="test", floors=10, elevators=2)


@pytest.fixture
def controller(building):
    return ElevatorController(building)


class TestBuilding:
    def test_requires_two_floors(self):
        with pytest.raises(ValueError):
            Building(name="shed", floors=1, elevators=1)

    def test_get_elevator_rejects_unknown_id(self, building):
        with pytest.raises(ValueError):
            building.get_elevator(2)


class TestRequest:
    def test_new_controller_is_idle(self, controller):
        assert controller.is_idle()

    def test_dispatches_call_to_an_elevator(self, controller, building):
        controller.request(5, Direction.UP)
        assert controller._assigned == {HallCall(5, Direction.UP): 0}
        assert building.elevators[0].queue_length == 1
        assert not controller.is_idle()

    def test_duplicate_call_is_ignored(self, controller, building):
        controller.request(5, Direction.UP)
        controller.request(5, Direction.UP)
        assert sum(e.queue_length for e in building.elevators) == 1

    def test_same_floor_opposite_direction_is_a_separate_call(self, controller):
        controller.request(5, Direction.UP)
        controller.request(5, Direction.DOWN)
        assert len(controller._assigned) == 2

    def test_second_call_goes_to_less_loaded_car(self, controller):
        controller.request(5, Direction.UP)
        controller.request(4, Direction.UP)
        # car 0 now has a stop queued, so car 1 (idle, same distance) wins
        assert controller._assigned[HallCall(4, Direction.UP)] == 1

    def test_call_at_current_floor_opens_doors_immediately(self, controller, building):
        controller.request(1, Direction.UP)
        car = building.elevators[0]
        assert car.door.is_open()
        assert car._door_open_ticks_remaining == Elevator.DOOR_OPEN_TICKS
        assert controller._assigned == {}

    def test_call_with_no_available_car_is_queued(self, controller, building):
        for car in building.elevators:
            car.mark_maintenance()
        controller.request(5, Direction.UP)
        assert controller._pending == [HallCall(5, Direction.UP)]
        assert controller._assigned == {}


class TestTick:
    def test_tick_moves_car_one_floor(self, controller, building):
        controller.request(4, Direction.DOWN)
        controller.tick()
        assert building.elevators[0].current_floor == 2

    def test_arrival_clears_assignment(self, controller, building):
        controller.request(3, Direction.UP)
        controller.tick()
        controller.tick()
        car = building.elevators[0]
        assert car.current_floor == 3
        assert car.door.is_open()
        assert controller._assigned == {}

    def test_car_waits_with_doors_open_before_moving_on(self, controller, building):
        controller.request(3, Direction.UP)
        controller.tick()
        controller.tick()                     # arrives at 3
        controller.board(0, 6)
        car = building.elevators[0]
        for _ in range(Elevator.DOOR_OPEN_TICKS):
            assert car.current_floor == 3
            controller.tick()                 # doors count down, no movement
        assert car.door.is_closed()
        controller.tick()
        assert car.current_floor == 4

    def test_board_adds_cabin_destination(self, controller, building):
        controller.board(1, 7)
        ticks = run_until_idle(controller)
        assert building.elevators[1].current_floor == 7
        # 6 floors of travel + door dwell
        assert ticks == 6 + Elevator.DOOR_OPEN_TICKS

    def test_cars_in_maintenance_do_not_move(self, controller, building):
        building.elevators[0].add_destination(5)
        building.elevators[0].state = ElevatorState.MAINTENANCE
        controller.tick()
        assert building.elevators[0].current_floor == 1

    def test_pending_call_is_dispatched_once_a_car_frees_up(self, controller, building):
        for car in building.elevators:
            car.mark_maintenance()
        controller.request(5, Direction.UP)
        controller.tick()
        assert controller._pending

        building.elevators[1].state = ElevatorState.STOPPED
        controller.tick()
        assert controller._pending == []
        assert controller._assigned == {HallCall(5, Direction.UP): 1}
        run_until_idle(controller)
        assert building.elevators[1].current_floor == 5

    def test_custom_strategy_is_used(self, building):
        class AlwaysLast(DispatchStrategy):
            def select(self, call, elevators):
                return elevators[-1] if elevators else None

        controller = ElevatorController(building, strategy=AlwaysLast())
        controller.request(5, Direction.UP)
        assert controller._assigned == {HallCall(5, Direction.UP): 1}


class TestScenario:
    def test_main_scenario_serves_every_call_and_goes_idle(self):
        building = Building(name="treasury bldg", floors=10, elevators=3)
        controller = ElevatorController(building)
        calls = [
            (1, Direction.UP), (5, Direction.UP), (5, Direction.UP),
            (4, Direction.UP), (6, Direction.DOWN), (8, Direction.DOWN),
            (3, Direction.UP),
        ]
        stops = []
        for car in building.elevators:
            car.on_arrival = (
                lambda eid, floor, d, inner=car.on_arrival:
                (stops.append(floor), inner(eid, floor, d))
            )
        for floor, direction in calls:
            controller.request(floor, direction)

        run_until_idle(controller)
        # floor 1 is served on the spot; every other call floor gets an arrival
        assert set(stops) == {3, 4, 5, 6, 8}
