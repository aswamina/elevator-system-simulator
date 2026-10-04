import pytest

from direction import Direction
from elevator import Elevator
from elevatorController import NearestCarStrategy
from hallcall import HallCall


def make_elevator(elevator_id=0, floor=1, direction=Direction.IDLE):
    e = Elevator(elevator_id=elevator_id, min_floor=1, max_floor=20)
    e.current_floor = floor
    e.direction = direction
    return e


@pytest.fixture
def strategy():
    return NearestCarStrategy()


class TestCost:
    def test_idle_cost_is_distance(self, strategy):
        e = make_elevator(floor=2)
        assert strategy._cost(e, HallCall(9, Direction.UP)) == 7
        assert strategy._cost(e, HallCall(2, Direction.DOWN)) == 0

    def test_moving_toward_call_in_same_direction_has_no_penalty(self, strategy):
        up = make_elevator(floor=3, direction=Direction.UP)
        down = make_elevator(floor=9, direction=Direction.DOWN)
        assert strategy._cost(up, HallCall(7, Direction.UP)) == 4
        assert strategy._cost(down, HallCall(5, Direction.DOWN)) == 4

    def test_moving_toward_call_in_opposite_direction(self, strategy):
        e = make_elevator(floor=3, direction=Direction.UP)
        assert strategy._cost(e, HallCall(7, Direction.DOWN)) == 4 + strategy.DIRECTION_PENALTY

    @pytest.mark.parametrize("direction, floor, call_floor", [
        (Direction.UP, 7, 3),
        (Direction.DOWN, 3, 7),
    ])
    def test_moving_away_from_call(self, strategy, direction, floor, call_floor):
        e = make_elevator(floor=floor, direction=direction)
        for call_dir in (Direction.UP, Direction.DOWN):
            cost = strategy._cost(e, HallCall(call_floor, call_dir))
            assert cost == 4 + strategy.MOVING_AGAINST_PENALTY

    def test_moving_car_at_the_call_floor_counts_as_moving_away(self, strategy):
        # Current behavior: a car that has just passed (or sits at) the floor
        # while still flagged UP/DOWN is not "moving toward" it.
        e = make_elevator(floor=5, direction=Direction.UP)
        assert strategy._cost(e, HallCall(5, Direction.UP)) == strategy.MOVING_AGAINST_PENALTY

    def test_load_penalty_per_queued_stop(self, strategy):
        e = make_elevator(floor=1)
        e.add_destination(10)
        e.add_destination(12)
        assert strategy._cost(e, HallCall(4, Direction.UP)) == 3 + 2 * strategy.LOAD_PENALTY


class TestSelect:
    def test_picks_nearest_idle_car(self, strategy):
        cars = [make_elevator(0, floor=1), make_elevator(1, floor=6), make_elevator(2, floor=10)]
        assert strategy.select(HallCall(7, Direction.UP), cars).id == 1

    def test_prefers_car_heading_toward_call_over_closer_car_heading_away(self, strategy):
        away = make_elevator(0, floor=6, direction=Direction.UP)     # 1 away, wrong way: 16
        toward = make_elevator(1, floor=1, direction=Direction.UP)   # 4 away, right way: 4
        assert strategy.select(HallCall(5, Direction.UP), [away, toward]) is toward

    def test_busy_car_loses_to_free_car(self, strategy):
        busy = make_elevator(0, floor=4)
        for floor in (8, 9, 10):
            busy.add_destination(floor)
        free = make_elevator(1, floor=1)
        assert strategy.select(HallCall(5, Direction.UP), [busy, free]) is free

    def test_skips_cars_in_maintenance(self, strategy):
        broken = make_elevator(0, floor=5)
        broken.mark_maintenance()
        far = make_elevator(1, floor=15)
        assert strategy.select(HallCall(5, Direction.UP), [broken, far]) is far

    def test_returns_none_when_no_car_available(self, strategy):
        broken = make_elevator(0)
        broken.mark_maintenance()
        assert strategy.select(HallCall(5, Direction.UP), [broken]) is None
        assert strategy.select(HallCall(5, Direction.UP), []) is None

    def test_ties_go_to_first_car(self, strategy):
        cars = [make_elevator(0, floor=3), make_elevator(1, floor=7)]
        assert strategy.select(HallCall(5, Direction.UP), cars).id == 0
