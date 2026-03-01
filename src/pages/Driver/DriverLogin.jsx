import React, { useState } from "react";
import axios from "axios";
import "./DriverLogin.scss";

const DriverLogin = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
  e.preventDefault();
  setLoading(true);

  try {
    const response = await axios.post(
      "https://server-production-cd13.up.railway.app/api/drivers/login",
      { email, password }
    );
    
    if (response.data.success) {
      // Store driver ID and token
      localStorage.setItem('driverId', response.data.driver.id);
      localStorage.setItem('driverToken', response.data.driver.token);
      localStorage.setItem('driverName', response.data.driver.driver_name);
      
      // Navigate to dashboard
      navigate('/driver/dashboard');
    }
  } catch (error) {
    alert("Login failed. Please check your credentials.");
  } finally {
    setLoading(false);
  }
};

  return (
    <div className="driver-login-page">
      <div className="driver-login-card">
        <h1>Driver Login</h1>
        <p className="subtitle">Sign in to access your dashboard</p>

        <form onSubmit={handleSubmit} className="driver-login-form">
          <label>
            Email
            <input
              type="email"
              placeholder="driver@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>

          <button type="submit" className="driver-login-btn" disabled={loading}>
            {loading ? "Logging in..." : "Login"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default DriverLogin;

