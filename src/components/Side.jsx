import React from "react";

const Side = () => {
  return (
    <div className="sidebar">
      <div className="profile">
        <h4>Welcome back, Alex!</h4>
      </div>

      <ul className="menu">
        <li className="active">Dashboard</li>
        <li>Shipment</li>
        <li>Customer</li>
        <li>Analysis</li>
        <li>History</li>
        <li>Notification</li>
      </ul>

      <div className="recent-trips">
        <h4>Recent Trips</h4>
        <p>1246 KM</p>
      </div>
    </div>
  );
};

export default Side;
