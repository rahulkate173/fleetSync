import { useRef } from "react";
import { useFleetStats } from "../../context/FleetStatsContext";
import "./Analysis.scss";

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from "chart.js";
import jsPDF from "jspdf";

import Sidebar from "../../components/Sidebar";
import Chart from "../../components/chart";
import { useShipmentData } from "../../context/ShipmentDataContext";
import ReportPDF from "../../components/ReportPDF";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);


const Analysis = () => {
  const pdfRef = useRef();
  const shipmentData = useShipmentData();
  const { stats } = useFleetStats();
  const {
      routeEfficiency,
      totalFleet,
      totalDistance,
      totalCO2,
    } = useFleetStats();

  const generatePDF = () => {
    // const doc = new jsPDF();
    // doc.text("Green Logistics - Analysis Report", 20, 20);
    // doc.text("Route Efficiency: 87%", 20, 40);
    // doc.text("Total Fleet: 42 Vehicles", 20, 50);
    // doc.text("Total Distance Covered: 12,540 km", 20, 60);
    // doc.text("Total CO2 Emission: 2,540 kg", 20, 70);
    // doc.save("analysis-report.pdf");
  
  };

  return (
    <div className="analysis-page" ref={pdfRef}>
    <Sidebar/>

      <div className="analysis-content">
        <h2>Analytics Overview</h2>

        {/* Top Cards */}
        <div className="cards">
          <div className="card">
            <h4>Route Efficiency</h4>
            <p>{routeEfficiency}</p>
          </div>
          <div className="card">
            <h4>Total Fleet</h4>
            <p>{totalFleet} Vehicles</p>
          </div>
          <div className="card">
            <h4>Total Distance</h4>
            <p>{totalDistance} km</p>
          </div>
          <div className="card">
            <h4>Total CO₂</h4>
            <p>{totalCO2}</p>
          </div>
        </div>

        {/* Chart Section */}
        {/* <div className="chart-section">
          <h3>Shipment Trends (Day-wise)</h3>
          <Bar data={shipmentData} />
        </div> */}
        <Chart shipmentData={shipmentData}/>

        {/* PDF Button */}
        {/* <button className="pdf-btn" onClick={generatePDF}>
          Generate PDF Report
        </button> */}
          <ReportPDF/>
      </div>
    </div>
  );
};

export default Analysis;