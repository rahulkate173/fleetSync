import { useState } from "react";
import axios from "axios";
import UserSidebar from "./UserSidebar";
import "./OrderPage.scss";

const OrderPage = () => {
  const [payloadType, setPayloadType] = useState("");
  const [weight, setWeight] = useState("");
  const [destination, setDestination] = useState("");
  const [truckType, setTruckType] = useState("small");

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      await axios.post("/api/orders", {
        payloadType,
        weight,
        destination,
        truckType,
      });

      // You can replace this with navigation or any other success UI
      alert("Order placed successfully");
    } catch (error) {
      console.error("Failed to place order", error);
      alert("Failed to place order. Please try again.");
    }
  };

  return (
    <div className="order-layout">
      <UserSidebar />

      <div className="order-content">
        <div className="order-card">
          <form onSubmit={handleSubmit}>
            <h2>Payload Type</h2>
            <input
              placeholder="Enter payload type"
              value={payloadType}
              onChange={(e) => setPayloadType(e.target.value)}
            />

            <h2>Weight</h2>
            <input
              placeholder="Enter weight"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
            />

            <h2>Destination</h2>
            <input
              placeholder="Enter destination"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
            />

            <h2>Truck Type</h2>
            <div className="truck-type-options">
              <label>
                <input
                  type="radio"
                  name="truckType"
                  value="small"
                  checked={truckType === "small"}
                  onChange={(e) => setTruckType(e.target.value)}
                />
                Small
              </label>
              <label>
                <input
                  type="radio"
                  name="truckType"
                  value="medium"
                  checked={truckType === "medium"}
                  onChange={(e) => setTruckType(e.target.value)}
                />
                Medium
              </label>
              <label>
                <input
                  type="radio"
                  name="truckType"
                  value="heavy"
                  checked={truckType === "heavy"}
                  onChange={(e) => setTruckType(e.target.value)}
                />
                Heavy
              </label>
            </div>

            <button type="submit" className="order-btn">
              Proceed to Pay
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default OrderPage;