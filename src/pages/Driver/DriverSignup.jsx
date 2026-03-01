import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import "./DriverLogin.scss";

const DriverSignup = () => {
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [truckId, setTruckId] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      alert("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      await axios.post(
        "https://server-production-cd13.up.railway.app/api/drivers/signup",
        {
          full_name: fullName,
          username,
          password,
          ...(truckId ? { truck_id: truckId } : {}),
        }
      );

      alert("Signup successful! Please log in.");
      navigate("/driver/login");
    } catch (error) {
      const msg = error.response?.data?.detail || "Signup failed. Please try again.";
      alert(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="driver-login-page">
      <div className="driver-login-card">
        <h1>Driver Sign Up</h1>
        <p className="subtitle">Create your driver account</p>

        <form onSubmit={handleSubmit} className="driver-login-form">
          <label>
            Full Name
            <input
              type="text"
              placeholder="Enter your full name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </label>

          <label>
            Username
            <input
              type="text"
              placeholder="Choose a username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              placeholder="Create a password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>

          <label>
            Confirm Password
            <input
              type="password"
              placeholder="Confirm your password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </label>

          <label>
            Truck ID (optional)
            <input
              type="text"
              placeholder="e.g. TRUCK-001"
              value={truckId}
              onChange={(e) => setTruckId(e.target.value)}
            />
          </label>

          <button type="submit" className="driver-login-btn" disabled={loading}>
            {loading ? "Signing up..." : "Sign Up"}
          </button>
        </form>

        <p style={{ marginTop: 16, textAlign: "center", fontSize: 14, color: "#6b7280" }}>
          Already have an account?{" "}
          <a href="/driver/login" style={{ color: "#3b82f6", fontWeight: 600 }}>
            Log in
          </a>
        </p>
      </div>
    </div>
  );
};

export default DriverSignup;
