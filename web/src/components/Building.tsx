import { useEffect, useState, type CSSProperties } from "react";
import type { Building as BuildingState, Elevator, HallDirection } from "../api";

/** Height of one floor in px; shorter for tall buildings so they still fit. */
export function rowHeight(floors: number): number {
  if (floors <= 8) return 64;
  if (floors <= 15) return 52;
  if (floors <= 30) return 40;
  return 32;
}

/** Distance from the top of the shaft to the top of a car standing at `floor`. */
export function carOffset(floor: number, floors: number, row: number): number {
  return (floors - floor) * row;
}

export type Motion = "moving" | "idle" | "boarding" | "maintenance";

export function motionOf(car: Elevator): Motion {
  if (car.in_maintenance) return "maintenance";
  if (car.state === "MOVING") return "moving";
  if (car.door !== "CLOSED") return "boarding";
  return car.stops.length ? "moving" : "idle";
}

const ARROW = { UP: "▲", DOWN: "▼", IDLE: "" } as const;

/** The car keeps its last heading after it parks; only show it while it has work. */
function headingArrow(car: Elevator): string {
  const motion = motionOf(car);
  return motion === "idle" || motion === "maintenance" ? "" : ARROW[car.direction];
}

interface Props {
  building: BuildingState;
  onHallCall: (floor: number, direction: HallDirection) => void;
}

export function Building({ building, onHallCall }: Props) {
  const { floors, elevators } = building;
  const row = rowHeight(floors);
  const floorsTopDown = Array.from({ length: floors }, (_, i) => floors - i);
  const waiting = new Set(
    [...building.hall_calls.assigned, ...building.hall_calls.pending].map(
      (c) => `${c.floor}-${c.direction}`,
    ),
  );

  const travelSeconds = building.clock.paused ? 0.3 : building.clock.tick_interval;
  const style = {
    "--floors": floors,
    "--cars": elevators.length,
    "--row": `${row}px`,
    // a car moves one floor per tick, so spreading each move over the tick
    // makes the motion continuous instead of jumping floor to floor
    "--tick": `${travelSeconds}s`,
    // doors slide within half a tick, so they're shut before the car can move off
    "--door-time": `${Math.min(0.6, travelSeconds / 2)}s`,
  } as CSSProperties;

  return (
    <div className="building" style={style}>
      <div className="roof">
        <div className="roof-spacer" />
        {elevators.map((car) => (
          <MachineRoom key={car.id} car={car} />
        ))}
      </div>

      <div className="interior">
        {floorsTopDown.map((floor, i) => (
          <div key={floor} className="floor-row" style={{ gridRow: i + 1 }}>
            <span className="floor-number">{floor}</span>
            <div className="hall-panel">
              {floor < floors && (
                <HallButton floor={floor} direction="UP" lit={waiting.has(`${floor}-UP`)} onPress={onHallCall} />
              )}
              {floor > 1 && (
                <HallButton floor={floor} direction="DOWN" lit={waiting.has(`${floor}-DOWN`)} onPress={onHallCall} />
              )}
            </div>
          </div>
        ))}
        {elevators.map((car, i) => (
          <Shaft key={car.id} car={car} column={i + 3} floors={floors} row={row} travelMs={travelSeconds * 1000} />
        ))}
      </div>

      <div className="ground" />
    </div>
  );
}

function HallButton({
  floor,
  direction,
  lit,
  onPress,
}: {
  floor: number;
  direction: HallDirection;
  lit: boolean;
  onPress: (floor: number, direction: HallDirection) => void;
}) {
  return (
    <button
      className={`hall-button${lit ? " lit" : ""}`}
      aria-label={`Call a car to floor ${floor}, going ${direction.toLowerCase()}`}
      aria-pressed={lit}
      onClick={() => onPress(floor, direction)}
    >
      {ARROW[direction]}
    </button>
  );
}

function MachineRoom({ car }: { car: Elevator }) {
  const motion = motionOf(car);
  return (
    <div className={`machine-room ${motion}`}>
      <div className={`sheave ${motion === "moving" ? `spin-${car.direction.toLowerCase()}` : ""}`} />
      <div className="indicator" aria-label={`Car ${car.id} at floor ${car.current_floor}`}>
        <span className={`indicator-arrow ${motion}`}>{headingArrow(car)}</span>
        <span className="indicator-floor">{car.in_maintenance ? "--" : car.current_floor}</span>
      </div>
    </div>
  );
}

/**
 * The floor the drawn car has finished gliding to. The simulator reports a car
 * at its new floor (doors already open, if it stops there) the moment the tick
 * lands, while the drawing still takes `travelMs` to get it there.
 */
export function useSettledFloor(floor: number, travelMs: number): number {
  const [settled, setSettled] = useState(floor);
  useEffect(() => {
    if (floor === settled) return;
    // a little slack, since the CSS transition starts a frame after the render
    const id = window.setTimeout(() => setSettled(floor), travelMs + 50);
    return () => window.clearTimeout(id);
  }, [floor, settled, travelMs]);
  return settled;
}

function Shaft({
  car,
  column,
  floors,
  row,
  travelMs,
}: {
  car: Elevator;
  column: number;
  floors: number;
  row: number;
  travelMs: number;
}) {
  const arrived = useSettledFloor(car.current_floor, travelMs) === car.current_floor;
  // keep the doors shut and the car "moving" until it is level with the landing
  const doorsOpen = arrived && car.door !== "CLOSED";
  const motion = !arrived && !car.in_maintenance ? "moving" : motionOf(car);
  const offset = carOffset(car.current_floor, floors, row);
  // the counterweight hangs on the other end of the rope, so it travels the opposite way
  const counterweight = (car.current_floor - 1) * row;

  return (
    <div
      className={`shaft ${motion}`}
      style={{ gridColumn: column }}
      data-testid={`shaft-${car.id}`}
    >
      <div className={`rope dir-${car.direction.toLowerCase()}`} style={{ height: offset + 4 }} />
      <div className="counterweight" style={{ transform: `translateY(${counterweight}px)` }} />
      <div
        className={`car ${motion}`}
        style={{ transform: `translateY(${offset}px)` }}
        data-testid={`car-${car.id}`}
        data-motion={motion}
        data-floor={car.current_floor}
        data-doors={doorsOpen ? "open" : "closed"}
      >
        <div className="car-header">
          <span>#{car.id}</span>
          <span className={`car-arrow ${motion}`}>{headingArrow(car)}</span>
        </div>
        <div className="cabin">
          <div className="cabin-light" />
          <div className={`door left ${doorsOpen ? "open" : ""}`} />
          <div className={`door right ${doorsOpen ? "open" : ""}`} />
          {car.in_maintenance && <div className="out-of-service">Out of service</div>}
        </div>
      </div>
    </div>
  );
}
