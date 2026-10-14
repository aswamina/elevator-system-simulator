import { api } from "./api";
import { Building } from "./components/Building";
import { CarPanels } from "./components/CarPanels";
import { Controls } from "./components/Controls";
import { useBuilding } from "./useBuilding";

export default function App() {
  const { building, error, act } = useBuilding();

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
        onReset={(floors, cars) => act(() => api.reset(building.name, floors, cars))}
      />
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      <main className="scene">
        <Building building={building} onHallCall={(floor, dir) => act(() => api.hallCall(floor, dir))} />
      </main>
      <CarPanels
        elevators={building.elevators}
        floors={building.floors}
        onCabinCall={(id, floor) => act(() => api.cabinCall(id, floor))}
        onMaintenance={(id, on) => act(() => api.setMaintenance(id, on))}
      />
    </>
  );
}
