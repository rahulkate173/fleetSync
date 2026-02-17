import React, { useState } from 'react'
import { Bar } from "react-chartjs-2";
const Chart = (props) => {

    let data=props.shipmentData
    console.log(data);
    
    return (
        <div className="chart-section">
            <h3>Shipment Trends (Day-wise)</h3>
            <Bar data={data} />
        </div>
    )
}

export default Chart
