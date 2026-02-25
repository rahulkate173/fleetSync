import { NavLink } from "react-router-dom";
import { UserButton } from "@clerk/clerk-react";
import "./UserSidebar.scss";

const UserSidebar = () => {
  return (
    <div className="user-sidebar">
      <div className="user-profile-circle">
        <UserButton
          appearance={{
            elements: {
              avatarBox: "user-avatar-circle",
            },
          }}
          afterSignOutUrl="/"
        />
      </div>

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