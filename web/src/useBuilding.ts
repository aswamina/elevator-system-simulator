import { useCallback, useEffect, useState } from "react";
import { api, type Building } from "./api";

const POLL_MS = 150;

/** Polls the simulator, and wraps actions so errors surface and state refreshes. */
export function useBuilding() {
  const [building, setBuilding] = useState<Building | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setBuilding(await api.building());
      setError((e) => (e?.startsWith("Can't reach") ? null : e));
    } catch (e) {
      setError(`Can't reach the simulator API: ${(e as Error).message}`);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = window.setInterval(refresh, POLL_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  const act = useCallback(
    async (action: () => Promise<unknown>) => {
      try {
        await action();
        setError(null);
      } catch (e) {
        setError((e as Error).message);
      }
      await refresh();
    },
    [refresh],
  );

  return { building, error, act };
}
