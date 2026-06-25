from building import Building
from elevatorController import ElevatorController
from direction import Direction


building = Building(name="treasury bldg", floors=10, elevators=3)
controller = ElevatorController(building)

# flood of requests across many floors
""" requests = [
    (1, Direction.UP), (5, Direction.UP), (5, Direction.UP),  # duplicate — ignored
    (6, Direction.DOWN), (8, Direction.DOWN), (3, Direction.UP),
] """

requests = [
    (1, Direction.UP),
    (5, Direction.UP),
    (5, Direction.UP), # duplicate — ignored
    (4, Direction.UP),
    (6, Direction.DOWN), 
    (8, Direction.DOWN), 
    (3, Direction.UP),
]
for floor, direction in requests:
    controller.request(floor, direction)

tick = 0
while not controller.is_idle():
    controller.tick()
    tick += 1
    print(f"Tick {tick}: {building}")