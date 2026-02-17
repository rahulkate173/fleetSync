----------------------------------------

# FRONTEND – BACKEND CONNECTION DOCUMENTATION

## ROUTES

| Path                | Component                | Role   |
|---------------------|-------------------------|--------|
| /                   | Home.jsx                | User   |
| /login              | AdminLogin.jsx          | Admin  |
| /dashboard          | Dashboard.jsx           | Admin  |
| /analysis           | Analysis.jsx            | Admin  |
| /shipment           | Shipment.jsx            | Admin  |
| /track              | Track.jsx               | Admin  |
| /notification       | Notification.jsx        | Admin  |
| /settings           | Settings.jsx            | Admin  |

> **Note:** All routes are managed via React Router in main.jsx using BrowserRouter.

---

## COMPONENTS

- Sidebar.jsx
- Side.jsx
- Header.jsx
- AiModal.jsx
- Card.jsx
- Chart.jsx
- MultiVehicleMap.jsx
- FleetHtmlMap.jsx
- ReportPDF.jsx

---

## API CONNECTIONS

### Shipment.jsx (Admin)
- **Endpoint:** _No direct API call in current code (uses dummyData)._
- **Expected:** Will call shipment tracking endpoint in future.
- **Request Body:** N/A
- **Response:** N/A

### Analysis.jsx (Admin)
- **Endpoint:** _No direct API call in current code (uses context for stats and chart data)._
- **Expected:** Will fetch analytics data from backend.
- **Request Body:** N/A
- **Response:** N/A

### Dashboard.jsx (Admin)
- **Endpoint:** _No direct API call in current code (uses context for stats and chart data)._
- **Expected:** Will fetch dashboard stats and live vehicle data from backend.
- **Request Body:** N/A
- **Response:** N/A

### Chart.jsx (Admin)
- **Endpoint:** _No direct API call in current code (receives shipmentData from context)._
- **Expected:** Will visualize data fetched elsewhere.

### Notification.jsx, Settings.jsx, Track.jsx, Home.jsx
- **Endpoint:** _No direct API call in current code (UI only or context-driven)._

---

## PROTECTED ROUTES

- All admin pages (Dashboard, Analysis, Shipment, Track, Notification, Settings) are intended to be protected.
- Protection is expected to be handled via Clerk authentication and route guards (see below).

---

## AUTHENTICATION-RELATED FILES

- **main.jsx**: Integrates ClerkProvider and BrowserRouter.
- **AdminLogin.jsx**: Login page for admin.
- **ClerkProvider**: Used in main.jsx to wrap the app.
- **Authentication context**: Clerk is used for authentication.

---

## CLERK AUTHENTICATION USAGE

- **ClerkProvider**: Used in main.jsx to wrap the entire app.
- **SignedIn, SignedOut, useUser**: Not directly found in the provided code, but ClerkProvider is present, so these may be used in other files or planned for use.
- **Authentication logic**: Likely handled in AdminLogin.jsx and protected routes, but explicit usage of SignedIn/SignedOut/useUser is not present in the current codebase.

---

## SUMMARY

- All API calls are currently stubbed or handled via context/dummy data.
- All admin pages are intended to be protected and require authentication.
- ClerkProvider is set up for authentication, but explicit usage of Clerk hooks/components is not found in the code provided.
- Backend endpoints, request/response formats, and authentication headers should be coordinated with the frontend team as integration proceeds.

----------------------------------------
