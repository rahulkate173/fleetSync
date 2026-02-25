
import { SignIn, SignedIn, SignedOut } from "@clerk/clerk-react";
import { Navigate } from "react-router-dom";
import "./UserLogin.scss";

function UserLogin() {
  return (
    <div className="user-login-page">
      <div className="login-card user-login-card">
        <h2>User Portal</h2>
        <p>Sign in to manage your shipments</p>

        <SignedOut>
          <div className="auth-container">
            <SignIn
              routing="hash"
              afterSignInUrl="/user/order"
              afterSignUpUrl="/user/order"
            />
          </div>
        </SignedOut>

        <SignedIn>
          <Navigate to="/user/order" replace />
        </SignedIn>
      </div>
    </div>
  );
}

export default UserLogin;