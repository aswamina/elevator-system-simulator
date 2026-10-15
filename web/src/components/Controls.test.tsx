import { fireEvent, render, screen } from "@testing-library/react";
import type { Building } from "../api";
import { Controls } from "./Controls";

function building(cars: number): Building {
  return {
    name: "test",
    floors: 10,
    tick: 0,
    clock: { running: true, paused: false, tick_interval: 1 },
    idle: true,
    elevators: Array.from({ length: cars }, (_, id) => ({
      id,
      current_floor: 1,
      direction: "IDLE" as const,
      state: "STOPPED" as const,
      door: "CLOSED" as const,
      in_maintenance: false,
      stops: [],
    })),
    hall_calls: { assigned: [], pending: [] },
  };
}

function setup(cars: number) {
  const onCarCount = vi.fn();
  render(
    <Controls
      building={building(cars)}
      onPause={() => {}}
      onStep={() => {}}
      onSpeed={() => {}}
      onCarCount={onCarCount}
      onReset={() => {}}
    />,
  );
  return onCarCount;
}

describe("car count stepper", () => {
  it("shows the current number of cars and steps it up or down", () => {
    const onCarCount = setup(3);
    expect(screen.getByRole("group", { name: "Number of cars" })).toHaveTextContent("3");
    fireEvent.click(screen.getByLabelText("Add a car"));
    expect(onCarCount).toHaveBeenLastCalledWith(4);
    fireEvent.click(screen.getByLabelText("Remove a car"));
    expect(onCarCount).toHaveBeenLastCalledWith(2);
  });

  it("won't go below one car", () => {
    setup(1);
    expect(screen.getByLabelText("Remove a car")).toBeDisabled();
  });

  it("won't go above twelve cars", () => {
    setup(12);
    expect(screen.getByLabelText("Add a car")).toBeDisabled();
  });
});
