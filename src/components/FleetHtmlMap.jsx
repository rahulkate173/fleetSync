


import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const FleetHtmlMap = () => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef({});
  const [liveVehicles, setLiveVehicles] = useState([]);

  const API_URL = "https://server-production-cd13.up.railway.app/";

  // ================================
  // FETCH DRIVER DATA
  // ================================
  const fetchTruckData = async () => {
    try {
      const response = await fetch(`${API_URL}/dashboard/map/data`);
      const data = await response.json();

      if (Array.isArray(data)) {
        setLiveVehicles(data);
      }
    } catch (error) {
      console.error("Error fetching truck data:", error);
    }
  };

  // ======================================
  // INITIALIZE MAP (RUN ONCE)
  // ======================================
  useEffect(() => {
    if (mapInstanceRef.current) return;

    const map = L.map(mapRef.current).setView(
      [18.5204, 73.8567],
      12
    );

    L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      { maxZoom: 19 }
    ).addTo(map);

    mapInstanceRef.current = map;

    fetchTruckData();
    const interval = setInterval(fetchTruckData, 5000);

    return () => {
      clearInterval(interval);
      map.remove();
    };
  }, []);

  // ======================================
  // UPDATE MARKERS
  // ======================================
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const existingMarkers = markersRef.current;
    const currentIds = new Set();

    liveVehicles.forEach((vehicle) => {
      const lat = vehicle?.gps?.lat;
      const lng = vehicle?.gps?.lon;
      const driver_id = vehicle?.vehicle_id;

      if (!lat || !lng || !driver_id) return;

      currentIds.add(driver_id);

      if (existingMarkers[driver_id]) {
        existingMarkers[driver_id].setLatLng([lat, lng]);
      } else {
        const marker = L.marker([lat, lng])
          .addTo(map)
          .bindPopup(`<b>Driver:</b> ${driver_id}`);

        existingMarkers[driver_id] = marker;
      }
    });

    // Remove old markers
    Object.keys(existingMarkers).forEach((id) => {
      if (!currentIds.has(id)) {
        map.removeLayer(existingMarkers[id]);
        delete existingMarkers[id];
      }
    });
  }, [liveVehicles]);

  return (
    <div style={{ width: "100%" }}>
      <div style={{ fontSize: 12, marginBottom: 8 }}>
        {liveVehicles.length > 0
          ? <>Live: {liveVehicles.length} driver(s)</>
          : "Waiting for driver data..."}
      </div>

      <div
        ref={mapRef}
        style={{ width: "100%", height: "400px" }}
      />
    </div>
  );
};

export default FleetHtmlMap;