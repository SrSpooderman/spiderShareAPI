export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  useMocks: (import.meta.env.VITE_USE_MOCKS ?? "true") !== "false",
  appEnv: import.meta.env.MODE
};
