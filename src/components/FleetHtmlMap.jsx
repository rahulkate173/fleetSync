import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const FleetHtmlMap = () => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef({});
  const routeLayersRef = useRef([]);

  const [liveVehicles, setLiveVehicles] = useState([]);

  const API_URL = "http://localhost:8000";
  const ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjA3YTk2ZjZlMDRmZTRiZDhiZDI2NDQ0MTE4NTZiYzQ5IiwiaCI6Im11cm11cjY0In0=";

  // ================================
  // STATIC DELIVERY POINTS
  // ================================
  const jobs = [
    { id: 1, location: [73.87, 18.53] },
    { id: 2, location: [73.88, 18.54] },
    { id: 3, location: [73.89, 18.55] },
    { id: 4, location: [73.90, 18.56] }
  ];

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
  // INITIALIZE MAP
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
  // UPDATE DRIVER MARKERS
  // ======================================
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const existingMarkers = markersRef.current;
    const currentIds = new Set();

    liveVehicles.forEach((vehicle) => {
      const lat = vehicle.gps?.lat;
      const lng = vehicle.gps?.lon;
      const driver_id = vehicle.vehicle_id;

      if (!lat || !lng) return;

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

    Object.keys(existingMarkers).forEach((id) => {
      if (!currentIds.has(id)) {
        map.removeLayer(existingMarkers[id]);
        delete existingMarkers[id];
      }
    });
  }, [liveVehicles]);

  // ======================================
  // OPTIMIZE ROUTES
  // ======================================
  const optimizeRoutes = async () => {
    if (liveVehicles.length === 0) {
      alert("No drivers available.");
      return;
    }

    const map = mapInstanceRef.current;

    // Clear old routes
    routeLayersRef.current.forEach((layer) => {
      map.removeLayer(layer);
    });
    routeLayersRef.current = [];

    // Convert drivers to ORS vehicles
    const vehicles = liveVehicles.map((vehicle, index) => ({
      id: index + 1,
      profile: "driving-car",
      start: [vehicle.gps.lon, vehicle.gps.lat],
      end: [vehicle.gps.lon, vehicle.gps.lat]
    }));

    const body = {
      jobs,
      vehicles
    };

    try {
      const response = await fetch(
        "https://api.openrouteservice.org/optimization",
        {
          method: "POST",
          headers: {
            Authorization: ORS_API_KEY,
            "Content-Type": "application/json"
          },
          body: JSON.stringify(body)
        }
      );

      const data = await response.json();

      if (!response.ok) {
        console.error(data);
        alert("Optimization failed.");
        return;
      }

      drawRoutes(data);

    } catch (err) {
      console.error("Optimization error:", err);
    }
  };

  // ======================================
  // DRAW ROUTES
  // ======================================
  const drawRoutes = async (data) => {
    const map = mapInstanceRef.current;
    const colors = ["blue", "red", "green", "purple"];

    for (let i = 0; i < data.routes.length; i++) {
      const route = data.routes[i];
      const orderedCoordinates = [];

      route.steps.forEach((step) => {
        if (step.type === "start" && route.vehicle_start)
          orderedCoordinates.push(route.vehicle_start);

        if (step.type === "job") {
          const job = jobs.find((j) => j.id === step.id);
          if (job) orderedCoordinates.push(job.location);
        }

        if (step.type === "end" && route.vehicle_end)
          orderedCoordinates.push(route.vehicle_end);
      });

      if (orderedCoordinates.length < 2) continue;

      const directionResponse = await fetch(
        "https://api.openrouteservice.org/v2/directions/driving-car/geojson",
        {
          method: "POST",
          headers: {
            Authorization: ORS_API_KEY,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            coordinates: orderedCoordinates,
            radiuses: orderedCoordinates.map(() => 2000)
          })
        }
      );

      const geoData = await directionResponse.json();

      if (!directionResponse.ok || !geoData.features) continue;

      const routeLayer = L.geoJSON(geoData, {
        style: {
          color: colors[i % colors.length],
          weight: 5
        }
      }).addTo(map);

      routeLayersRef.current.push(routeLayer);
      map.fitBounds(routeLayer.getBounds());
    }
  };

  return (
    <div>
      <button onClick={optimizeRoutes} style={{ marginBottom: 10 }}>
        Optimize Routes
      </button>

      <div
        ref={mapRef}
        style={{ width: "100%", height: "500px" }}
      />
    </div>
  );
};

export default FleetHtmlMap;


