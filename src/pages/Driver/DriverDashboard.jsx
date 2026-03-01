import React, { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import DriverMap from "../../components/DriverMap";
import axios from "axios";
import "./DriverDashboard.scss";

const DriverDashboard = () => {
  const navigate = useNavigate();
  const [driverId, setDriverId] = useState(null);

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
  const reconnectTimeoutRef = useRef(null);

  // ==============================
  // 🔐 LOAD DRIVER ID FROM LOCALSTORAGE
  // ==============================

  useEffect(() => {
    const storedDriverId = localStorage.getItem("driverId");
    if (!storedDriverId) {
      navigate("/driver/login");
    } else {
      setDriverId(storedDriverId);
    }
  }, [navigate]);

  // ==============================
  // 🔥 WEBSOCKET
  // ==============================

  const connectWebSocket = useCallback(() => {
    // Don't connect if driverId is not set
    if (!driverId) {
      console.log("Waiting for driver ID...");
      return;
    }

    // Close existing connection if any
    if (socketRef.current) {
      socketRef.current.close();
    }

    const ws = new WebSocket(
      `wss://server-production-cd13.up.railway.app/ws/notifications/${driverId}`
    );

    ws.onopen = () => {
      console.log(`WebSocket connected for driver ${driverId}`);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        const newNotification = {
          id: Date.now(),
          message: data.message || "New notification",
          time: new Date().toLocaleTimeString(),
        };

        setNotifications((prev) => [newNotification, ...prev]);
      } catch (err) {
        console.error("Invalid WebSocket message:", err);
      }
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected. Reconnecting...");
      reconnectTimeoutRef.current = setTimeout(() => {
        connectWebSocket();
      }, 3000);
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      ws.close();
    };

    socketRef.current = ws;
  }, [driverId]);

  useEffect(() => {
    if (!driverId) return; // Wait until driverId is loaded

    connectWebSocket();

    return () => {
      if (socketRef.current) socketRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };
  }, [connectWebSocket, driverId]);

  // ==============================
  // 📍 GPS TRACKING
  // ==============================

  const sendLocationToBackend = async (coords) => {
    if (!driverId) return;

    try {
      await axios.post(
        "https://server-production-cd13.up.railway.app/truck/gps",
        {
          vehicle_id: driverId,
          lat: coords.latitude,
          lon: coords.longitude,
          speed_kmh: 50,
          temperature: 0,
          reference_id: "45",
        },
        {
          headers: { "Content-Type": "application/json" },
        }
      );

      console.log("Location sent successfully");
    } catch (err) {
      console.error("Location error:", err.response?.data || err.message);
    }
  };

  const startTracking = () => {
    if (!navigator.geolocation) {
      alert("Geolocation not supported");
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
      () => alert("GPS permission denied")
    );
  };

  const stopTracking = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  const handleToggle = () => {
    if (isActive) stopTracking();
    else startTracking();

    setIsActive((prev) => !prev);
  };

  useEffect(() => {
    return () => stopTracking();
  }, []);

  // ==============================
  // 📊 FETCH STATS
  // ==============================

  useEffect(() => {
    let cancelled = false;

    const fetchStats = async () => {
      try {
        const res = await fetch(
          "https://server-production-cd13.up.railway.app/analysis/fleet-stats"
        );
        if (!res.ok) return;

        const data = await res.json();
        if (cancelled) return;

        setStats((prev) => ({
          ...prev,
          co2: data.totalCO2 ?? prev.co2,
          avgSpeed:
            data.avgSpeed != null
              ? `${data.avgSpeed} km/h`
              : prev.avgSpeed,
          distance: data.totalDistance ?? prev.distance,
        }));
      } catch {
        // ignore temporary network errors
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
  // ⏳ LOADING STATE
  // ==============================

  if (!driverId) {
    return (
      <div className="dashboard-container">
        <div className="loading-state">
          <h2>Loading...</h2>
          <p>Redirecting to login...</p>
        </div>
      </div>
    );
  }

  // ==============================
  // 🎨 UI
  // ==============================

  return (
    <div className="dashboard-container">
      <div className="sidebar">
        <div className="sidebar-top">
          <h2 className="logo">FleetSync</h2>
          <div className="profile-section">
            <div className="profile-circle">D</div>
            <button className="exit-btn" onClick={() => {
              localStorage.removeItem("driverId");
              localStorage.removeItem("driverToken");
              localStorage.removeItem("driverName");
              navigate("/");
            }}>
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
          <DriverMap location={location} />
        </div>
      </div>
    </div>
  );
};

export default DriverDashboard;