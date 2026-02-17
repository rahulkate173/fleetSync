import { useEffect, useRef, useState } from "react";
import "leaflet/dist/leaflet.css";
const FleetHtmlMap = () => {
  const mapRef = useRef(null);
  const [speed, setSpeed] = useState(1);
  const [liveVehicles, setLiveVehicles] = useState([]);
  const markersRef = useRef({});

  const wsUrl = () => {
    const base = import.meta.env.VITE_API_URL || "http://localhost:8000";
    return base.replace(/^http/, "ws") + "/dashboard/map/ws";
  };

  useEffect(() => {
    let ws;
    try {
      ws = new WebSocket(wsUrl());
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          setLiveVehicles(Array.isArray(data) ? data : []);
        } catch {}
      };
      ws.onclose = () => setLiveVehicles([]);
    } catch (e) {
      console.warn("WebSocket not available", e);
    }
    return () => ws?.close();
  }, []);

  useEffect(() => {
    const leafletScript = document.createElement("script");
    leafletScript.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
    leafletScript.async = true;
    document.body.appendChild(leafletScript);

    const movingMarkerScript = document.createElement("script");
    movingMarkerScript.src = "https://rawcdn.githack.com/ewoken/Leaflet.MovingMarker/master/MovingMarker.js";
    movingMarkerScript.async = true;
    document.body.appendChild(movingMarkerScript);

    let mapInstance;
    let vehicleMarkers = {};

    leafletScript.onload = () => {
      movingMarkerScript.onload = () => {
        if (!window.L || !mapRef.current) return;
        if (mapInstance) mapInstance.remove();
        mapInstance = window.L.map(mapRef.current).setView([18.5167, 73.92], 13);
        window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19 }).addTo(mapInstance);

        const stops = [
          { name: "Lone", coord: [18.488704515525065, 74.02516910447125] },
          { name: "Hadapsar Gadital", coord: [18.501101821815556, 73.937915200395] },
          { name: "Swargate Bus Stand", coord: [18.500843023224533, 73.85923150489732] },
        ];
        const coords = stops.map((s) => s.coord);
        const routeLayer = window.L.polyline(coords, { color: "#1976d2", weight: 4 }).addTo(mapInstance);
        mapInstance.fitBounds(routeLayer.getBounds().pad(0.2));

        let buses = [], busSeq = 0, globalSpeed = 1.0;

        const addLiveVehicle = (v) => {
          const gps = v?.gps || {};
          const lat = gps.lat; const lon = gps.lon;
          if (lat == null || lon == null) return;
          if (vehicleMarkers[v.vehicle_id]) {
            vehicleMarkers[v.vehicle_id].setLatLng([lat, lon]);
            return;
          }
          const m = window.L.marker([lat, lon])
            .addTo(mapInstance)
            .bindPopup(`<b>${v.vehicle_id}</b><br>Speed: ${gps.speed_kmh ?? 0} km/h`);
          vehicleMarkers[v.vehicle_id] = m;
        };

        const removeLiveVehicle = (vid) => {
          if (vehicleMarkers[vid]) {
            mapInstance.removeLayer(vehicleMarkers[vid]);
            delete vehicleMarkers[vid];
          }
        };

        window.addEventListener("fleetmap-add-bus", () => {
          if (stops.length < 2) return;
          const colors = ["#1976d2", "#d32f2f", "#2e7d32", "#ff9800"];
          const id = ++busSeq, color = colors[Math.floor(Math.random() * colors.length)];
          const msArr = Array(stops.length - 1).fill(2000 / globalSpeed);
          const marker = window.L.Marker.movingMarker(stops.map(s => s.coord), msArr, { autostart: false, loop: true });
          marker.setIcon(window.L.divIcon({ html: `<div style='padding:4px 6px;background:${color};color:#fff;border-radius:6px'>BUS ${id}</div>` }));
          marker.addTo(mapInstance).bindPopup(`<b>Bus ${id}</b>`);
          buses.push({ id, marker });
        });
        window.addEventListener("fleetmap-play", () => buses.forEach(b => { try { b.marker.start(); } catch {} }));
        window.addEventListener("fleetmap-pause", () => buses.forEach(b => { try { b.marker.pause(); } catch {} }));
        window.addEventListener("fleetmap-reset", () => buses.forEach(b => { try { b.marker.stop(); b.marker.setLatLng(stops[0].coord); } catch {} }));
        window.addEventListener("fleetmap-speed", (e) => { globalSpeed = e.detail; });

        markersRef.current = { addLiveVehicle, removeLiveVehicle, vehicleIds: new Set() };
      };
    };

    return () => {
      if (mapInstance) mapInstance.remove();
      try {
        document.body.removeChild(leafletScript);
        document.body.removeChild(movingMarkerScript);
      } catch {}
    };
  }, []);

  useEffect(() => {
    const { addLiveVehicle, removeLiveVehicle, vehicleIds } = markersRef.current;
    if (!addLiveVehicle) return;
    const currentIds = new Set(liveVehicles.map((v) => v.vehicle_id));
    liveVehicles.forEach((v) => addLiveVehicle(v));
    vehicleIds.forEach((vid) => { if (!currentIds.has(vid)) removeLiveVehicle(vid); });
    liveVehicles.forEach((v) => vehicleIds.add(v.vehicle_id));
  }, [liveVehicles]);

  return (
    <div style={{ width: "100%", borderRadius: "10px", overflow: "hidden" }}>
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 8, flexWrap: "wrap" }}>
        <span style={{ fontSize: 12, color: "#666" }}>
          {liveVehicles.length > 0 ? `Live: ${liveVehicles.length} vehicle(s)` : "Live map (WebSocket)"}
        </span>
        <button onClick={() => window.dispatchEvent(new CustomEvent("fleetmap-add-bus"))}>Add Bus (Sim)</button>
        <button onClick={() => window.dispatchEvent(new CustomEvent("fleetmap-play"))}>Play</button>
        <button onClick={() => window.dispatchEvent(new CustomEvent("fleetmap-pause"))}>Pause</button>
        <button onClick={() => window.dispatchEvent(new CustomEvent("fleetmap-reset"))}>Reset</button>
        <label style={{ marginLeft: 12 }}>
          Speed ×
          <input
            type="range"
            min="0.25"
            max="4"
            step="0.05"
            value={speed}
            onChange={(e) => {
              setSpeed(e.target.value);
              window.dispatchEvent(new CustomEvent("fleetmap-speed", { detail: parseFloat(e.target.value) }));
            }}
            style={{ margin: "0 8px", verticalAlign: "middle" }}
          />
          <span>{parseFloat(speed).toFixed(2)}x</span>
        </label>
      </div>
      <div style={{ width: "100%", height: "350px" }}>
        <div ref={mapRef} style={{ width: "100%", height: "100%" }} />
      </div>
    </div>
  );
};

export default FleetHtmlMap;
