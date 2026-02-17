const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = {
  track: (refId) => `${API_BASE}/track/${encodeURIComponent(refId)}`,
  dashboardSummary: `${API_BASE}/dashboard/summary`,
  mapWs: (host = window.location.hostname) => {
    const base = import.meta.env.VITE_WS_URL || `ws://${host}:8000`;
    return `${base}/dashboard/map/ws`;
  },
  truckGps: `${API_BASE}/truck/gps`,
  alerts: (truckId) => `${API_BASE}/alerts/${truckId}`,
};
