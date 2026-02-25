import UserSidebar from "./UserSidebar";
import "./OrderPage.scss";

const OrderPage = () => {
  return (
    <div className="order-layout">
      <UserSidebar />

      <div className="order-content">
        <div className="order-card">
          <h2>Payload Type</h2>
          <input placeholder="Enter payload type" />

          <h2>Weight</h2>
          <input placeholder="Enter weight" />

          <h2>Destination</h2>
          <input placeholder="Enter destination" />

          <h2>Truck Type</h2>
          <input placeholder="Enter truck type" />

          <button className="order-btn">
            Proceed to Pay
          </button>
        </div>
      </div>
    </div>
  );
};

export default OrderPage;