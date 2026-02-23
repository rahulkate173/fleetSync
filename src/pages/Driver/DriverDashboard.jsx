import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import "./DriverDashboard.scss";

const DriverDashboard = () => {
  const navigate = useNavigate();
  const [isActive, setIsActive] = useState(false);
  const [location, setLocation] = useState(null);
  const intervalRef = useRef(null);

  // Dummy stats (Replace with API data if needed)
  const stats = {
    load: "12 Tons",
    co2: "240 kg",
    avgSpeed: "65 km/h",
    distance: "320 km",
  };

  // Function to send location to backend
  const sendLocationToBackend = async (coords) => {
    try {
      await fetch("http://localhost:5000/api/location", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          latitude: coords.latitude,
          longitude: coords.longitude,
          timestamp: new Date(),
        }),
      });
    } catch (err) {
      console.error("Error sending location:", err);
    }
  };

  // Start GPS Tracking
  const startTracking = () => {
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const coords = position.coords;
        setLocation(coords);
        sendLocationToBackend(coords);

        intervalRef.current = setInterval(() => {
          navigator.geolocation.getCurrentPosition((pos) => {
            const newCoords = pos.coords;
            setLocation(newCoords);
            sendLocationToBackend(newCoords);
          });
        }, 30000); // Every 30 seconds
      },
      (error) => {
        console.error(error);
        alert("GPS permission denied.");
      }
    );
  };

  const stopTracking = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
  };

  const handleToggle = () => {
    if (!isActive) {
      startTracking();
    } else {
      stopTracking();
    }
    setIsActive(!isActive);
  };

  useEffect(() => {
    return () => stopTracking(); // Cleanup on unmount
  }, []);

  return (
    <div className="dashboard-container">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-top">
          <h2 className="logo">FleetSync</h2>
          <div className="profile-section">
            <div className="profile-circle">D</div>
            <button
              className="exit-btn"
              onClick={() => navigate("/")}
            >
              Exit
            </button>
          </div>
        </div>
      </div>

      {/* Main Dashboard */}
      <div className="main-content">
        <h1>Driver Dashboard</h1>

        <div className="cards">
          <div className="card">
            <h3>Load</h3>
            <p>{stats.load}</p>
          </div>

          <div className="card">
            <h3>CO₂ Emission</h3>
            <p>{stats.co2}</p>
          </div>

          <div className="card">
            <h3>Avg Speed</h3>
            <p>{stats.avgSpeed}</p>
          </div>

          <div className="card">
            <h3>Distance Covered</h3>
            <p>{stats.distance}</p>
          </div>

          <div className="card">
            <h3>Live Location</h3>
            {location ? (
              <p>
                Lat: {location.latitude.toFixed(4)} <br />
                Lng: {location.longitude.toFixed(4)}
              </p>
            ) : (
              <p>Not Active</p>
            )}
          </div>
        </div>

        <button
          className={`status-btn ${isActive ? "active" : ""}`}
          onClick={handleToggle}
        >
          {isActive ? "Deactivate" : "Activate"}
        </button>
      </div>
    </div>
  );
};

export default DriverDashboard;