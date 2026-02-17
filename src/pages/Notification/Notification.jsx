import { useState } from "react";
import "./Notification.scss";
import Sidebar from "../../components/Sidebar";

const dummyNotifications = [
  {
    customer_id: "CUST001",
    ticket_id: "TKT101",
    origin: "Pune",
    destination: "Mumbai",
    load: "Express - 500kg",
    driver_id: "DRV12",
  },
  {
    customer_id: "CUST002",
    ticket_id: "TKT102",
    origin: "Delhi",
    destination: "Jaipur",
    load: "Standard - 300kg",
    driver_id: "DRV07",
  },
  {
    customer_id: "CUST003",
    ticket_id: "TKT103",
    origin: "Bangalore",
    destination: "Hyderabad",
    load: "Heavy - 900kg",
    driver_id: "DRV21",
  },
];

const Notification = () => {
  const [notifications] = useState(dummyNotifications);

  return (
    <div className="notification-page">
      {/* Sidebar */}
     <Sidebar/>

      {/* Main Content */}
      <div className="notification-content">
        <h2>Shipment Notifications</h2>

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Customer ID</th>
                <th>Ticket ID</th>
                <th>Origin</th>
                <th>Destination</th>
                <th>Delivery Type</th>
                <th>Driver ID</th>
              </tr>
            </thead>

            <tbody>
              {notifications.map((item, index) => (
                <tr key={index}>
                  <td>{item.customer_id}</td>
                  <td>{item.ticket_id}</td>
                  <td>{item.origin}</td>
                  <td>{item.destination}</td>
                  <td>{item.load}</td>
                  <td>{item.driver_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Notification;
