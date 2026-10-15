import type { ButtonEvent } from "../api";

const ARROW = { UP: "▲", DOWN: "▼" } as const;

/** "09:41:07" in the viewer's local time. */
export function clockTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
}

function describe(event: ButtonEvent): string {
  if (event.kind === "hall") return `Hall, floor ${event.floor} ${ARROW[event.direction ?? "UP"]}`;
  return `In car #${event.car_id}, to ${event.floor}`;
}

function Served({ event }: { event: ButtonEvent }) {
  if (event.status === "waiting") return <span className="event-pill waiting">Waiting</span>;
  if (event.status === "cancelled") return <span className="event-pill cancelled">Cancelled</span>;
  const ticks = (event.served_tick ?? 0) - event.pressed_tick;
  return (
    <span title={`${ticks} tick${ticks === 1 ? "" : "s"} after the press`}>
      {clockTime(event.served_at!)} <span className="event-wait">+{ticks}</span>
    </span>
  );
}

export function EventTable({ events }: { events: ButtonEvent[] }) {
  return (
    <aside className="event-log" aria-label="Button presses">
      <header>
        <h2>Events</h2>
        <span className="event-count">{events.filter((e) => e.status === "waiting").length} waiting</span>
      </header>
      {events.length === 0 ? (
        <p className="event-empty">Press a hall or cabin button and it shows up here.</p>
      ) : (
        <div className="event-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Time</th>
                <th scope="col">Button</th>
                <th scope="col">Car</th>
                <th scope="col">Served</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id} className={`event-row kind-${event.kind} ${event.status}`} data-testid={`event-${event.id}`}>
                  <td className="event-time">{clockTime(event.pressed_at)}</td>
                  <td>{describe(event)}</td>
                  <td className="event-car">
                    {event.car_id === null ? "—" : `#${event.car_id}`}
                  </td>
                  <td>
                    <Served event={event} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </aside>
  );
}
