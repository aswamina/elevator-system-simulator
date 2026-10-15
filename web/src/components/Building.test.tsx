import { act, fireEvent, render, screen } from "@testing-library/react";
import type { Building as BuildingState, Elevator } from "../api";
import { Building, carOffset, motionOf, rowHeight } from "./Building";

function car(overrides: Partial<Elevator> = {}): Elevator {
  return {
    id: 0,
    current_floor: 1,
    direction: "IDLE",
    state: "STOPPED",
    door: "CLOSED",
    in_maintenance: false,
    stops: [],
    ...overrides,
  };
}

function building(overrides: Partial<BuildingState> = {}): BuildingState {
  return {
    name: "test",
    floors: 10,
    tick: 0,
    clock: { running: true, paused: false, tick_interval: 1 },
    idle: true,
    elevators: [car()],
    hall_calls: { assigned: [], pending: [] },
    ...overrides,
  };
}

describe("motionOf", () => {
  it("is idle when stopped with doors shut and nothing to do", () => {
    expect(motionOf(car())).toBe("idle");
  });
  it("is moving while travelling", () => {
    expect(motionOf(car({ state: "MOVING", direction: "UP", stops: [5] }))).toBe("moving");
  });
  it("is boarding while the doors are open", () => {
    expect(motionOf(car({ door: "OPEN", direction: "UP" }))).toBe("boarding");
  });
  it("is maintenance whatever else is going on", () => {
    expect(motionOf(car({ in_maintenance: true, state: "MAINTENANCE" }))).toBe("maintenance");
  });
});

describe("geometry", () => {
  it("puts the top floor at the top of the shaft", () => {
    expect(carOffset(10, 10, 52)).toBe(0);
    expect(carOffset(1, 10, 52)).toBe(9 * 52);
  });
  it("shrinks rows for taller buildings", () => {
    expect(rowHeight(5)).toBeGreaterThan(rowHeight(40));
  });
});

describe("<Building>", () => {
  it("draws one shaft per car with the car at its floor", () => {
    const state = building({
      elevators: [car({ id: 0, current_floor: 4 }), car({ id: 1, current_floor: 10 })],
    });
    render(<Building building={state} onHallCall={() => {}} />);
    const row = rowHeight(10);
    expect(screen.getByTestId("car-0")).toHaveStyle({ transform: `translateY(${6 * row}px)` });
    expect(screen.getByTestId("car-1")).toHaveStyle({ transform: "translateY(0px)" });
    expect(screen.getByTestId("car-1")).toHaveAttribute("data-motion", "idle");
  });

  it("omits the buttons that don't exist on the end floors", () => {
    render(<Building building={building()} onHallCall={() => {}} />);
    expect(screen.queryByLabelText(/floor 10, going up/)).toBeNull();
    expect(screen.queryByLabelText(/floor 1, going down/)).toBeNull();
    expect(screen.getAllByRole("button")).toHaveLength(18);
  });

  it("lights hall buttons with an outstanding call and reports presses", () => {
    const onHallCall = vi.fn();
    const state = building({
      hall_calls: { assigned: [{ floor: 7, direction: "DOWN", elevator_id: 0 }], pending: [] },
    });
    render(<Building building={state} onHallCall={onHallCall} />);
    const lit = screen.getByLabelText("Call a car to floor 7, going down");
    expect(lit).toHaveClass("lit");
    expect(screen.getByLabelText("Call a car to floor 7, going up")).not.toHaveClass("lit");

    fireEvent.click(screen.getByLabelText("Call a car to floor 3, going up"));
    expect(onHallCall).toHaveBeenCalledWith(3, "UP");
  });

  it("marks a car out of service", () => {
    const state = building({ elevators: [car({ in_maintenance: true, state: "MAINTENANCE" })] });
    render(<Building building={state} onHallCall={() => {}} />);
    expect(screen.getByTestId("shaft-0")).toHaveClass("maintenance");
    expect(screen.getByText("Out of service")).toBeInTheDocument();
  });
});

describe("heading arrows", () => {
  it("hides the arrow once a car has parked", () => {
    const state = building({ elevators: [car({ direction: "UP", current_floor: 5 })] });
    render(<Building building={state} onHallCall={() => {}} />);
    expect(screen.getByTestId("car-0")).not.toHaveTextContent("▲");
  });
  it("shows the arrow while the car travels", () => {
    const state = building({
      elevators: [car({ direction: "UP", state: "MOVING", current_floor: 5, stops: [8] })],
    });
    render(<Building building={state} onHallCall={() => {}} />);
    expect(screen.getByTestId("car-0")).toHaveTextContent("▲");
  });
});

describe("arriving at a floor", () => {
  afterEach(() => vi.useRealTimers());

  it("keeps the doors shut until the car has glided level with the floor", () => {
    vi.useFakeTimers();
    const moving = building({
      elevators: [car({ current_floor: 4, state: "MOVING", direction: "UP", stops: [5] })],
    });
    const { rerender } = render(<Building building={moving} onHallCall={() => {}} />);

    // the simulator reports the car at 5 with its doors open the moment the tick lands
    const arrived = building({
      elevators: [car({ current_floor: 5, direction: "UP", door: "OPEN" })],
    });
    rerender(<Building building={arrived} onHallCall={() => {}} />);
    const drawn = screen.getByTestId("car-0");
    expect(drawn).toHaveAttribute("data-doors", "closed");
    expect(drawn).toHaveAttribute("data-motion", "moving");

    // the glide takes one tick (1 s here), plus a frame or so of slack
    act(() => vi.advanceTimersByTime(1049));
    expect(drawn).toHaveAttribute("data-doors", "closed");
    act(() => vi.advanceTimersByTime(1));
    expect(drawn).toHaveAttribute("data-doors", "open");
    expect(drawn).toHaveAttribute("data-motion", "boarding");
  });

  it("opens straight away for a call at the floor the car is already on", () => {
    const parked = building({ elevators: [car({ current_floor: 3 })] });
    const { rerender } = render(<Building building={parked} onHallCall={() => {}} />);
    rerender(
      <Building building={building({ elevators: [car({ current_floor: 3, door: "OPEN" })] })} onHallCall={() => {}} />,
    );
    expect(screen.getByTestId("car-0")).toHaveAttribute("data-doors", "open");
  });
});
