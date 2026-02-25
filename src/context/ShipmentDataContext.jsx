
import React, { createContext, useContext, useEffect, useState } from "react";
import axios from "axios";

const ShipmentDataContext = createContext();

export const useShipmentData = () => useContext(ShipmentDataContext);

export const ShipmentDataProvider = ({ children }) => {
  const [shipmentData, setShipmentData] = useState({
    labels: [],
    datasets: [
      {
        label: "Shipments Per Day",
        data: [],
        backgroundColor: "#00adb5",
      },
    ],
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get("http://localhost:8000/dashboard/summary");
        const data = res.data;

        const trends = data.shipment_trends || [];

        setShipmentData({
          labels: trends.map((_, index) => `Day ${index + 1}`),
          datasets: [
            {
              label: "Shipments Per Day",
              data: trends,
              backgroundColor: "#00adb5",
            },
          ],
        });

      } catch (err) {
        console.error("Error fetching shipment data:", err);
      }
    };

    fetchData();
  }, []);

  return (
    <ShipmentDataContext.Provider value={shipmentData}>
      {children}
    </ShipmentDataContext.Provider>
  );
};