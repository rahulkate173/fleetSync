
import React from "react";
import { useFleetStats } from "../context/FleetStatsContext";

const Card = () => {
  const {
    routeEfficiency,
    totalFleet,
    totalDistance,
    totalCO2,
  } = useFleetStats();

  return (
    <div className="cards">
      <div className="cd">
        <div className="card">
          <h4>Route Efficiency</h4>
          <p>{routeEfficiency}</p>
        </div>

        <div className="card">
          <h4>Total Fleet</h4>
          <p>{totalFleet} Vehicles</p>
        </div>
      </div>

      <div className="cd">
        <div className="card">
          <h4>Total Distance</h4>
          {/* <p>{Number(totalDistance).toLocaleString()} km</p> */}
          <p>{totalDistance} km</p>
        </div>

        <div className="card">
          <h4>Total CO₂</h4>
           <p>{totalCO2}</p>
          {/* <p>{Number(totalCO2).toLocaleString()} kg</p> */}
        </div>
      </div>
    </div>
  );
};

export default Card;