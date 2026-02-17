import React, { createContext, useContext } from "react";

const shipmentData = {
  labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
  datasets: [
    {
      label: "Shipments",
      data: [12, 19, 8, 15, 22, 30, 18],
      backgroundColor: "#22c55e",
    },
  ],
};

const ShipmentDataContext = createContext(shipmentData);

export const useShipmentData = () => useContext(ShipmentDataContext);

export const ShipmentDataProvider = ({ children }) => (
  <ShipmentDataContext.Provider value={shipmentData}>
    {children}
  </ShipmentDataContext.Provider>
);
