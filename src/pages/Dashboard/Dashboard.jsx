
import "./Dashboard.scss";
import axios from "axios";
import FleetHtmlMap from "../../components/FleetHtmlMap";


import React, { useState, useEffect } from "react";
import Side from "../../components/Side";
import Header from "../../components/Header";
import Sidebar from "../../components/Sidebar";
import AiModal from "../../components/AiModal";
import Analysis from "../Analysis/Analysis";
import Chart from "../../components/chart";
import { useShipmentData } from "../../context/ShipmentDataContext";
import Card from "../../components/Card";


const Dashboard = () => {
  const shipmentData = useShipmentData();
  const [active, setActive] = useState(0);
  const [total, setTotal] = useState(0);


  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get("http://localhost:8000/dashboard/summary");
        const data = res.data;
        //  console.log(data)
        
        setActive(data.fleet_status.delayed || 0);
        setTotal(data.fleet_status.total || 0);
      } catch (err) {
        console.error("Error fetching dashboard summary:", err);
      }
    };

    fetchData();
  }, []);

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
                <span className="active">{total-active}</span>
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

              <Chart shipmentData={shipmentData} />
            </div>

            <div className="card efficiency">

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
