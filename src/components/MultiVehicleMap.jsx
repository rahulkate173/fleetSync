import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
} from "react-leaflet";
import L from "leaflet";

// Custom icons
const startIcon = new L.Icon({
  iconUrl: "https://cdn-icons-png.flaticon.com/512/190/190411.png",
  iconSize: [25, 25],
});

const endIcon = new L.Icon({
  iconUrl: "https://cdn-icons-png.flaticon.com/512/684/684908.png",
  iconSize: [25, 25],
});

const vehicleIcon = new L.Icon({
  iconUrl: "https://cdn-icons-png.flaticon.com/512/1995/1995470.png", 
  iconSize: [35, 35],
  iconAnchor: [17, 17],   // center alignment
  popupAnchor: [0, -15],
});


const MultiVehicleMap = () => {
  const [vehicles, setVehicles] = useState([
    {
      id: "TRK101",
      start: [18.5204, 73.8567],
      end: [18.5900, 73.7800],
      current: [18.5204, 73.8567],
      path: [[18.5204, 73.8567]],
      load: "500kg",
    },
    {
      id: "TRK102",
      start: [18.5100, 73.8600],
      end: [18.5800, 73.8200],
      current: [18.5100, 73.8600],
      path: [[18.5100, 73.8600]],
      load: "300kg",
    },
  ]);

  // Simulate movement toward destination
  useEffect(() => {
    const interval = setInterval(() => {
      setVehicles((prevVehicles) =>
        prevVehicles.map((vehicle) => {
          const latStep =
            (vehicle.end[0] - vehicle.current[0]) * 0.05;
          const lngStep =
            (vehicle.end[1] - vehicle.current[1]) * 0.05;

          const newPosition = [
            vehicle.current[0] + latStep,
            vehicle.current[1] + lngStep,
          ];

          return {
            ...vehicle,
            current: newPosition,
            path: [...vehicle.path, newPosition],
          };
        })
      );
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  return (
    <MapContainer
      center={[18.5204, 73.8567]}
      zoom={12}
      style={{ height: "450px", width: "100%" }}
    >
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {vehicles.map((vehicle) => (
        <div key={vehicle.id}>
          {/* Start Marker */}
          <Marker position={vehicle.start} icon={startIcon}>
            <Popup>Start - {vehicle.id}</Popup>
          </Marker>

          {/* End Marker */}
          <Marker position={vehicle.end} icon={endIcon}>
            <Popup>Destination - {vehicle.id}</Popup>
          </Marker>

          {/* Vehicle Marker */}
          <Marker position={vehicle.current} icon={vehicleIcon}>
            <Popup>
              <strong>{vehicle.id}</strong><br />
              Load: {vehicle.load}
            </Popup>
          </Marker>

          {/* Path Covered */}
          <Polyline
            positions={vehicle.path}
            pathOptions={{ color: "green", weight: 4 }}
          />
        </div>
      ))}
    </MapContainer>
  );
};

export default MultiVehicleMap;
