import time

import pytest
from fastapi.testclient import TestClient

from api import create_app
from simulation import Simulation


@pytest.fixture
def sim():
    return Simulation(name="test", floors=10, elevators=2)


@pytest.fixture
def client(sim):
    # no background clock: tests advance time with /api/simulation/tick
    with TestClient(create_app(sim, autostart=False)) as client:
        yield client


def tick(client, steps=1):
    response = client.post("/api/simulation/tick", params={"steps": steps})
    assert response.status_code == 200
    return response.json()


class TestState:
    def test_health(self, client):
        assert client.get("/health").json() == {"status": "ok"}

    def test_building_snapshot(self, client):
        body = client.get("/api/building").json()
        assert body["name"] == "test"
        assert body["floors"] == 10
        assert body["tick"] == 0
        assert body["idle"] is True
        assert body["hall_calls"] == {"assigned": [], "pending": []}
        assert body["elevators"][0] == {
            "id": 0,
            "current_floor": 1,
            "direction": "IDLE",
            "state": "STOPPED",
            "door": "CLOSED",
            "in_maintenance": False,
            "stops": [],
        }

    def test_list_and_get_elevators(self, client):
        assert [e["id"] for e in client.get("/api/elevators").json()] == [0, 1]
        assert client.get("/api/elevators/1").json()["id"] == 1

    def test_unknown_elevator_is_404(self, client):
        assert client.get("/api/elevators/7").status_code == 404

    def test_openapi_docs_are_served(self, client):
        assert client.get("/docs").status_code == 200
        paths = client.get("/openapi.json").json()["paths"]
        assert "/api/hall-calls" in paths

    def test_cors_allows_browser_clients(self, client):
        response = client.get("/api/building", headers={"Origin": "http://localhost:5173"})
        assert response.headers["access-control-allow-origin"] == "*"


class TestHallCalls:
    def test_call_is_assigned_and_served(self, client):
        response = client.post("/api/hall-calls", json={"floor": 4, "direction": "UP"})
        assert response.status_code == 202
        assert response.json()["hall_calls"]["assigned"] == [
            {"floor": 4, "direction": "UP", "elevator_id": 0}
        ]

        body = tick(client, 3)
        car = body["elevators"][0]
        assert car["current_floor"] == 4
        assert car["door"] == "OPEN"
        assert car["state"] == "STOPPED"
        assert body["hall_calls"]["assigned"] == []

    def test_car_moves_one_floor_per_tick(self, client):
        client.post("/api/hall-calls", json={"floor": 6, "direction": "DOWN"})
        car = tick(client)["elevators"][0]
        assert car["current_floor"] == 2
        assert car["direction"] == "UP"
        assert car["state"] == "MOVING"
        assert car["stops"] == [6]

    def test_call_at_the_cars_floor_opens_doors_without_waiting(self, client):
        started = time.monotonic()
        client.post("/api/hall-calls", json={"floor": 1, "direction": "UP"})
        assert time.monotonic() - started < 0.5
        assert client.get("/api/elevators/0").json()["door"] == "OPEN"

    @pytest.mark.parametrize(
        "payload",
        [
            {"floor": 11, "direction": "UP"},
            {"floor": 0, "direction": "UP"},
            {"floor": 3, "direction": "IDLE"},
            {"floor": 10, "direction": "UP"},
            {"floor": 1, "direction": "DOWN"},
        ],
    )
    def test_invalid_calls_are_rejected(self, client, payload):
        assert client.post("/api/hall-calls", json=payload).status_code == 422


class TestCabinButtons:
    def test_destination_is_queued_and_reached(self, client):
        response = client.post("/api/elevators/1/destinations", json={"floor": 3})
        assert response.status_code == 202
        assert response.json()["stops"] == [3]

        car = tick(client, 2)["elevators"][1]
        assert car["current_floor"] == 3
        assert car["door"] == "OPEN"

    def test_floor_out_of_range_is_422(self, client):
        response = client.post("/api/elevators/0/destinations", json={"floor": 42})
        assert response.status_code == 422

    def test_unknown_elevator_is_404(self, client):
        response = client.post("/api/elevators/9/destinations", json={"floor": 3})
        assert response.status_code == 404


class TestMaintenance:
    def test_car_in_maintenance_hands_its_calls_to_another_car(self, client):
        client.post("/api/hall-calls", json={"floor": 8, "direction": "DOWN"})
        response = client.put("/api/elevators/0/maintenance", json={"in_maintenance": True})
        assert response.json()["in_maintenance"] is True
        assert response.json()["state"] == "MAINTENANCE"

        assigned = client.get("/api/building").json()["hall_calls"]["assigned"]
        assert assigned == [{"floor": 8, "direction": "DOWN", "elevator_id": 1}]

    def test_cabin_button_rejected_while_in_maintenance(self, client):
        client.put("/api/elevators/0/maintenance", json={"in_maintenance": True})
        response = client.post("/api/elevators/0/destinations", json={"floor": 3})
        assert response.status_code == 422

    def test_pending_call_is_served_once_a_car_returns(self, client):
        client.put("/api/building", json={"name": "one car", "floors": 5, "elevators": 1})
        client.put("/api/elevators/0/maintenance", json={"in_maintenance": True})
        body = client.post("/api/hall-calls", json={"floor": 3, "direction": "UP"}).json()
        assert body["hall_calls"]["pending"] == [{"floor": 3, "direction": "UP"}]

        car = client.put("/api/elevators/0/maintenance", json={"in_maintenance": False}).json()
        assert car["state"] == "STOPPED"

        body = tick(client, 3)
        assert body["hall_calls"]["pending"] == []
        assert body["elevators"][0]["current_floor"] == 3


class TestSimulation:
    def test_reset_builds_a_new_building(self, client):
        client.post("/api/hall-calls", json={"floor": 5, "direction": "UP"})
        tick(client)
        body = client.put(
            "/api/building", json={"name": "tower", "floors": 30, "elevators": 4}
        ).json()
        assert (body["name"], body["floors"], body["tick"]) == ("tower", 30, 0)
        assert len(body["elevators"]) == 4
        assert body["idle"] is True

    def test_reset_rejects_a_one_floor_building(self, client):
        assert client.put("/api/building", json={"floors": 1}).status_code == 422

    def test_pause_and_change_speed(self, client):
        clock = client.patch(
            "/api/simulation", json={"paused": True, "tick_interval": 0.25}
        ).json()
        assert clock["paused"] is True
        assert clock["tick_interval"] == 0.25

    def test_tick_interval_must_be_positive(self, client):
        assert client.patch("/api/simulation", json={"tick_interval": 0}).status_code == 422


class TestBackgroundClock:
    def test_clock_advances_the_simulation(self):
        sim = Simulation(floors=10, elevators=1, tick_interval=0.01)
        with TestClient(create_app(sim)) as client:
            client.post("/api/hall-calls", json={"floor": 5, "direction": "UP"})
            deadline = time.monotonic() + 5
            while client.get("/api/elevators/0").json()["current_floor"] != 5:
                assert time.monotonic() < deadline, "car never reached floor 5"
                time.sleep(0.01)
            assert client.get("/api/simulation").json()["running"] is True
        assert not sim.running  # shutting the app down stops the clock

    def test_paused_clock_does_not_tick(self):
        sim = Simulation(floors=10, elevators=1, tick_interval=0.01)
        with TestClient(create_app(sim)) as client:
            client.patch("/api/simulation", json={"paused": True})
            before = client.get("/api/building").json()["tick"]
            time.sleep(0.1)
            assert client.get("/api/building").json()["tick"] == before
