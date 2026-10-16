import { api } from "./api";
import { Building } from "./components/Building";
import { CarPanels } from "./components/CarPanels";
import { Controls } from "./components/Controls";
import { EventTable } from "./components/EventTable";
import { useBuilding } from "./useBuilding";

export default function App() {
  const { building, events, error, act } = useBuilding();

  if (!building) {
    return <main className="loading">{error ?? "Connecting to the simulator…"}</main>;
  }

  return (
    <>
      <Controls
        building={building}
        onPause={(paused) => act(() => api.setClock({ paused }))}
        onStep={() => act(api.step)}
        onSpeed={(tick_interval) => act(() => api.setClock({ tick_interval }))}
        onCarCount={(cars) => act(() => api.setCarCount(cars))}
        onReset={(floors) => act(() => api.reset(building.name, floors, building.elevators.length))}
      />
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      <div className="workspace">
        <main className="scene">
          <Building building={building} onHallCall={(floor, dir) => act(() => api.hallCall(floor, dir))} />
        </main>
        <EventTable events={events} />
      </div>
      <CarPanels
        elevators={building.elevators}
        floors={building.floors}
        onCabinCall={(id, floor) => act(() => api.cabinCall(id, floor))}
        onMaintenance={(id, on) => act(() => api.setMaintenance(id, on))}
      />
    </>
  );
}
