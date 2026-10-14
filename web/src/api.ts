// Types mirror the response models in api.py.

export type Direction = "UP" | "DOWN" | "IDLE";
export type HallDirection = "UP" | "DOWN";
export type CarState = "MOVING" | "STOPPED" | "MAINTENANCE";
export type DoorState = "OPEN" | "CLOSED" | "OPENING" | "CLOSING";

export interface Elevator {
  id: number;
  current_floor: number;
  direction: Direction;
  state: CarState;
  door: DoorState;
  in_maintenance: boolean;
  stops: number[];
}

export interface Clock {
  running: boolean;
  paused: boolean;
  tick_interval: number;
}

export interface Building {
  name: string;
  floors: number;
  tick: number;
  clock: Clock;
  idle: boolean;
  elevators: Elevator[];
  hall_calls: {
    assigned: { floor: number; direction: HallDirection; elevator_id: number }[];
    pending: { floor: number; direction: HallDirection }[];
  };
}

// The API normally serves this app, so it lives at the same origin.
// Point the app at another server with ?api=http://host:port
const BASE = new URLSearchParams(window.location.search).get("api") ?? "";

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail =
        typeof err.detail === "string"
          ? err.detail
          : err.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch {
      // keep the status text
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  building: () => call<Building>("GET", "/api/building"),
  hallCall: (floor: number, direction: HallDirection) =>
    call("POST", "/api/hall-calls", { floor, direction }),
  cabinCall: (elevatorId: number, floor: number) =>
    call("POST", `/api/elevators/${elevatorId}/destinations`, { floor }),
  setMaintenance: (elevatorId: number, inMaintenance: boolean) =>
    call("PUT", `/api/elevators/${elevatorId}/maintenance`, { in_maintenance: inMaintenance }),
  setClock: (update: { paused?: boolean; tick_interval?: number }) =>
    call("PATCH", "/api/simulation", update),
  step: () => call("POST", "/api/simulation/tick"),
  reset: (name: string, floors: number, elevators: number) =>
    call("PUT", "/api/building", { name, floors, elevators }),
};
