

import { SignIn, SignedIn, SignedOut } from "@clerk/clerk-react";
import { Navigate } from "react-router-dom";
import './AdminLogin.scss'
function AdminLogin() {
  return (
    <div className="admin-login-page">
      <div className="login-card">
        <h2>Admin Portal</h2>
        <p>Secure access to Fleet Sync Dashboard</p>

        <SignedOut>
          <div className="auth-container">
            <SignIn
              routing="hash"
              afterSignInUrl="/dashboard"
              afterSignUpUrl="/dashboard"
            />
          </div>
        </SignedOut>

        <SignedIn>
          <Navigate to="/dashboard" replace />
        </SignedIn>

      </div>
    </div>
  );
}

export default AdminLogin;
