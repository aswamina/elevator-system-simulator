from elevator import Elevator

class Building:
    def __init__(self, name, floors, elevators):
        super().__init__()
        self.name = name

        if floors < 2:
            raise ValueError("Building must have at least 2 floors")
        self.floors = floors

        self.elevators: list[Elevator] = [
            Elevator(elevator_id=i, min_floor=1, max_floor=floors)
            for i in range(elevators)
        ]

    def get_elevator(self, elevator_id: int) -> Elevator:
        if not (0 <= elevator_id < len(self.elevators)):
            raise ValueError(f"No elevator with id {elevator_id}")
        return self.elevators[elevator_id]

    def add_elevator(self) -> Elevator:
        """Install another car, parked on the ground floor."""
        elevator = Elevator(elevator_id=len(self.elevators), min_floor=1, max_floor=self.floors)
        self.elevators.append(elevator)
        return elevator

    def remove_last_elevator(self) -> Elevator:
        """Take out the highest-numbered car, so the remaining ids stay 0..n-1."""
        if len(self.elevators) <= 1:
            raise ValueError("Building must have at least 1 elevator")
        return self.elevators.pop()

    def available_elevators(self) -> list[Elevator]:
        return [e for e in self.elevators if e.is_available]
    
    def __repr__(self):
        return (
            f"Building(floors={self.floors}, "
            f"elevators={len(self.elevators)})\n"
            + "\n".join(f"  {e}" for e in self.elevators)
        )
