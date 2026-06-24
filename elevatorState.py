from enum import Enum


class ElevatorState(Enum):
    MOVING = "MOVING"
    STOPPED = "STOPPED"
    MAINTENANCE = "MAINTENANCE"