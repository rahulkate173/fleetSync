import { useState } from "react";
import axios from "axios";
import "./Shipment.scss";
import Sidebar from "../../components/Sidebar";
import FleetHtmlMap from "../../components/FleetHtmlMap";

const Shipment = () => {
  const [searchId, setSearchId] = useState("");
  const [shipment, setShipment] = useState(null);

  const [showPopup, setShowPopup] = useState(false);
  const [message, setMessage] = useState("");

  const handleSearch = async () => {
    if (!searchId.trim()) return;

    try {
      const response = await axios.get(
        `https://server-production-cd13.up.railway.app/shipment/search/${searchId}`
      );

      if (response.data) {
        setShipment(response.data);
      } else {
        alert("Shipment not found");
        setShipment(null);
      }
    } catch (error) {
      alert("Error fetching shipment data");
      setShipment(null);
    }
  };

  const handleSend = async () => {
    if (!message.trim()) return alert("Message cannot be empty");

    try {
      await axios.post("https://server-production-cd13.up.railway.app/alerts/send", {
        driver_id: shipment.driver_id,   // IMPORTANT
        shipmentId: shipment._id,
        message: message,
      });

      alert("Alert sent successfully");
      setShowPopup(false);
      setMessage("");
    } catch (error) {
      alert("Error sending alert");
    }
  };

  return (
    <div className="shipment-page">
      <Sidebar />

      <div className="main-content">
        <div className="map-section">
          <h3>Live Shipment Map</h3>
          <FleetHtmlMap />
        </div>

        <div className="details-panel">
          <div className="search-box">
            <input
              type="text"
              placeholder="Enter Shipment ID"
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

              <div className="action-buttons">
                <button onClick={() => setShowPopup(true)}>
                  Send Alert
                </button>
              </div>
            </div>
          )}
        </div>

        {showPopup && (
          <div className="side-popup">
            <div className="popup-content">
              <h4>Send Alert to Driver</h4>

              <textarea
                placeholder="Enter your message..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
              />

              <div className="popup-buttons">
                <button onClick={handleSend}>Send</button>
                <button onClick={() => setShowPopup(false)}>Cancel</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Shipment;