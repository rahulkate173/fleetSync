import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import "./DriverLogin.scss";

const DriverLogin = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
  e.preventDefault();
  setLoading(true);

  try {
    const response = await axios.post(
      "https://server-production-cd13.up.railway.app/api/drivers/login",
      { email, password }
    );
    
    if (response.data.success) {
      
      localStorage.setItem("driverId", response.data.driver.driver_id);
      localStorage.setItem("driverToken", response.data.driver.token);
      localStorage.setItem("driverName", response.data.driver.driver_name);
      
      navigate("/driver/dashboard");
    }
  } catch (error) {
    console.error("Login failed:", error);
    alert("Login failed. Please check your credentials.");
  } finally {
    setLoading(false);
  }
};;

  return (
    <div className="driver-login-page">
      <div className="driver-login-card">
        <h1>Driver Login</h1>
        <p className="subtitle">Sign in to access your dashboard</p>

        <form onSubmit={handleSubmit} className="driver-login-form">
          <label>
            Username
            <input
              type="text"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
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

        <p style={{ marginTop: 16, textAlign: "center", fontSize: 14, color: "#6b7280" }}>
          Don&apos;t have an account?{" "}
          <a href="/driver/signup" style={{ color: "#3b82f6", fontWeight: 600 }}>
            Sign up
          </a>
        </p>
      </div>
    </div>
  );
};

export default DriverLogin;

