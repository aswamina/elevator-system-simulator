import { useEffect, useState, type FormEvent } from "react";
import type { Building } from "../api";

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
  onReset: (floors: number, elevators: number) => void;
}

export function Controls({ building, onPause, onStep, onSpeed, onReset }: Props) {
  const { clock } = building;
  const [floors, setFloors] = useState(building.floors);
  const [cars, setCars] = useState(building.elevators.length);

  // follow the building when it changes underneath the form
  useEffect(() => setFloors(building.floors), [building.floors]);
  useEffect(() => setCars(building.elevators.length), [building.elevators.length]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    onReset(floors, cars);
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
      <form className="control-group" onSubmit={submit}>
        <label>
          Floors
          <input type="number" min={2} max={60} value={floors} onChange={(e) => setFloors(Number(e.target.value))} />
        </label>
        <label>
          Cars
          <input type="number" min={1} max={12} value={cars} onChange={(e) => setCars(Number(e.target.value))} />
        </label>
        <button type="submit">New building</button>
      </form>
    </header>
  );
}
