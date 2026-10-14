import type { Elevator } from "../api";
import { motionOf } from "./Building";

interface Props {
  elevators: Elevator[];
  floors: number;
  onCabinCall: (elevatorId: number, floor: number) => void;
  onMaintenance: (elevatorId: number, inMaintenance: boolean) => void;
}

const MOTION_LABEL = {
  moving: "Moving",
  idle: "Idle",
  boarding: "Doors open",
  maintenance: "Out of service",
} as const;

export function CarPanels({ elevators, floors, onCabinCall, onMaintenance }: Props) {
  return (
    <section className="car-panels" aria-label="Elevator cars">
      {elevators.map((car) => {
        const motion = motionOf(car);
        const stops = new Set(car.stops);
        return (
          <article key={car.id} className="car-panel" data-testid={`panel-${car.id}`}>
            <header>
              <h2>Car #{car.id}</h2>
              <span className={`status-pill ${motion}`}>{MOTION_LABEL[motion]}</span>
            </header>
            <dl className="readout">
              <dt>Floor</dt>
              <dd>{car.current_floor}</dd>
              <dt>Direction</dt>
              <dd>{car.direction.toLowerCase()}</dd>
              <dt>Door</dt>
              <dd>{car.door.toLowerCase()}</dd>
              <dt>Stops</dt>
              <dd>{car.stops.length ? car.stops.join(", ") : "none"}</dd>
            </dl>
            <div className="keypad">
              {Array.from({ length: floors }, (_, i) => i + 1).map((floor) => (
                <button
                  key={floor}
                  className={stops.has(floor) ? "lit" : ""}
                  disabled={car.in_maintenance}
                  aria-label={`Car ${car.id}: go to floor ${floor}`}
                  onClick={() => onCabinCall(car.id, floor)}
                >
                  {floor}
                </button>
              ))}
            </div>
            <button className="maintenance-toggle" onClick={() => onMaintenance(car.id, !car.in_maintenance)}>
              {car.in_maintenance ? "Return to service" : "Take out of service"}
            </button>
          </article>
        );
      })}
    </section>
  );
}
