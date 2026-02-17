// import React, { useRef } from "react";
// import { jsPDF } from "jspdf";
// import html2canvas from "html2canvas";
// import {
//   PieChart,
//   Pie,
//   Cell,
//   BarChart,
//   Bar,
//   XAxis,
//   YAxis,
//   Tooltip,
//   ResponsiveContainer,
// } from "recharts";

// const COLORS = ["#2E7D32", "#66BB6A", "#A5D6A7"];

// const pieData = [
//   { name: "Fuel Efficient", value: 60 },
//   { name: "Moderate", value: 25 },
//   { name: "High Emission", value: 15 },
// ];

// const barData = [
//   { name: "Jan", emission: 400 },
//   { name: "Feb", emission: 300 },
//   { name: "Mar", emission: 500 },
//   { name: "Apr", emission: 200 },
// ];

// export default function ReportPDF() {
//   const reportRef = useRef();

//   const generatePDF = async () => {
//     const input = reportRef.current;
//     const canvas = await html2canvas(input, { scale: 2 });
//     const imgData = canvas.toDataURL("image/png");

//     const pdf = new jsPDF("p", "mm", "a4");
//     const pdfWidth = pdf.internal.pageSize.getWidth();
//     const pdfHeight = (canvas.height * pdfWidth) / canvas.width;

//     pdf.addImage(imgData, "PNG", 0, 0, pdfWidth, pdfHeight);
//     pdf.save("fleetSync.pdf");
//   };

//   return (
//     <>
//       <button onClick={generatePDF} style={{ margin: "20px" }}>
//         Download Report
//       </button>

//       <div
//         ref={reportRef}
//         style={{
//           padding: "40px",
//           backgroundColor: "#f5f7fa",
//           fontFamily: "Arial",
//           width: "800px",
//         }}
//       >
//         {/* Header */}
//         <div style={{ display: "flex", justifyContent: "space-between" }}>
//           <div>
//             <h1 style={{ color: "#2E7D32" }}>
//               Green Logistics Analysis Report
//             </h1>
//             <p>Date: {new Date().toLocaleDateString()}</p>
//           </div>

//           {/* Logo */}
//           <img
//             src="/logo.png"
//             alt="logo"
//             style={{ width: "100px", height: "auto" }}
//           />
//         </div>

//         <hr />

//         {/* Summary Section */}
//         <div style={{ marginTop: "20px" }}>
//           <h2>Key Metrics</h2>
//           <p>Route Efficiency: <b>87%</b></p>
//           <p>Total Fleet: <b>42 Vehicles</b></p>
//           <p>Total Distance Covered: <b>12,540 km</b></p>
//           <p>Total CO₂ Emission: <b>2,540 kg</b></p>
//         </div>

//         {/* Charts Section */}
//         <div
//           style={{
//             display: "flex",
//             justifyContent: "space-between",
//             marginTop: "40px",
//           }}
//         >
//           {/* Pie Chart */}
//           <div>
//             <h3>Fleet Distribution</h3>
//             <PieChart width={300} height={300}>
//               <Pie
//                 data={pieData}
//                 cx="50%"
//                 cy="50%"
//                 outerRadius={100}
//                 dataKey="value"
//                 label
//               >
//                 {pieData.map((entry, index) => (
//                   <Cell key={`cell-${index}`} fill={COLORS[index]} />
//                 ))}
//               </Pie>
//               <Tooltip />
//             </PieChart>
//           </div>

//           {/* Bar Chart */}
//           <div>
//             <h3>Monthly CO₂ Emission</h3>
//             <BarChart width={300} height={300} data={barData}>
//               <XAxis dataKey="name" />
//               <YAxis />
//               <Tooltip />
//               <Bar dataKey="emission" fill="#2E7D32" />
//             </BarChart>
//           </div>
//         </div>
//       </div>
//     </>
//   );
// }
// import { jsPDF } from "jspdf";
// import { Chart, ArcElement, BarElement, CategoryScale, LinearScale } from "chart.js";

// Chart.register(ArcElement, BarElement, CategoryScale, LinearScale);

// const generatePDF = async () => {
//   const pdf = new jsPDF("p", "mm", "a4");

//   // ---------- HEADER ----------
//   pdf.setFontSize(20);
//   pdf.setTextColor(46, 125, 50);
//   pdf.text("Green Logistics Analysis Report", 20, 20);

//   pdf.setFontSize(10);
//   pdf.setTextColor(100);
//   pdf.text(`Date: ${new Date().toLocaleDateString()}`, 20, 28);

//   // Logo
//   const logo = new Image();
//   logo.src = "/logo.png";
//   await new Promise((resolve) => {
//     logo.onload = resolve;
//   });
//   pdf.addImage(logo, "PNG", 150, 10, 40, 20);

//   // ---------- METRICS BOX ----------
//   pdf.setDrawColor(200);
//   pdf.rect(20, 40, 170, 40);

//   pdf.setFontSize(12);
//   pdf.setTextColor(0);

//   pdf.text("Route Efficiency: 87%", 30, 55);
//   pdf.text("Total Fleet: 42 Vehicles", 30, 65);
//   pdf.text("Distance Covered: 12,540 km", 110, 55);
//   pdf.text("CO₂ Emission: 2,540 kg", 110, 65);

//   // ---------- PIE CHART ----------
//   const pieCanvas = document.createElement("canvas");
//   pieCanvas.width = 300;
//   pieCanvas.height = 300;

//   new Chart(pieCanvas, {
//     type: "pie",
//     data: {
//       labels: ["Fuel Efficient", "Moderate", "High Emission"],
//       datasets: [
//         {
//           data: [60, 25, 15],
//           backgroundColor: ["#2E7D32", "#66BB6A", "#A5D6A7"],
//         },
//       ],
//     },
//   });

//   const pieImage = pieCanvas.toDataURL("image/png");
//   pdf.text("Fleet Distribution", 20, 95);
//   pdf.addImage(pieImage, "PNG", 20, 100, 80, 80);

//   // ---------- BAR CHART ----------
//   const barCanvas = document.createElement("canvas");
//   barCanvas.width = 400;
//   barCanvas.height = 300;

//   new Chart(barCanvas, {
//     type: "bar",
//     data: {
//       labels: ["Jan", "Feb", "Mar", "Apr"],
//       datasets: [
//         {
//           label: "CO₂ Emission",
//           data: [400, 300, 500, 200],
//           backgroundColor: "#2E7D32",
//         },
//       ],
//     },
//     options: {
//       responsive: false,
//     },
//   });

//   const barImage = barCanvas.toDataURL("image/png");
//   pdf.text("Monthly CO₂ Emission", 110, 95);
//   pdf.addImage(barImage, "PNG", 110, 100, 80, 80);

//   // ---------- FOOTER ----------
//   pdf.setFontSize(9);
//   pdf.setTextColor(120);
//   pdf.text("Generated by FleetSync System", 20, 285);

//   pdf.save("fleetSync.pdf");
// };

// export default function ReportPDF() {
//   return (
//     <button onClick={generatePDF} style={{ padding: "10px 20px" }}>
//       Download Report
//     </button>
//   );
// }

import React from "react";
import { jsPDF } from "jspdf";
import {
  Chart,
  ArcElement,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from "chart.js";

Chart.register(ArcElement, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

export default function ReportPDF() {
  const generatePDF = async () => {
    try {
      const pdf = new jsPDF("p", "mm", "a4");

      const pageWidth = pdf.internal.pageSize.getWidth();

      // ================= HEADER =================
      pdf.setFont("helvetica", "bold");
      pdf.setFontSize(18);
      pdf.setTextColor(46, 125, 50);
      pdf.text("fleetSync Analysis Report", 20, 20);

      pdf.setFontSize(10);
      pdf.setTextColor(100);
      pdf.text(`Date: ${new Date().toLocaleDateString()}`, 20, 28);

      // Right side brand name
      pdf.setFontSize(24);
      pdf.setTextColor(46, 125, 50);
      pdf.text("fleetSync", pageWidth - 20, 20, { align: "right" });

      // ================= METRICS BOX =================
      pdf.setDrawColor(200);
      pdf.rect(20, 40, 170, 35);

      pdf.setFontSize(12);
      pdf.setTextColor(0);

      pdf.text("Route Efficiency: 87%", 30, 55);
      pdf.text("Total Fleet: 42 Vehicles", 30, 65);
      pdf.text("Distance Covered: 12,540 km", 110, 55);
      pdf.text("CO₂ Emission: 2,540 kg", 110, 65);

      // ================= PIE CHART =================
      const pieCanvas = document.createElement("canvas");
      pieCanvas.width = 500;
      pieCanvas.height = 500;

      const pieChart = new Chart(pieCanvas.getContext("2d"), {
        type: "pie",
        data: {
          labels: ["Fuel Efficient", "Moderate", "High Emission"],
          datasets: [
            {
              data: [60, 25, 15],
              backgroundColor: ["#2E7D32", "#66BB6A", "#A5D6A7"],
            },
          ],
        },
        options: {
          animation: false,
          responsive: false,
        },
      });

      await new Promise((resolve) => setTimeout(resolve, 500));

      const pieImage = pieCanvas.toDataURL("image/jpeg", 1.0);
      pdf.text("Fleet Distribution", 20, 90);
      pdf.addImage(pieImage, "JPEG", 20, 95, 80, 80);

      pieChart.destroy();

      // ================= BAR CHART =================
      const barCanvas = document.createElement("canvas");
      barCanvas.width = 600;
      barCanvas.height = 400;

      const barChart = new Chart(barCanvas.getContext("2d"), {
        type: "bar",
        data: {
          labels: ["Jan", "Feb", "Mar", "Apr"],
          datasets: [
            {
              label: "CO₂ Emission",
              data: [400, 300, 500, 200],
              backgroundColor: "#2E7D32",
            },
          ],
        },
        options: {
          animation: false,
          responsive: false,
          plugins: {
            legend: { display: false },
          },
        },
      });

      await new Promise((resolve) => setTimeout(resolve, 500));

      const barImage = barCanvas.toDataURL("image/jpeg", 1.0);
      pdf.text("Monthly CO₂ Emission", 110, 90);
      pdf.addImage(barImage, "JPEG", 110, 95, 80, 80);

      barChart.destroy();

      // ================= FOOTER =================
      pdf.setFontSize(9);
      pdf.setTextColor(120);
      pdf.text("Generated by fleetSync System", 20, 285);

      pdf.save("fleetSync.pdf");
    } catch (error) {
      console.error("PDF generation failed:", error);
    }
  };

  return (
    <div style={{ padding: "40px" }}>
      <button
        onClick={generatePDF}
        style={{
          padding: "10px 20px",
          backgroundColor: "#2E7D32",
          color: "white",
          border: "none",
          borderRadius: "6px",
          cursor: "pointer",
        }}
      >
        Download Report
      </button>
    </div>
  );
}
