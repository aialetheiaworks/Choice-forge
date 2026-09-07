import { create } from "zustand";
import { checkHealth } from "../api/client";

const STORAGE_KEY = "choice-forge:api-base-url";
const DEFAULT_URL = "http://localhost:8000";

type Status = "idle" | "checking" | "connected" | "error";

interface ConnectionState {
  baseUrl: string;
  status: Status;
  error: string | null;
  rolesCount: number | null;
  setBaseUrl: (url: string) => void;
  connect: (url: string) => Promise<boolean>;
  disconnect: () => void;
}

function readStoredUrl(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) || DEFAULT_URL;
  } catch {
    return DEFAULT_URL;
  }
}

export const useConnectionStore = create<ConnectionState>((set) => ({
  baseUrl: readStoredUrl(),
  status: "idle",
  error: null,
  rolesCount: null,

  setBaseUrl: (url) => set({ baseUrl: url }),

  connect: async (url) => {
    set({ status: "checking", error: null });
    try {
      const health = await checkHealth(url);
      try {
        localStorage.setItem(STORAGE_KEY, url);
      } catch {
        /* private-browsing or storage disabled — connection still works */
      }
      set({
        status: "connected",
        baseUrl: url,
        rolesCount: health.roles?.length ?? null,
        error: null,
      });
      return true;
    } catch (e) {
      set({ status: "error", error: e instanceof Error ? e.message : String(e) });
      return false;
    }
  },

  disconnect: () => set({ status: "idle", error: null, rolesCount: null }),
}));
