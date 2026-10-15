import { useState } from "react";
import type { ButtonEvent } from "../api";

export const PAGE_SIZE = 20;

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
  const [requestedPage, setPage] = useState(0);
  const pages = Math.max(1, Math.ceil(events.length / PAGE_SIZE));
  // the log can shrink under us (a new building clears it)
  const page = Math.min(requestedPage, pages - 1);
  const shown = events.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

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
              {shown.map((event) => (
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
      {pages > 1 && (
        <nav className="event-pager" aria-label="Event pages">
          <button onClick={() => setPage(page - 1)} disabled={page === 0} aria-label="Newer events">
            ‹ Newer
          </button>
          <span>
            Page {page + 1} of {pages}
          </span>
          <button onClick={() => setPage(page + 1)} disabled={page >= pages - 1} aria-label="Older events">
            Older ›
          </button>
        </nav>
      )}
    </aside>
  );
}
