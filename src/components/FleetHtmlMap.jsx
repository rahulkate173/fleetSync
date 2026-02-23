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
  // FETCH TRUCK DATA FROM REST API
  // ================================
  const fetchTruckData = async () => {
    try {
      const response = await fetch(`${API_URL}/truck/gps`);
      const data = await response.json();

      if (Array.isArray(data)) {
        setLiveVehicles(data);
      }
    } catch (error) {
      console.error("Error fetching truck data:", error);
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
        [18.5204, 73.8567], // Default center (Pune)
        12
      );

      window.L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        { maxZoom: 19 }
      ).addTo(map);

      mapInstanceRef.current = map;

      // Initial API call
      fetchTruckData();

      // Refresh every 30 seconds
      const interval = setInterval(fetchTruckData, 30000);

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
    const currentTruckIds = new Set();

    liveVehicles.forEach((truck) => {
      const { truck_id, latitude, longitude, status, timestamp } = truck;

      if (!latitude || !longitude) return;

      currentTruckIds.add(truck_id);

      // If marker already exists → update position
      if (existingMarkers[truck_id]) {
        existingMarkers[truck_id].setLatLng([latitude, longitude]);
        existingMarkers[truck_id].setPopupContent(`
          <b>Truck:</b> ${truck_id}<br/>
          <b>Status:</b> ${status}<br/>
          <b>Updated:</b> ${new Date(timestamp).toLocaleTimeString()}
        `);
      } else {
        // Create new marker
        const marker = window.L.marker([latitude, longitude])
          .addTo(map)
          .bindPopup(`
            <b>Truck:</b> ${truck_id}<br/>
            <b>Status:</b> ${status}<br/>
            <b>Updated:</b> ${new Date(timestamp).toLocaleTimeString()}
          `);

        existingMarkers[truck_id] = marker;
      }
    });

    // Remove trucks not in latest response
    Object.keys(existingMarkers).forEach((id) => {
      if (!currentTruckIds.has(id)) {
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
          ? `Live: ${liveVehicles.length} truck(s)`
          : "Waiting for truck data..."}
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