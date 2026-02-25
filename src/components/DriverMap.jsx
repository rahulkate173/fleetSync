import React, { useState } from "react";

// Simple Google Maps route link generator for drivers
const DriverMap = () => {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [waypointsText, setWaypointsText] = useState("");
  const [travelMode, setTravelMode] = useState("driving");

  const [mapUrl, setMapUrl] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    setMapUrl("");

    if (!origin.trim() || !destination.trim()) {
      return;
    }

    // Split waypoints by newline or comma
    const waypoints = waypointsText
      .split(/\n|,/)
      .map((w) => w.trim())
      .filter((w) => w.length > 0);

    // Build waypoints string with optimize:true for best ordering
    let waypointsParam = "";
    if (waypoints.length > 0) {
      const joined = ["optimize:true", ...waypoints].join("|");
      waypointsParam = `&waypoints=${encodeURIComponent(joined)}`;
    }

    const url = `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(
      origin
    )}&destination=${encodeURIComponent(
      destination
    )}&travelmode=${encodeURIComponent(travelMode)}${waypointsParam}`;

    setMapUrl(url);
  };

  return (
    <div className="driver-map">
      <h2>Optimized Route (Google Maps)</h2>

      <form className="driver-map__form" onSubmit={handleSubmit}>
        <div className="driver-map__row">
          <div className="driver-map__field">
            <label>Origin</label>
            <input
              type="text"
              placeholder="e.g. Mumbai, India"
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
            />
          </div>

          <div className="driver-map__field">
            <label>Destination</label>
            <input
              type="text"
              placeholder="e.g. Pune, India"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
            />
          </div>
        </div>

        <div className="driver-map__row">
          <div className="driver-map__field driver-map__field--full">
            <label>Waypoints (comma or newline separated)</label>
            <textarea
              rows={3}
              placeholder={"Stop 1\nStop 2\nStop 3"}
              value={waypointsText}
              onChange={(e) => setWaypointsText(e.target.value)}
            />
          </div>

          <div className="driver-map__field">
            <label>Travel Mode</label>
            <select
              value={travelMode}
              onChange={(e) => setTravelMode(e.target.value)}
            >
              <option value="driving">Driving</option>
              <option value="walking">Walking</option>
              <option value="bicycling">Bicycling</option>
              <option value="transit">Transit</option>
            </select>
          </div>
        </div>

        <button type="submit" className="driver-map__submit">
          Get Optimized Route Link
        </button>
      </form>

      {mapUrl && (
        <div className="driver-map__result">
          <a href={mapUrl} target="_blank" rel="noopener noreferrer">
            Open optimized route in Google Maps
          </a>
        </div>
      )}
    </div>
  );
};

export default DriverMap;

