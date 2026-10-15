import { fireEvent, render, screen, within } from "@testing-library/react";
import type { ButtonEvent } from "../api";
import { EventTable } from "./EventTable";

const base = {
  pressed_at: "2026-10-15T09:00:00+00:00",
  pressed_tick: 2,
  served_at: null,
  served_tick: null,
};

const events: ButtonEvent[] = [
  { ...base, id: 3, kind: "cabin", floor: 7, direction: null, car_id: 1, status: "waiting" },
  {
    ...base,
    id: 2,
    kind: "hall",
    floor: 4,
    direction: "DOWN",
    car_id: 0,
    status: "served",
    served_at: "2026-10-15T09:00:05+00:00",
    served_tick: 7,
  },
  { ...base, id: 1, kind: "cabin", floor: 9, direction: null, car_id: 2, status: "cancelled" },
];

describe("<EventTable>", () => {
  it("lists each press with its button, car and outcome", () => {
    render(<EventTable events={events} />);
    const cabin = within(screen.getByTestId("event-3"));
    expect(cabin.getByText("In car #1, to 7")).toBeInTheDocument();
    expect(cabin.getByText("#1")).toBeInTheDocument();
    expect(cabin.getByText("Waiting")).toBeInTheDocument();

    const hall = within(screen.getByTestId("event-2"));
    expect(hall.getByText("Hall, floor 4 ▼")).toBeInTheDocument();
    expect(hall.getByText("#0")).toBeInTheDocument();
    expect(hall.getByText("+5")).toBeInTheDocument();

    expect(within(screen.getByTestId("event-1")).getByText("Cancelled")).toBeInTheDocument();
    expect(screen.getByText("1 waiting")).toBeInTheDocument();
  });

  it("shows a dash while a hall call has no car yet", () => {
    render(
      <EventTable
        events={[{ ...base, id: 1, kind: "hall", floor: 5, direction: "UP", car_id: null, status: "waiting" }]}
      />,
    );
    expect(within(screen.getByTestId("event-1")).getByText("—")).toBeInTheDocument();
  });

  it("explains itself when empty", () => {
    render(<EventTable events={[]} />);
    expect(screen.getByText(/shows up here/)).toBeInTheDocument();
  });
});

describe("paging", () => {
  const many: ButtonEvent[] = Array.from({ length: 45 }, (_, i) => ({
    ...base,
    id: 45 - i,
    kind: "hall" as const,
    floor: (i % 9) + 1,
    direction: "UP" as const,
    car_id: 0,
    status: "waiting" as const,
  }));

  it("shows 20 events a page, newest first, and pages through the rest", () => {
    render(<EventTable events={many} />);
    expect(screen.getAllByTestId(/^event-/)).toHaveLength(20);
    expect(screen.getByTestId("event-45")).toBeInTheDocument();
    expect(screen.getByText("Page 1 of 3")).toBeInTheDocument();
    expect(screen.getByLabelText("Newer events")).toBeDisabled();

    fireEvent.click(screen.getByLabelText("Older events"));
    expect(screen.getByText("Page 2 of 3")).toBeInTheDocument();
    expect(screen.getByTestId("event-25")).toBeInTheDocument();
    expect(screen.queryByTestId("event-45")).toBeNull();

    fireEvent.click(screen.getByLabelText("Older events"));
    expect(screen.getAllByTestId(/^event-/)).toHaveLength(5);
    expect(screen.getByLabelText("Older events")).toBeDisabled();

    fireEvent.click(screen.getByLabelText("Newer events"));
    expect(screen.getByText("Page 2 of 3")).toBeInTheDocument();
  });

  it("hides the pager when everything fits on one page", () => {
    render(<EventTable events={many.slice(0, 20)} />);
    expect(screen.queryByRole("navigation", { name: "Event pages" })).toBeNull();
  });

  it("falls back to the last page when the log shrinks", () => {
    const { rerender } = render(<EventTable events={many} />);
    fireEvent.click(screen.getByLabelText("Older events"));
    fireEvent.click(screen.getByLabelText("Older events"));
    rerender(<EventTable events={many.slice(0, 30)} />);
    expect(screen.getByText("Page 2 of 2")).toBeInTheDocument();
  });
});
