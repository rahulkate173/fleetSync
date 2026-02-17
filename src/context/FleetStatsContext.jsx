import React, { createContext, useContext, useState } from "react";

const FleetStatsContext = createContext();

export const FleetStatsProvider = ({ children }) => {
  const [stats, setStats] = useState({
    routeEfficiency: 87,
    totalFleet: 42,
    totalDistance: 12540,
    totalCO2: 2540,
  });

  // Update any stat by key
  const updateStat = (key, value) => {
    setStats((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <FleetStatsContext.Provider value={{ stats, updateStat }}>
      {children}
    </FleetStatsContext.Provider>
  );
};

export const useFleetStats = () => useContext(FleetStatsContext);
