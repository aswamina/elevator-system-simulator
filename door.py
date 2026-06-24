from enum import Enum
from time import sleep


class DoorState(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    OPENING = "OPENING"
    CLOSING = "CLOSING"


class Door:
    def __init__(self):
        self.state = DoorState.CLOSED

    def open(self) -> bool:
        if self.state in (DoorState.CLOSED, DoorState.CLOSING):
            self.state = DoorState.OPENING
            sleep(1)  # simulate time to open the door
            # simulate motor: in real system this is async + sensor feedback
            self.state = DoorState.OPEN
            return True
        return False

    def close(self) -> bool:
        if self.state in (DoorState.OPEN, DoorState.OPENING):
            self.state = DoorState.CLOSING
            sleep(1)  # simulate time to close the door
            self.state = DoorState.CLOSED
            return True
        return False

    def is_open(self) -> bool:
        return self.state == DoorState.OPEN

    def is_closed(self) -> bool:
        return self.state == DoorState.CLOSED

    def __repr__(self):
        return f"Door({self.state.value})"

