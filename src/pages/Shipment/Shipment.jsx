import { useState } from "react";
import "./Shipment.scss";
import Sidebar from "../../components/Sidebar";
import FleetHtmlMap from "../../components/FleetHtmlMap";

const dummyData = {
  SHP001: {
    location: "Pune, Maharashtra",
    load: "450 kg",
    co2: "120 kg CO₂",
    eta: "14 Feb 2026 - 5:30 PM",
  },
  SHP002: {
    location: "Mumbai, Maharashtra",
    load: "800 kg",
    co2: "220 kg CO₂",
    eta: "15 Feb 2026 - 2:00 PM",
  },
};

const Shipment = () => {
  const [searchId, setSearchId] = useState("");
  const [shipment, setShipment] = useState(null);

  const handleSearch = () => {
    const result = dummyData[searchId];
    if (result) {
      setShipment(result);
    } else {
      alert("Shipment not found");
      setShipment(null);
    }
  };

  return (
    <div className="shipment-page">
      {/* Sidebar */}
    <Sidebar/>

      {/* Main Content */}
      <div className="main-content">
        {/* Map Section */}
        <div className="map-section">
          <h3>Live Shipment Map</h3>
          <FleetHtmlMap />
        </div>

        {/* Right Panel */}
        <div className="details-panel">
          <div className="search-box">
            <input
              type="text"
              placeholder="Enter Shipment ID (SHP001)"
              value={searchId}
              onChange={(e) => setSearchId(e.target.value)}
            />
            <button onClick={handleSearch}>Search</button>
          </div>

          {shipment && (
            <div className="shipment-details">
              <h4>Shipment Details</h4>

              <p><strong>Location:</strong> {shipment.location}</p>
              <p><strong>Load:</strong> {shipment.load}</p>
              <p><strong>CO₂ Emission:</strong> {shipment.co2}</p>
              <p><strong>ETA:</strong> {shipment.eta}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Shipment;
