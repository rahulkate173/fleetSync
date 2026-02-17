// import React, { useState } from "react";
// import "./AdminLogin.scss";



// import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/clerk-react';

// function AdminLogin() {
//   return (
//     <header>
//       {/* Show the sign-in and sign-up buttons when the user is signed out */}
//       <SignedOut>
//         <SignInButton />
//         <SignUpButton />
//       </SignedOut>
//       {/* Show the user button when the user is signed in */}
//       <SignedIn>
//         <UserButton />
//       </SignedIn>
//     </header>
//   );
// }



// export default AdminLogin;

// import "./AdminLogin.scss";
// import { 
//   SignedIn, 
//   SignedOut, 
//   SignIn, 
//   SignUp, 
//   useUser 
// } from "@clerk/clerk-react";
// import { useNavigate } from "react-router-dom";
// import { useEffect } from "react";

// function AdminLogin() {

//   const { isSignedIn } = useUser();
//   const navigate = useNavigate();

//   // Redirect after login
// 

//   return (
//     <div className="admin-login-page">

//       <div className="login-card">

//         <h2>Admin Portal</h2>
//         <p>Secure access to Fleet Sync Dashboard</p>

//         <SignedOut>
//           <div className="auth-container">
//             <SignIn routing="hash" />
//           </div>
//         </SignedOut>

//         <SignedIn>
//           <p className="redirect-text">Redirecting to dashboard...</p>
//         </SignedIn>

//       </div>

//     </div>
//   );
// }

// export default AdminLogin;

// import "./AdminLogin.scss";
// import { SignedIn, SignedOut, SignIn } from "@clerk/clerk-react";

// function AdminLogin() {
//   //   useEffect(() => {
//   //   if (isSignedIn) {
//   //     navigate("/dashboard");
//   //   }
//   // }, [isSignedIn, navigate]);
//   return (
//     <div className="admin-login-page">
//       <div className="login-card">
//         <h2>Admin Portal</h2>
//         <p>Secure access to Fleet Sync Dashboard</p>

//         <SignedOut>
//           <div className="auth-container">
//             <SignIn routing="hash" afterSignInUrl="/dashboard" />
//           </div>
//         </SignedOut>

//         <SignedIn>
//           <p className="redirect-text">Redirecting to dashboard...</p>
//         </SignedIn>

//       </div>
//     </div>
//   );
// }

// export default AdminLogin;

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
          <SignIn
            routing="hash"
            afterSignInUrl="/dashboard"
            afterSignUpUrl="/dashboard"
          />
        </SignedOut>

        <SignedIn>
          <Navigate to="/dashboard" replace />
        </SignedIn>

      </div>
    </div>
  );
}

export default AdminLogin;
