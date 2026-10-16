from datetime import datetime, timedelta, timezone

import pytest

from direction import Direction
from events import EventLog
from simulation import Simulation


@pytest.fixture
def sim():
    sim = Simulation(name="test", floors=10, elevators=2)
    # a fake clock that advances one second per reading
    start = datetime(2026, 10, 15, 9, 0, 0, tzinfo=timezone.utc)
    readings = iter(start + timedelta(seconds=i) for i in range(10_000))
    sim.events = EventLog(now=lambda: next(readings))
    return sim


def events(sim):
    return sim.recent_events()


def run_until_idle(sim, max_ticks=100):
    for _ in range(max_ticks):
        sim.tick()
        if sim.controller.is_idle():
            return
    raise AssertionError("simulation never went idle")


class TestHallCalls:
    def test_records_the_press_and_the_car_sent(self, sim):
        sim.request(6, Direction.DOWN)
        [event] = events(sim)
        assert event["kind"] == "hall"
        assert (event["floor"], event["direction"]) == (6, "DOWN")
        assert event["status"] == "waiting"
        assert event["car_id"] == 0
        assert event["pressed_at"] == "2026-10-15T09:00:00+00:00"
        assert event["pressed_tick"] == 0

    def test_marks_it_served_when_the_car_arrives(self, sim):
        sim.request(4, Direction.UP)
        sim.tick(2)
        assert events(sim)[0]["status"] == "waiting"
        sim.tick()
        [event] = events(sim)
        assert event["status"] == "served"
        assert event["car_id"] == 0
        assert event["served_tick"] == 3
        assert event["served_at"] is not None

    def test_names_the_car_that_actually_served_it_after_a_handoff(self, sim):
        sim.request(8, Direction.DOWN)
        sim.set_maintenance(0, True)
        run_until_idle(sim)
        [event] = events(sim)
        assert event["status"] == "served"
        assert event["car_id"] == 1

    def test_call_answered_on_the_spot(self, sim):
        sim.request(1, Direction.UP)  # car 0 is already on floor 1
        [event] = events(sim)
        assert event["status"] == "served"
        assert event["car_id"] == 0
        assert event["served_tick"] == 0

    def test_pressing_a_lit_button_again_is_not_logged_twice(self, sim):
        sim.request(5, Direction.UP)
        sim.request(5, Direction.UP)
        assert len(events(sim)) == 1

    def test_waiting_with_no_car_available(self, sim):
        sim.set_maintenance(0, True)
        sim.set_maintenance(1, True)
        sim.request(5, Direction.UP)
        [event] = events(sim)
        assert (event["status"], event["car_id"]) == ("waiting", None)
        sim.set_maintenance(1, False)
        run_until_idle(sim)
        assert events(sim)[0]["status"] == "served"
        assert events(sim)[0]["car_id"] == 1


class TestCabinPresses:
    def test_records_and_serves_a_cabin_press(self, sim):
        sim.board(1, 3)
        [event] = events(sim)
        assert (event["kind"], event["car_id"], event["floor"]) == ("cabin", 1, 3)
        assert event["direction"] is None
        assert event["status"] == "waiting"
        sim.tick(2)
        assert events(sim)[0]["status"] == "served"
        assert events(sim)[0]["served_tick"] == 2

    def test_press_for_the_current_floor_is_served_at_once(self, sim):
        sim.board(0, 1)
        assert events(sim)[0]["status"] == "served"

    def test_cancelled_when_the_car_goes_out_of_service(self, sim):
        sim.board(0, 7)
        sim.tick()
        sim.set_maintenance(0, True)
        [event] = events(sim)
        assert event["status"] == "cancelled"
        assert event["served_at"] is None

    def test_cancelled_when_the_car_is_removed(self, sim):
        sim.board(1, 7)
        sim.set_elevator_count(1)
        assert events(sim)[0]["status"] == "cancelled"


class TestLog:
    def test_newest_first_and_cleared_by_a_new_building(self, sim):
        sim.request(5, Direction.UP)
        sim.board(1, 9)
        assert [e["kind"] for e in events(sim)] == ["cabin", "hall"]
        sim.reset("new", 10, 2)
        assert events(sim) == []

    def test_keeps_only_the_most_recent_events(self):
        log = EventLog(limit=3)
        for floor in range(2, 7):
            log.hall_call(floor, Direction.UP, 0)
        assert [e["floor"] for e in log.recent(10)] == [6, 5, 4]
