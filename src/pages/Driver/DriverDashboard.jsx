import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import DriverMap from "../../components/DriverMap";
import axios from "axios";
import "./DriverDashboard.scss";

const DRIVER_ID = "40"; // Replace with logged-in driver ID

const DriverDashboard = () => {
  const navigate = useNavigate();
  const [isActive, setIsActive] = useState(false);
  const [location, setLocation] = useState(null);
  const [stats, setStats] = useState({
    load: "—",
    co2: "—",
    avgSpeed: "—",
    distance: "—",
  });
  const [notifications, setNotifications] = useState([]);
  const intervalRef = useRef(null);
  const socketRef = useRef(null);

  // ==============================
  // 🔥 WEBSOCKET CONNECTION
  // ==============================

  const connectWebSocket = () => {
    const ws = new WebSocket(
      `ws://https://server-production-cd13.up.railway.app/ws/notifications/${DRIVER_ID}`
    );

    ws.onopen = () => {
      console.log("Connected to notification server");
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      const newNotification = {
        id: Date.now(),
        message: data.message,
        time: new Date().toLocaleTimeString(),
      };

      setNotifications((prev) => [newNotification, ...prev]);
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected. Reconnecting...");
      setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      ws.close();
    };

    socketRef.current = ws;
  };

  useEffect(() => {
    connectWebSocket();

    return () => {
      if (socketRef.current) socketRef.current.close();
    };
  }, []);

  // ==============================
  // 📍 GPS TRACKING
  // ==============================

  const sendLocationToBackend = async (coords) => {
  try {
    const response = await axios.post(
      "https://server-production-cd13.up.railway.app/truck/gps",
      {
        vehicle_id: DRIVER_ID,
        lat: coords.latitude,
        lon: coords.longitude,
        speed_kmh: 50,
        temperature: 0,
        reference_id: "45",
      },
      {
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    console.log("Location sent successfully:", response.data);
  } catch (err) {
    console.error("Error sending location:", err.response?.data || err.message);
  }
};

  const startTracking = () => {
    if (!navigator.geolocation) {
      alert("Geolocation not supported.");
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
        }, 30000);
      },
      () => {
        alert("GPS permission denied.");
      }
    );
  };

  const stopTracking = () => {
    if (intervalRef.current) clearInterval(intervalRef.current);
  };

  const handleToggle = () => {
    if (!isActive) startTracking();
    else stopTracking();

    setIsActive(!isActive);
  };

  useEffect(() => {
    return () => stopTracking();
  }, []);

  useEffect(() => {
    let cancelled = false;

    const fetchStats = async () => {
      try {
        const res = await fetch("https://server-production-cd13.up.railway.app/analysis/fleet-stats");
        if (!res.ok) return;
        const data = await res.json();
        if (cancelled) return;

        setStats((prev) => ({
          ...prev,
          co2: data.totalCO2 ?? prev.co2,
          avgSpeed:
            data.avgSpeed !== undefined && data.avgSpeed !== null
              ? `${data.avgSpeed} km/h`
              : prev.avgSpeed,
          distance: data.totalDistance ?? prev.distance,
        }));
      } catch {
        // ignore transient network errors
      }
    };

    fetchStats();
    const id = setInterval(fetchStats, 30000);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  // ==============================
  // UI
  // ==============================

  return (
    <div className="dashboard-container">
      <div className="sidebar">
        <div className="sidebar-top">
          <h2 className="logo">FleetSync</h2>
          <div className="profile-section">
            <div className="profile-circle">D</div>
            <button className="exit-btn" onClick={() => navigate("/")}>
              Exit
            </button>
          </div>
        </div>
      </div>

      <div className="main-content">
        <h1>Driver Dashboard</h1>

        <div className="cards driver-stats">
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
        </div>

        <button
          className={`status-btn ${isActive ? "active" : ""}`}
          onClick={handleToggle}
        >
          {isActive ? "Deactivate" : "Activate"}
        </button>

        {/* 🔔 Notifications */}
        <div className="notification-section">
          <h2>Notifications</h2>

          {notifications.length === 0 ? (
            <p className="no-notifications">No notifications yet</p>
          ) : (
            notifications.map((note) => (
              <div key={note.id} className="notification-item">
                <p>{note.message}</p>
                <span>{note.time}</span>
              </div>
            ))
          )}
        </div>

        <div className="driver-map-section">
          <DriverMap />
        </div>
      </div>
    </div>
  );
};

export default DriverDashboard;