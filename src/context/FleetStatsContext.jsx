import React, { createContext, useContext, useEffect, useState } from "react";
import axios from "axios";
import { log } from "three";
const FleetStatsContext = createContext();

export const FleetStatsProvider = ({ children }) => {

  const [routeEfficiency, setRouteEfficiency] = useState(0);
  const [totalFleet, setTotalFleet] = useState(42);
  const [totalDistance, setTotalDistance] = useState(12540);
  const [totalCO2, setTotalCO2] = useState(2540);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get("https://server-production-cd13.up.railway.app/dashboard/summary");
        const data = res.data;

        console.log("Backend Response:", data);

        setRouteEfficiency(data.route_efficiency || 0);
        setTotalFleet(data.total || 0);
        setTotalDistance(data.total_distance || 0);
        setTotalCO2(data.co2_total_fleet || 0);

      } catch (err) {
        console.error("Error fetching dashboard summary:", err);
      }
    };

    fetchData();
  }, []);

  return (
    <FleetStatsContext.Provider
      value={{
        routeEfficiency,
        totalFleet,
        totalDistance,
        totalCO2,
      }}
    >
      {children}
    </FleetStatsContext.Provider>
  );
};

export const useFleetStats = () => useContext(FleetStatsContext);