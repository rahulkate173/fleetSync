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
      await axios.post("https://server-production-cd13.up.railway.app/api/drivers/login", {
        email,
        password,
      });

      alert("Driver logged in successfully");
      // TODO: navigate to driver dashboard or store token as needed
    } catch (error) {
      console.error("Driver login failed", error);
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

