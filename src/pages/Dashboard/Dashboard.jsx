// import { useEffect } from "react";
// import { gsap } from "gsap";
import "./Dashboard.scss";
// import { useState } from "react";



// import Sidebar from "../../components/Sidebar";
// import AiModal from "../../components/AiModal";
import FleetHtmlMap from "../../components/FleetHtmlMap";

// const Dashboard = () => {
//   const [showAI, setShowAI] = useState(false);

//   useEffect(() => {
//     gsap.from(".map-card", {
//       y: 50,
//       opacity: 0,
//       duration: 1,
//     });

//     gsap.from(".co2-card", {
//       x: 50,
//       opacity: 0,
//       duration: 1,
//       delay: 0.3,
//     });
//   }, []);

//   return (
//     <div className="admin-dashboard">
//       {/* Sidebar */}
//       <Sidebar />

//       {/* Main Content */}
//       <div className="main-content">
//         <h2>Dashboard</h2>

//         <div className="top-section">
//           {/* Map Section */}
//           <div className="map-card">
//             <h3>Live Vehicle Tracking</h3>
//             <MultiVehicleMap />
//           </div>

//           {/* CO2 Card */}
//           <div className="co2-card">
//             <h3>Total CO₂ Used</h3>
//             <p className="co2-value">2,540 kg</p>
//             <span className="eco-indicator">↓ 12% less than last week 🌱</span>
//           </div>
//         </div>

//         {/* AI Floating Button */}
//         <button className="ai-button">AI</button>
//         <button className="ai-button" onClick={() => setShowAI(true)}>
//           AI
//         </button>

//         {showAI && <AiModal onClose={() => setShowAI(false)} />}

//       </div>
//     </div>
//   );
// };

// export default Dashboard;

import React, { useState } from "react";
import Side from "../../components/Side";
import Header from "../../components/Header";
import Sidebar from "../../components/Sidebar";
import AiModal from "../../components/AiModal";
import Analysis from "../Analysis/Analysis";
import Chart from "../../components/chart";
import { useShipmentData } from "../../context/ShipmentDataContext";
import Card from "../../components/Card";

// import Sidebar from "./Sidebar";
// import Header from "./Header";


const Dashboard = () => {
  const shipmentData = useShipmentData();
   const [active, setActive] = useState(40);
  const [total, setTotal] = useState(90);

  return (
    <div className="dashboard">
      {/* <Side /> */}
      <Sidebar />

      <div className="main">
        {/* <Header /> */}

        <div className="content">
          <div className="top-section">
           
            <div className="map-card">
              <h3>Live Vehicle Tracking</h3>
              <FleetHtmlMap />
            </div>
          </div>

          <div className="middle-section">
            <div className="card shipment-details">
              
                <h2>Fleet Status</h2>
                <div className="fleet-count">
                  <span className="active">{active}</span>
                  <span className="divider">/</span>
                  <span className="total">{total}</span>
            
                <p>Fleets Active</p>
              </div>
            </div>

            <div className="card truck-capacity">
              <h3>Current Truck Capacity</h3>
              <div className="truck-box">
                <div className="capacity-bar">
                  <div className="fill"></div>
                </div>
                <p>86%</p>
              </div>
            </div>
          </div>

          <div className="bottom-section">
            <div className="card trends">
              {/* <h3>Shipment Trends</h3>
              <div className="graph-placeholder">Graph</div> */}
              {/* <Analysis/> */}
              <Chart shipmentData={shipmentData} />
            </div>

            <div className="card efficiency">
              {/* <h3>Route Efficiency</h3>
              <h1>96%</h1> */}
              <Card />
            </div>

            <div className="card chat">
              {/* <h3>Chat</h3> */}
              <AiModal />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
