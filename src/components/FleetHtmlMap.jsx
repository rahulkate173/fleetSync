import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const FleetHtmlMap = () => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef({});
  const [liveVehicles, setLiveVehicles] = useState([]);

  const API_URL = "http://localhost:8000";

  // ================================
  // FETCH DRIVER DATA
  // ================================
  const fetchTruckData = async () => {
    try {
      const response = await fetch(`${API_URL}/dashboard/map/data`);
      const data = await response.json();
      console.log("LIVE DATA:", data);

      if (Array.isArray(data)) {
        setLiveVehicles(data);
        console.log("Live vehicles updated:", data);
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
      [18.5204, 73.8567], // Pune default
      12
    );

    L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      { maxZoom: 19 }
    ).addTo(map);

    mapInstanceRef.current = map;

    fetchTruckData();
    const interval = setInterval(fetchTruckData, 5000); // refresh every 5 sec

    return () => {
      clearInterval(interval);
      map.remove();
    };
  }, []);

  // ======================================
  // UPDATE MARKERS WHEN DATA CHANGES
  // ======================================
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const existingMarkers = markersRef.current;
    const currentIds = new Set();

    liveVehicles.forEach((vehicle) => {
      const lat=ve  hicle.gps.lat
        const lng=vehicle.gps.lon
        const driver_id=vehicle.vehicle_id
        console.log(lat,lng)
      

      if (!lat || !lng) return;

      currentIds.add(driver_id);

      if (existingMarkers[driver_id]) {
        // Update position
        existingMarkers[driver_id].setLatLng([lat, lng]);
      } else {
        // Create marker
        const marker = L.marker([lat, lng])
          .addTo(map)
          .bindPopup(`<b>Driver:</b> ${driver_id}`);

        existingMarkers[driver_id] = marker;
      }
    });

    // Remove markers that are no longer in response
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
          ? `Live: ${liveVehicles.length} driver(s)`
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
// import { useEffect, useRef, useState } from "react";
// import "leaflet/dist/leaflet.css";

// const FleetHtmlMap = () => {
//   const mapRef = useRef(null);
//   const mapInstanceRef = useRef(null);
//   const markersRef = useRef({});
//   const [liveVehicles, setLiveVehicles] = useState([]);

//   const API_URL =
//     import.meta.env.VITE_API_URL || "http://localhost:8000";

//   // ================================
//   // FETCH TRUCK DATA FROM REST API
//   // ================================
//   const fetchTruckData = async () => {
//     try {
//       const response = await fetch(`${API_URL}/dashboard/map/data`);
//       const data = await response.json();
//       console.log('data',data)
//       if (Array.isArray(data)) {
//         setLiveVehicles(data);
//       }
//     } catch (error) {
//       console.error("Error fetching truck data:", error);
//     }
//   };

//   // ======================================
//   // LOAD LEAFLET MAP (ONLY ONCE)
//   // ======================================
//   useEffect(() => {
//     const leafletScript = document.createElement("script");
//     leafletScript.src =
//       "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
//     leafletScript.async = true;
//     document.body.appendChild(leafletScript);

//     leafletScript.onload = () => {
//       if (!window.L || !mapRef.current) return;

//       const map = window.L.map(mapRef.current).setView(
//         [18.5204, 73.8567], // Default center (Pune)
//         12
//       );

//       window.L.tileLayer(
//         "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
//         { maxZoom: 19 }
//       ).addTo(map);

//       mapInstanceRef.current = map;

//       // Initial API call
//       fetchTruckData();

//       // Refresh every 30 seconds
//       const interval = setInterval(fetchTruckData, 30000);

//       return () => clearInterval(interval);
//     };

//     return () => {
//       if (mapInstanceRef.current) {
//         mapInstanceRef.current.remove();
//       }
//       try {
//         document.body.removeChild(leafletScript);
//       } catch {}
//     };
//   }, []);

//   // ======================================
//   // UPDATE MARKERS WHEN DATA CHANGES
//   // ======================================
//   useEffect(() => {
//     const map = mapInstanceRef.current;
//     if (!map) return;

//     const existingMarkers = markersRef.current;
//     const currentTruckIds = new Set();

//     liveVehicles.forEach((truck) => {
//       const { truck_id, latitude, longitude, status, timestamp } = truck;

//       if (!latitude || !longitude) return;

//       currentTruckIds.add(truck_id);

//       // If marker already exists → update position
//       if (existingMarkers[truck_id]) {
//         existingMarkers[truck_id].setLatLng([latitude, longitude]);
//         existingMarkers[truck_id].setPopupContent(`
//           <b>Truck:</b> ${truck_id}<br/>
//           <b>Status:</b> ${status}<br/>
//           <b>Updated:</b> ${new Date(timestamp).toLocaleTimeString()}
//         `);
//       } else {
//         // Create new marker
//         const marker = window.L.marker([latitude, longitude])
//           .addTo(map)
//           .bindPopup(`
//             <b>Truck:</b> ${truck_id}<br/>
//             <b>Status:</b> ${status}<br/>
//             <b>Updated:</b> ${new Date(timestamp).toLocaleTimeString()}
//           `);

//         existingMarkers[truck_id] = marker;
//       }
//     });

//     // Remove trucks not in latest response
//     Object.keys(existingMarkers).forEach((id) => {
//       if (!currentTruckIds.has(id)) {
//         map.removeLayer(existingMarkers[id]);
//         delete existingMarkers[id];
//       }
//     });
//   }, [liveVehicles]);

//   return (
//     <div
//       style={{
//         width: "100%",
//         borderRadius: "10px",
//         overflow: "hidden",
//       }}
//     >
//       <div
//         style={{
//           fontSize: 12,
//           marginBottom: 8,
//           color: "#666",
//         }}
//       >
//         {liveVehicles.length > 0
//           ? `Live: ${liveVehicles.length} truck(s)`
//           : "Waiting for truck data..."}
//       </div>

//       <div style={{ width: "100%", height: "400px" }}>
//         <div
//           ref={mapRef}
//           style={{ width: "100%", height: "100%" }}
//         />
//       </div>
//     </div>
//   );
// };

// export default FleetHtmlMap;


