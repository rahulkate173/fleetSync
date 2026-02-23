import { useEffect, useRef, useState } from "react";
import "leaflet/dist/leaflet.css";

const FleetHtmlMap = () => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef({});
  const [liveVehicles, setLiveVehicles] = useState([]);

  const API_URL =
    import.meta.env.VITE_API_URL || "http://localhost:8000";

  // ================================
  // FETCH VEHICLE DATA
  // ================================
  const fetchVehicleData = async () => {
    try {
      const response = await fetch(`${API_URL}/dashboard/map/data`);
      const data = await response.json();

      // If backend returns single object → convert to array
      if (!Array.isArray(data)) {
        setLiveVehicles([data]);
      } else {
        setLiveVehicles(data);
      }
    } catch (error) {
      console.error("Error fetching vehicle data:", error);
    }
  };

  // ======================================
  // LOAD LEAFLET MAP (ONLY ONCE)
  // ======================================
  useEffect(() => {
    const leafletScript = document.createElement("script");
    leafletScript.src =
      "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
    leafletScript.async = true;
    document.body.appendChild(leafletScript);

    leafletScript.onload = () => {
      if (!window.L || !mapRef.current) return;

      const map = window.L.map(mapRef.current).setView(
        [18.5204, 73.8567], // Pune default
        12
      );

      window.L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        { maxZoom: 19 }
      ).addTo(map);

      mapInstanceRef.current = map;

      fetchVehicleData();
      const interval = setInterval(fetchVehicleData, 10000); // every 10 sec

      return () => clearInterval(interval);
    };

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
      }
      try {
        document.body.removeChild(leafletScript);
      } catch {}
    };
  }, []);

  // ======================================
  // UPDATE MARKERS WHEN DATA CHANGES
  // ======================================
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const existingMarkers = markersRef.current;
    const currentVehicleIds = new Set();

    liveVehicles.forEach((vehicle) => {
      const {
        vehicle_id,
        lat,
        lon,
        speed_kmh,
        temperature,
        reference_id,
      } = vehicle;

      if (!lat || !lon) return;

      currentVehicleIds.add(vehicle_id);

      const popupContent = `
        <b>Vehicle:</b> ${vehicle_id}<br/>
        <b>Speed:</b> ${speed_kmh} km/h<br/>
        <b>Temperature:</b> ${temperature}°C<br/>
        <b>Reference ID:</b> ${reference_id}
      `;

      // Update existing marker
      if (existingMarkers[vehicle_id]) {
        existingMarkers[vehicle_id].setLatLng([lat, lon]);
        existingMarkers[vehicle_id].setPopupContent(popupContent);
      } else {
        // Create new marker
        const marker = window.L.marker([lat, lon])
          .addTo(map)
          .bindPopup(popupContent);

        existingMarkers[vehicle_id] = marker;
      }
    });

    // Remove vehicles not in latest API response
    Object.keys(existingMarkers).forEach((id) => {
      if (!currentVehicleIds.has(id)) {
        map.removeLayer(existingMarkers[id]);
        delete existingMarkers[id];
      }
    });
  }, [liveVehicles]);

  return (
    <div
      style={{
        width: "100%",
        borderRadius: "10px",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          fontSize: 12,
          marginBottom: 8,
          color: "#666",
        }}
      >
        {liveVehicles.length > 0
          ? `Live: ${liveVehicles.length} vehicle(s)`
          : "Waiting for vehicle data..."}
      </div>

      <div style={{ width: "100%", height: "400px" }}>
        <div
          ref={mapRef}
          style={{ width: "100%", height: "100%" }}
        />
      </div>
    </div>
  );
};

export default FleetHtmlMap;