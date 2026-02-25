import { NavLink } from "react-router-dom";
import "./UserSidebar.scss";

const UserSidebar = () => {
  return (
    <div className="user-sidebar">
      <div className="user-profile-circle"></div>

      <NavLink
        to="/user/order"
        className={({ isActive }) =>
          isActive ? "user-nav-item active" : "user-nav-item"
        }
      >
        Order
      </NavLink>

      <NavLink
        to="/user/eta"
        className={({ isActive }) =>
          isActive ? "user-nav-item active" : "user-nav-item"
        }
      >
        ETA
      </NavLink>
    </div>
  );
};

export default UserSidebar;