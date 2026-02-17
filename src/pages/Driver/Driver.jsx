import { useState, useEffect, useRef } from "react";
import "./Driver.scss";
import { api } from "../../api/config";

const MAX_SPEED_KMH = 80;
const ALERT_SOUND_URL = "https://assets.mixkit.co/active_storage/sfx/2869-2869-preview.mp3"; // beep for alerts

const Driver = () => {
  const [vehicleId, setVehicleId] = useState("TRUCK-001");
  const [truckId, setTruckId] = useState(1); // for alerts API
  const [referenceId, setReferenceId] = useState("");
  const [locationGranted, setLocationGranted] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | active | error
  const [alerts, setAlerts] = useState([]);
  const audioRef = useRef(null);
  const intervalRef = useRef(null);

  const playAlertSound = () => {
    try {
      if (audioRef.current) {
        audioRef.current.currentTime = 0;
        audioRef.current.play().catch(() => {});
      }
    } catch {}
  };

  useEffect(() => {
    if (!navigator.geolocation) {
      setStatus("error");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      () => setLocationGranted(true),
      () => setLocationGranted(false),
      { enableHighAccuracy: true }
    );
  }, []);

  const prevAlertsCountRef = useRef(0);
  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const res = await fetch(api.alerts(truckId));
        const data = await res.json();
        if (Array.isArray(data)) {
          if (data.length > prevAlertsCountRef.current) {
            playAlertSound();
          }
          prevAlertsCountRef.current = data.length;
          setAlerts(data);
        }
      } catch {}
    };
    fetchAlerts();
    const t = setInterval(fetchAlerts, 5000);
    return () => clearInterval(t);
  }, [vehicleId, truckId]);

  const sendGps = async (position) => {
    const lat = position.coords.latitude;
    const lon = position.coords.longitude;
    const speed = (position.coords.speed ?? 0) * 3.6 || 0; // m/s -> km/h

    if (speed > MAX_SPEED_KMH) {
      playAlertSound();
    }

    try {
      const res = await fetch(api.truckGps, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vehicle_id: vehicleId,
          lat,
          lon,
          speed_kmh: Math.round(speed * 10) / 10,
          reference_id: referenceId || undefined,
        }),
      });
      const data = await res.json();
      return data;
    } catch (e) {
      throw e;
    }
  };

  const startSending = () => {
    if (!locationGranted) {
      alert("Please allow location access first.");
      return;
    }
    setIsSending(true);
    setStatus("active");

    const doSend = () => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          sendGps(pos)
            .then(() => setStatus("active"))
            .catch(() => setStatus("error"));
        },
        () => setStatus("error"),
        { enableHighAccuracy: true, maximumAge: 5000 }
      );
    };

    doSend();
    intervalRef.current = setInterval(doSend, 5000);
  };

  const stopSending = () => {
    setIsSending(false);
    setStatus("idle");
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  return (
    <div className="driver-page">
      <audio ref={audioRef} src={ALERT_SOUND_URL} preload="auto" />

      <div className="driver-header">
        <h1>Truck Driver</h1>
        <p>Share your live location. You will receive alerts for overspeed and route deviation.</p>
      </div>

      <div className="driver-form">
        <div className="field">
          <label>Vehicle ID</label>
          <input
            type="text"
            value={vehicleId}
            onChange={(e) => setVehicleId(e.target.value)}
            placeholder="TRUCK-001"
            disabled={isSending}
          />
        </div>
        <div className="field">
          <label>Truck ID (for alerts)</label>
          <input
            type="number"
            min="1"
            value={truckId}
            onChange={(e) => setTruckId(parseInt(e.target.value, 10) || 1)}
            disabled={isSending}
          />
        </div>
        <div className="field">
          <label>Reference ID (optional)</label>
          <input
            type="text"
            value={referenceId}
            onChange={(e) => setReferenceId(e.target.value)}
            placeholder="REF-123"
            disabled={isSending}
          />
        </div>

        <div className="location-status">
          {locationGranted ? (
            <span className="ok">Location access granted</span>
          ) : (
            <span className="warn">Allow location access to start</span>
          )}
        </div>

        <div className="driver-actions">
          {!isSending ? (
            <button className="btn-start" onClick={startSending} disabled={!locationGranted}>
              Start Sharing Location
            </button>
          ) : (
            <button className="btn-stop" onClick={stopSending}>
              Stop Sharing
            </button>
          )}
        </div>

        <div className={`status-indicator ${status}`}>
          {status === "active" && "Sending GPS every 5s"}
          {status === "error" && "Failed to send. Check server."}
          {status === "idle" && "Idle"}
        </div>
      </div>

      <div className="alerts-section">
        <h3>Alerts from Admin</h3>
        <p className="hint">Sound plays for overspeed and route deviation alerts</p>
        <ul className="alerts-list">
          {alerts.length === 0 && <li className="empty">No alerts yet</li>}
          {alerts.map((a, i) => (
            <li key={i} className={`alert-item ${a.severity}`}>
              <strong>{a.type}</strong>: {a.message}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default Driver;
