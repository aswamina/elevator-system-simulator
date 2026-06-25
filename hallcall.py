from dataclasses import dataclass
from direction import Direction


@dataclass(frozen=True)
class HallCall:
    """A unique hall button press — floor + direction."""
    floor: int
    direction: Direction