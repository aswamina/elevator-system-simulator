"""Hall calls are served only by a car travelling in the caller's direction.

Run from the repo root: python -m unittest discover tests
"""
import unittest

from building import Building
from direction import Direction
from elevator import Elevator
from elevatorController import ElevatorController
from hallcall import HallCall

UP, DOWN = Direction.UP, Direction.DOWN


def run(elevator: Elevator, max_ticks: int = 200) -> list[tuple[int, Direction]]:
    """Drive one car until it has nothing left to do; return its (floor, direction) stops."""
    stops = []
    elevator.on_arrival = lambda _id, floor, direction: stops.append((floor, direction))
    for _ in range(max_ticks):
        if elevator.door.is_open():
            elevator.tick_doors()
        elif not elevator.step() and elevator.queue_length == 0:
            return stops
    raise AssertionError(f"car never went idle: {elevator}")


class ElevatorDirectionTest(unittest.TestCase):
    def setUp(self):
        self.car = Elevator(elevator_id=0, min_floor=1, max_floor=10)

    def test_down_call_not_served_on_the_way_up(self):
        self.car.add_destination(9)
        self.car.add_hall_call(6, DOWN)
        self.assertEqual(run(self.car), [(9, UP), (6, DOWN)])

    def test_up_call_served_on_the_way_up(self):
        self.car.add_destination(9)
        self.car.add_hall_call(6, UP)
        self.assertEqual(run(self.car), [(6, UP), (9, UP)])

    def test_up_call_not_served_on_the_way_down(self):
        self.car.current_floor = 10
        self.car.add_destination(2)
        self.car.add_hall_call(5, UP)
        self.assertEqual(run(self.car), [(2, DOWN), (5, UP)])

    def test_car_climbs_to_highest_down_call_before_turning(self):
        self.car.add_hall_call(5, DOWN)
        self.car.add_hall_call(8, DOWN)
        self.assertEqual(run(self.car), [(8, DOWN), (5, DOWN)])

    def test_car_descends_to_lowest_up_call_before_turning(self):
        self.car.current_floor = 10
        self.car.add_hall_call(6, UP)
        self.car.add_hall_call(3, UP)
        self.assertEqual(run(self.car), [(3, UP), (6, UP)])

    def test_cabin_stops_served_in_either_direction(self):
        self.car.current_floor = 5
        self.car.direction = UP
        self.car.add_destination(8)
        self.car.add_destination(2)
        self.assertEqual(run(self.car), [(8, UP), (2, DOWN)])

    def test_opposite_call_at_end_of_run_served_in_same_stop(self):
        self.car.add_hall_call(7, UP)
        self.car.add_hall_call(7, DOWN)
        self.assertEqual(run(self.car), [(7, UP), (7, DOWN)])
        self.assertEqual(self.car.direction, Direction.IDLE)

    def test_opposite_call_waits_when_run_continues(self):
        self.car.add_destination(9)
        self.car.add_hall_call(6, UP)
        self.car.add_hall_call(6, DOWN)
        self.assertEqual(run(self.car), [(6, UP), (9, UP), (6, DOWN)])

    def test_call_at_current_floor_in_other_direction_served_after_run(self):
        self.car.current_floor = 5
        self.car.direction = UP
        self.car.add_hall_call(5, DOWN)
        self.car.add_destination(8)
        self.assertEqual(run(self.car), [(8, UP), (5, DOWN)])

    def test_hall_call_requires_direction(self):
        with self.assertRaises(ValueError):
            self.car.add_hall_call(5, Direction.IDLE)


class ControllerDirectionTest(unittest.TestCase):
    def setUp(self):
        self.building = Building(name="test", floors=10, elevators=1)
        self.controller = ElevatorController(self.building)
        self.car = self.building.get_elevator(0)

    def tick_until(self, condition, max_ticks: int = 200) -> None:
        for _ in range(max_ticks):
            if condition():
                return
            self.controller.tick()
        raise AssertionError(f"condition never met: {self.car}")

    def test_down_call_stays_assigned_while_car_passes_going_up(self):
        self.controller.request(1, UP)  # car is already at 1: doors open
        self.controller.board(0, 9)
        self.controller.request(6, DOWN)
        call = HallCall(6, DOWN)

        self.tick_until(lambda: self.car.current_floor == 7)
        self.assertEqual(self.car.direction, UP)
        self.assertIn(call, self.controller._assigned)

        self.tick_until(lambda: call not in self.controller._assigned)
        self.assertEqual(self.car.current_floor, 6)
        self.assertEqual(self.car.direction, DOWN)

    def test_both_calls_on_a_floor_cleared_only_by_their_own_direction(self):
        self.controller.board(0, 9)
        self.controller.request(6, UP)
        self.controller.request(6, DOWN)

        self.tick_until(lambda: HallCall(6, UP) not in self.controller._assigned)
        self.assertIn(HallCall(6, DOWN), self.controller._assigned)

        self.tick_until(self.controller.is_idle)
        self.assertEqual(self.car.current_floor, 6)


if __name__ == "__main__":
    unittest.main()
