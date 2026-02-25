import React from 'react'
import Home from './pages/Home/Home'
import { Route, Routes } from 'react-router-dom'
import Track from './pages/Track/Track'
import Driver from './pages/Driver/DriverDashboard'
import Dashboard from './pages/Dashboard/Dashboard'
import Shipment from './pages/Shipment/Shipment'
import Analysis from './pages/Analysis/Analysis'
import Notification from './pages/Notification/Notification'
import Setting from './pages/Settingspage/Settings'
import AdminLogin from './pages/Login/AdminLogin'
import OrderPage from './pages/User/OrderPage'
import EtaPage from './pages/User/EtaPage'
import UserLogin from './pages/user/UserLogin'



const App = () => {
   
  return (
    <div>
     
     <Routes>
        <Route path="/" element={<Home />} />
          <Route path="/track" element={<Track/>} />
          <Route path="/driver" element={<Driver/>} />
              <Route path="/dashboard" element={<Dashboard/>} />
               <Route path="/shipment" element={<Shipment/>} />
                 <Route path="/analysis" element={<Analysis/>} />
                  <Route path="/notification" element={<Notification/>} />
                  <Route path="/settings" element={<Setting/>} />
                   <Route path="/login" element={<AdminLogin/>} />
                     <Route path="/user" element={<UserLogin/>} />
                       <Route path="/user/order" element={<OrderPage/>} />
                         <Route path="/user/eta" element={<EtaPage/>} />

           
      </Routes>
    </div>
   
  )
}

export default App
