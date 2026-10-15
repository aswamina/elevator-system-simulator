import { useEffect, useState, type FormEvent } from "react";
import type { Building } from "../api";

const MAX_CARS = 12;

const SPEEDS = [
  { label: "0.5×", interval: 2 },
  { label: "1×", interval: 1 },
  { label: "2×", interval: 0.5 },
  { label: "4×", interval: 0.25 },
];

interface Props {
  building: Building;
  onPause: (paused: boolean) => void;
  onStep: () => void;
  onSpeed: (tickInterval: number) => void;
  onCarCount: (elevators: number) => void;
  onReset: (floors: number) => void;
}

export function Controls({ building, onPause, onStep, onSpeed, onCarCount, onReset }: Props) {
  const { clock } = building;
  const cars = building.elevators.length;
  const [floors, setFloors] = useState(building.floors);

  // follow the building when it changes underneath the form
  useEffect(() => setFloors(building.floors), [building.floors]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    onReset(floors);
  };

  return (
    <header className="controls">
      <div className="title">
        <h1>{building.name}</h1>
        <span className="tick">
          Tick <strong>{building.tick}</strong>
        </span>
      </div>
      <div className="control-group">
        <button onClick={() => onPause(!clock.paused)}>{clock.paused ? "Resume" : "Pause"}</button>
        <button onClick={onStep} disabled={!clock.paused} title="Advance one tick">
          Step
        </button>
        <label>
          Speed
          <select value={String(clock.tick_interval)} onChange={(e) => onSpeed(Number(e.target.value))}>
            {!SPEEDS.some((s) => s.interval === clock.tick_interval) && (
              <option value={String(clock.tick_interval)}>{clock.tick_interval}s/tick</option>
            )}
            {SPEEDS.map((s) => (
              <option key={s.interval} value={String(s.interval)}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="control-group stepper" role="group" aria-label="Number of cars">
        <span>Cars</span>
        <button onClick={() => onCarCount(cars - 1)} disabled={cars <= 1} aria-label="Remove a car">
          −
        </button>
        <output aria-live="polite">{cars}</output>
        <button onClick={() => onCarCount(cars + 1)} disabled={cars >= MAX_CARS} aria-label="Add a car">
          +
        </button>
      </div>
      <form className="control-group" onSubmit={submit}>
        <label>
          Floors
          <input type="number" min={2} max={60} value={floors} onChange={(e) => setFloors(Number(e.target.value))} />
        </label>
        <button type="submit" title="Start over with an empty building">
          New building
        </button>
      </form>
    </header>
  );
}
