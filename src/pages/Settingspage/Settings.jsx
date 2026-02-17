import { useState } from "react";
import "./Setting.scss";
import Sidebar from "../../components/Sidebar";

const Setting = () => {
  const [formData, setFormData] = useState({
    name: "Admin User",
    email: "admin@greenlogistics.com",
    region: "India",
    emissionLimit: 500,
    notifications: true,
  });

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;

    setFormData({
      ...formData,
      [name]: type === "checkbox" ? checked : value,
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    alert("Settings Saved Successfully ✅");
  };

  return (
    <div className="setting-page">
      {/* Sidebar */}
   <Sidebar/>

      {/* Main Content */}
      <div className="setting-content">
        <h2>Admin Settings</h2>

        <form onSubmit={handleSubmit} className="settings-form">
          
          {/* Profile Section */}
          <div className="section">
            <h3>Profile Information</h3>

            <label>Name</label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
            />

            <label>Email</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
            />
          </div>

          {/* Password Section */}
          <div className="section">
            <h3>Change Password</h3>

            <label>New Password</label>
            <input type="password" placeholder="Enter new password" />

            <label>Confirm Password</label>
            <input type="password" placeholder="Confirm password" />
          </div>

          {/* System Preferences */}
          <div className="section">
            <h3>System Preferences</h3>

            <label>Default Region</label>
            <select
              name="region"
              value={formData.region}
              onChange={handleChange}
            >
              <option value="India">India</option>
              <option value="USA">USA</option>
              <option value="Europe">Europe</option>
            </select>

            <label>CO₂ Emission Alert Threshold (kg)</label>
            <input
              type="number"
              name="emissionLimit"
              value={formData.emissionLimit}
              onChange={handleChange}
            />

            <div className="checkbox">
              <input
                type="checkbox"
                name="notifications"
                checked={formData.notifications}
                onChange={handleChange}
              />
              <span>Enable Notifications</span>
            </div>
          </div>

          <button type="submit" className="save-btn">
            Save Settings
          </button>

        </form>
      </div>
    </div>
  );
};

export default Setting;
