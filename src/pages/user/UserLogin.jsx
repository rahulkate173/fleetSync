
import { SignIn, SignedIn, SignedOut } from "@clerk/clerk-react";
import { Navigate } from "react-router-dom";
import './UserLogin.scss'
function UserLogin() {
  return (
    <div className="user-login-page">
      <div className="login-card">
        <h2>Admin Portal</h2>
        <p>Secure access to Fleet Sync Dashboard</p>

        <SignedOut>
          <SignIn
            routing="hash"
            afterSignInUrl="/user/order"
            afterSignUpUrl="/user/order"
          />
        </SignedOut>

        <SignedIn>
          <Navigate to="/user/order" replace />
        </SignedIn>

      </div>
    </div>
  );
}

export default UserLogin;