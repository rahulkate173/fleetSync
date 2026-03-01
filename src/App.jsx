
import React from 'react'
import Home from './pages/Home/Home'
import { Route, Routes } from 'react-router-dom'
import Track from './pages/Track/Track'
import Driver from './pages/Driver/DriverDashboard'
import Dashboard from './pages/Dashboard/Dashboard'
import Shipment from './pages/Shipment/Shipment'
import Analysis from './pages/Analysis/Analysis'
import Setting from './pages/Settingspage/Settings'
import AdminLogin from './pages/Login/AdminLogin'
import OrderPage from './pages/user/OrderPage'
import EtaPage from './pages/user/EtaPage'
import UserLogin from './pages/user/UserLogin'
import { ThemeProvider } from './context/ThemeContext'
import DriverDashboard from './pages/Driver/DriverDashboard'
import DriverLogin from './pages/Driver/DriverLogin'
import DriverSignup from './pages/Driver/DriverSignup'
// import ThemeToggle from "./components/ThemeToggle"
// import React from "react";
// import Home from "./pages/Home/Home";
// import { Route, Routes } from "react-router-dom";
// import DriverDashboard from "./pages/Driver/DriverDashboard";
// import Dashboard from "./pages/Dashboard/Dashboard";
// import Shipment from "./pages/Shipment/Shipment";
// import Analysis from "./pages/Analysis/Analysis";
// import Notification from "./pages/Notification/Notification";
// import Setting from "./pages/Settingspage/Settings";
// import AdminLogin from "./pages/Login/AdminLogin";
// import OrderPage from "./pages/User/OrderPage";
// import EtaPage from "./pages/User/EtaPage";
// import UserLogin from "./pages/user/UserLogin";
// import DriverLogin from "./pages/Driver/DriverLogin";
// import { ThemeProvider } from "./context/ThemeContext";
// import ThemeToggle from "./components/ThemeToggle";
// import "./theme.css";



const App = () => {
  return (
    <ThemeProvider>
      <div>
        {/* <ThemeToggle /> */}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/driver" element={<DriverDashboard />} />
          <Route path="/driver/dashboard" element={<DriverDashboard />} />
          <Route path="/driver/login" element={<DriverLogin />} />
          <Route path="/driver/signup" element={<DriverSignup />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/shipment" element={<Shipment />} />
          <Route path="/analysis" element={<Analysis />} />
          <Route path="/notification" element={<Notification />} />
          <Route path="/settings" element={<Setting />} />
          <Route path="/login" element={<AdminLogin />} />
          <Route path="/user" element={<UserLogin />} />
          <Route path="/user/order" element={<OrderPage />} />
          <Route path="/user/eta" element={<EtaPage />} />
        </Routes>
      </div>
    </ThemeProvider>
  );
};

export default App;
