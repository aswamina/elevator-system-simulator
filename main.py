from building import Building
from elevatorController import ElevatorController
from direction import Direction

""" building = Building(name="treasury bldg", floors=10, elevators=3)
e = building.get_elevator(0)

e.add_destination(5)
e.add_destination(8)
e.add_destination(3)

while e.step():
    print(e) """


building = Building(name="treasury bldg", floors=10, elevators=3)
controller = ElevatorController(building)

# Hall button presses
controller.request(floor=1, direction=Direction.UP)
controller.request(floor=7, direction=Direction.DOWN)

# Run simulation
while not controller.is_idle():
    controller.tick()
    print(building)

# Passenger boards elevator 0 and presses floor 9
controller.board(elevator_id=0, target_floor=9)