/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** When set, REST + WebSocket calls go here (e.g. `http://127.0.0.1:8001`). Dev default: same origin + Vite proxy. */
  readonly VITE_API_ORIGIN?: string;
}
