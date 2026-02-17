import { useState } from "react";
import "./Track.scss";
import { api } from "../../api/config";

const STAGES = ["departed", "middle", "loc", "delivered"];

const Track = () => {
  const [referenceId, setReferenceId] = useState("");
  const [shipment, setShipment] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleTrack = async () => {
    if (!referenceId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(api.track(referenceId.trim()));
      const data = await res.json();
      if (data.error) {
        setError(data.error);
        setShipment(null);
      } else {
        setShipment(data);
        setError(null);
      }
    } catch (e) {
      setError("Unable to fetch. Is the server running?");
      setShipment(null);
    } finally {
      setLoading(false);
    }
  };

  const getStepIndex = () => {
    if (!shipment) return -1;
    const idx = shipment.status_code ?? STAGES.indexOf(shipment.current_stage ?? "");
    return Math.max(0, idx);
  };

  return (
    <div className="track-page">
      <div className="heading">Track Your Shipment</div>
      <p className="track-sub">Enter your reference ID to see delivery status</p>

      <div className="track-input">
        <input
          type="text"
          placeholder="Enter Reference ID (e.g. REF-123)"
          value={referenceId}
          onChange={(e) => setReferenceId(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleTrack()}
        />
        <button onClick={handleTrack} disabled={loading || !referenceId.trim()}>
          {loading ? "Fetching..." : "Track"}
        </button>
      </div>

      {error && <div className="track-error">{error}</div>}

      {shipment && !error && (
        <div className="shipment-card">
          <h3>Reference ID: {shipment.reference_id}</h3>
          <p className="current-stage">Current: <strong>{shipment.current_stage}</strong></p>

          <div className="timeline">
            {STAGES.map((step, index) => {
              const currentStep = getStepIndex();
              return (
                <div
                  key={step}
                  className={`timeline-step ${index <= currentStep ? "active" : ""}`}
                >
                  <div className="circle"></div>
                  <p>{step}</p>
                  {shipment.timestamps && shipment.timestamps[step] && (
                    <small className="timestamp">
                      {new Date(shipment.timestamps[step]).toLocaleString()}
                    </small>
                  )}
                </div>
              );
            })}
          </div>

          {shipment.gps && (
            <div className="shipment-info">
              <div>
                <strong>Last Location:</strong>
                <p>Lat: {shipment.gps.lat?.toFixed(4)}, Lon: {shipment.gps.lon?.toFixed(4)}</p>
              </div>
              {shipment.gps.speed_kmh != null && (
                <div>
                  <strong>Speed:</strong>
                  <p>{shipment.gps.speed_kmh} km/h</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Track;
