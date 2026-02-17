import React from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import "leaflet/dist/leaflet.css";
import { ClerkProvider } from '@clerk/clerk-react';
import { BrowserRouter } from "react-router-dom";
import { FleetStatsProvider } from './context/FleetStatsContext';
import { ShipmentDataProvider } from "./context/ShipmentDataContext";
import App from './App.jsx';

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || "pk_test_placeholder";

createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <ClerkProvider publishableKey={PUBLISHABLE_KEY}>
      <ShipmentDataProvider>
        <FleetStatsProvider>
          <App />
        </FleetStatsProvider>
      </ShipmentDataProvider>
    </ClerkProvider>
  </BrowserRouter>
)
