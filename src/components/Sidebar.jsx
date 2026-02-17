
import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "./Sidebar.scss";
import { UserButton } from "@clerk/clerk-react";

import { ImExit } from "react-icons/im";

const Sidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const currentPath = location.pathname;

  const handleClick = (page) => {
    navigate(`/${page}`);
  };

  return (
    <div className="sidebar">
      <div className="side">

        <div className="profile-circle">
          <UserButton
            afterSignOutUrl="/"
            appearance={{
              elements: {
                avatarBox: "clerk-avatar"
              }
            }}
          />
        </div>

        <button
          className="back-btn"
          onClick={() => navigate("/")}
        >
          <ImExit />
        </button>
      </div>


      <div
        className={`sidebar-item ${currentPath === "/dashboard" ? "active" : ""}`}
        onClick={() => handleClick("dashboard")}
      >
        <button>Dashboard</button>
      </div>

      <div
        className={`sidebar-item ${currentPath === "/shipment" ? "active" : ""}`}
        onClick={() => handleClick("shipment")}
      >
        <button>Shipment</button>
      </div>

      <div
        className={`sidebar-item ${currentPath === "/analysis" ? "active" : ""}`}
        onClick={() => handleClick("analysis")}
      >
        <button>Analysis</button>
      </div>

      <div
        className={`sidebar-item ${currentPath === "/notification" ? "active" : ""}`}
        onClick={() => handleClick("notification")}
      >
        <button>Notification</button>
      </div>

      <div
        className={`sidebar-item ${currentPath === "/settings" ? "active" : ""}`}
        onClick={() => handleClick("settings")}
      >
        <button>Setting</button>
      </div>
    </div>
  );
};

export default Sidebar;
