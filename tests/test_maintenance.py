import unittest

from building import Building
from direction import Direction
from elevatorController import ElevatorController
from hallcall import HallCall

MAX_TICKS = 50

class MaintenanceReassignmentTest(unittest.TestCase):
    def setUp(self):
        self.building = Building(name="test bldg", floors=10, elevators=3)
        self.controller = ElevatorController(self.building)

    def _run_until_idle(self) -> int:
        for tick in range(1, MAX_TICKS + 1):
            self.controller.tick()
            if self.controller.is_idle():
                return tick
        self.fail(f"controller still busy after {MAX_TICKS} ticks: {self.building}")

    def test_assigned_call_is_reassigned_when_car_enters_maintenance(self):
        self.controller.request(8, Direction.DOWN)
        assigned = self.building.get_elevator(0)
        self.assertEqual(assigned.queue_length, 1)  # car 0 took the call

        assigned.mark_maintenance()

        self._run_until_idle()
        served_by = [e.id for e in self.building.elevators if e.current_floor == 8]
        self.assertTrue(served_by, "no car reached floor 8")
        self.assertNotIn(assigned.id, served_by)

    def test_call_goes_pending_when_no_car_is_available(self):
        building = Building(name="one car", floors=10, elevators=1)
        controller = ElevatorController(building)
        car = building.get_elevator(0)
        controller.request(5, Direction.UP)

        car.mark_maintenance()

        self.assertEqual(controller._assigned, {})
        self.assertEqual(controller._pending, [HallCall(5, Direction.UP)])

from hallcall import HallCall  # noqa: E402

if __name__ == "__main__":
    unittest.main()
