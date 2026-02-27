# fleetSync

## Live Links

- 🔗 [Frontend Application](https://frontend-production-3ba4.up.railway.app/)
- 🔗 [Backend API Documentation](https://server-production-cd13.up.railway.app/docs)
- 🔗 [Demo Video](https://drive.google.com/drive/folders/1NNpGGE-rZzSxzXo9W4qly0AHnnISbRvS)


**Real-Time Supply-Chain Visibility and ETA Predictions** — Fleet management platform built for Hack for Green Bharat.

## Overview

fleetSync provides:

- **User**: Track shipments by reference ID with 4 stages (departed, middle, loc, delivered) and timestamps
- **Admin**: Dashboard with live vehicle map, analytics, PDF reports, and alerts to truck drivers
- **Truck Driver**: Share live GPS → Kafka → Pathway → Server; receive sound alerts for overspeed, route deviation, temperature excursion

## Architecture

```
Truck Driver (GPS) → Kafka (JSON) → Pathway Engine (filter anomalies) → FastAPI Server → Admin Dashboard / User Track
```

| Component | Role |
|-----------|------|
| **Kafka** | Message broker for GPS/temp/coord from truck drivers (JSON format) |
| **Pathway** | Stream processing: filter invalid (0,0), anomalies; POST to server |
| **Server** | FastAPI: ingest endpoint, WebSocket for live map, reference ID tracking, alerts |
| **Frontend** | React: Landing, Track (User), Dashboard (Admin), Driver (Truck Driver) |

## Directory Structure

```
fleetSync/
├── src/                 # Frontend (React)
│   ├── pages/
│   │   ├── Home/        # Landing page
│   │   ├── Track/       # User: reference ID tracking (4 stages)
│   │   ├── Driver/      # Truck driver: location sharing, alerts
│   │   └── Dashboard/   # Admin: live map, analysis
│   └── api/config.js    # API endpoints
├── server/              # FastAPI
│   ├── main.py
│   ├── models.py
│   └── database.py
├── kafka/               # Producer (truck driver JSON → Kafka)
│   └── producer.py
├── pathway/             # Engine (Kafka → filter → POST server)
│   └── engine.py
├── Dockerfile.server
├── Dockerfile.pathway
├── Dockerfile.frontend
├── docker-compose.yml
├── run.sh
└── .env.example
```

## Quick Start (WSL / Linux)

### 1. Environment

```bash
cp .env.example .env
# Edit .env with your values (Kafka, Supabase optional)
```

### 2. Run all in one go

```bash
chmod +x run.sh
./run.sh all
```

Or run individually:

```bash
./run.sh kafka    # Start Kafka (requires Docker)
./run.sh server   # FastAPI on :8000
./run.sh pathway  # Pathway engine (consumes Kafka, POSTs to server)
./run.sh frontend # Vite dev server
```

### 3. Using Docker Compose

```bash
docker-compose up -d
# Server: http://localhost:8000
# Frontend: http://localhost:3000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/track/{reference_id}` | User: get shipment status (4 stages) |
| GET | `/dashboard/summary` | Admin: fleet summary |
| WS | `/dashboard/map/ws` | Admin: live vehicle positions |
| POST | `/truck/gps` | Truck driver: send GPS (→ Kafka) |
| POST | `/ingest/pathway` | Pathway: processed data from Kafka |
| GET | `/alerts/{truck_id}` | Truck driver: fetch alerts |
| POST | `/alerts/send` | Admin: send alert to truck driver |
| GET | `/analysis/generate-pdf` | Admin: generate PDF report |

## Truck Driver Flow

1. Login at landing page (or `/driver`)
2. Grant location permission
3. Enter Vehicle ID and optional Reference ID
4. Click "Start Sharing Location" → GPS sent every 5s to server → Kafka
5. Pathway consumes, filters, POSTs to server
6. Admin sees live positions on map
7. Driver receives alerts (overspeed, route deviation, temp) with sound

## ETA / Routing (Optional)

Credentials for ETA (Google Maps, TomTom, OpenRouteService, OSRM) can be added in `.env`. For free options:

- **OSRM**: `https://router.project-osrm.org` (no key)
- **OpenRouteService**: Free tier with API key

## Deployment (Railway)

Individual Dockerfiles for each service:

- `Dockerfile.server` — FastAPI backend
- `Dockerfile.pathway` — Pathway engine
- `Dockerfile.frontend` — React app (serves User, Admin, Truck Driver)

Deploy each as a separate Railway service. Set environment variables in Railway dashboard.

## Database (Supabase)

Add `SUPABASE_URL` and `SUPABASE_ANON_KEY` in `.env` for auth. `DATABASE_URL` can point to Supabase PostgreSQL.

## License

MIT
