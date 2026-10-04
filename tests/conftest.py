import pytest

import door


@pytest.fixture(autouse=True)
def no_door_sleep(monkeypatch):
    """Door.open/close sleep for a second to simulate the motor; skip that in tests."""
    monkeypatch.setattr(door, "sleep", lambda _seconds: None)
