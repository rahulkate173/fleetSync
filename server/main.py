import os
import asyncio
from typing import List, Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi import BackgroundTasks
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from fpdf import FPDF

import models
import database

# --- Pydantic models (Pathway/Kafka contract) ---
class GPSData(BaseModel):
    lat: float
    lon: float
    speed_kmh: float
    temperature: Optional[float] = None
    is_valid: bool = True


class PathwayUpdate(BaseModel):
    update_timestamp: str
    vehicle_id: str
    shipment_id: Optional[str] = None
    reference_id: Optional[str] = None
    gps: GPSData


# In-memory live state (populated by Pathway / Kafka consumer)
fleet_state: Dict[str, dict] = {}
# Reference ID -> shipment tracking (4 stages)
ref_tracking: Dict[str, dict] = {}
# Active WebSocket connections for map
map_connections: List[WebSocket] = []


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=database.engine)
    yield


app = FastAPI(title="fleetSync API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- USER: Reference ID Tracking (4 stages) ---
@app.get("/track/{reference_id}", tags=["User"])
def track_by_reference(reference_id: str, db: Session = Depends(get_db)):
    """User enters reference ID to see delivery status (departed, middle, loc, delivered)."""
    shipment = db.query(models.Shipment).filter(
        models.Shipment.reference_id == reference_id
    ).first()
    if not shipment:
        # Check live state (from truck driver GPS)
        if reference_id in ref_tracking:
            r = ref_tracking[reference_id]
            return {
                "reference_id": reference_id,
                "current_stage": "middle",
                "stages": ["departed", "middle", "loc", "delivered"],
                "timestamps": {},
                "status_code": 1,
                "gps": r.get("gps"),
            }
        return {"error": "Reference ID not found", "reference_id": reference_id}

    stages = ["departed", "middle", "loc", "delivered"]
    stage_idx = min(shipment.status, 3)
    timestamps = {
        "departed": shipment.departed_at.isoformat() if shipment.departed_at else None,
        "middle": shipment.middle_at.isoformat() if shipment.middle_at else None,
        "loc": shipment.loc_at.isoformat() if shipment.loc_at else None,
        "delivered": shipment.delivered_at.isoformat() if shipment.delivered_at else None,
    }
    return {
        "reference_id": reference_id,
        "current_stage": stages[stage_idx],
        "stages": stages,
        "timestamps": timestamps,
        "status_code": shipment.status,
    }


# --- ADMIN: Dashboard ---
@app.get("/dashboard/summary", tags=["Admin"])
def dashboard_summary():
    active = len(fleet_state)
    delayed = sum(1 for v in fleet_state.values() if v.get("eta", {}).get("delay_minutes", 0) > 30)
    return {
        "co2_total_fleet": "5600 kg",
        "fleet_status": {"total": active, "delayed": delayed},
        "route_efficiency": "92%",
        "shipment_trends": [40, 55, 45, 70],
    }


@app.websocket("/dashboard/map/ws")
async def dashboard_map_ws(websocket: WebSocket):
    await websocket.accept()
    map_connections.append(websocket)
    try:
        while True:
            await websocket.send_json(list(fleet_state.values()))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in map_connections:
            map_connections.remove(websocket)


@app.post("/dashboard/voice-ai", tags=["Admin"])
def voice_ai(query: str):
    return {"ai_response": f"Processing your request about: {query}"}


# --- ADMIN: Shipment ---
@app.get("/shipment/search/{truck_id}", tags=["Admin"])
def shipment_search(truck_id: int, db: Session = Depends(get_db)):
    data = db.query(models.Shipment).filter(models.Shipment.truck_id == truck_id).first()
    if not data:
        return {"error": "Not Found"}
    return {
        "location": {"lat": float(data.origin_lat), "lon": float(data.origin_long)},
        "load": float(data.load),
        "co2": data.co2_emission,
        "eta": "12:45 PM",
    }


# --- ADMIN: Analysis ---
@app.get("/analysis/total-report", tags=["Admin"])
def analysis_report(db: Session = Depends(get_db)):
    total_dist = db.query(func.sum(models.Shipment.distance_covered)).scalar() or 0
    return {
        "total_distance": f"{total_dist} km",
        "total_fleet_co2": "8900 kg",
        "available_fleet": 15,
        "pdf_url": "/analysis/generate-pdf",
    }


@app.get("/analysis/generate-pdf", tags=["Admin"])
def generate_pdf(background_tasks: BackgroundTasks):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="fleetSync FLEET ANALYSIS REPORT", ln=1, align="C")
    pdf.cell(200, 10, txt="Real-Time Supply Chain Visibility", ln=1, align="C")
    file = "fleetsync_report.pdf"
    pdf.output(file)
    background_tasks.add_task(os.remove, file)
    return FileResponse(file, filename=file)


# --- ADMIN: Alerts to Truck Driver ---
@app.post("/alerts/send", tags=["Admin"])
def send_alert(truck_id: int, alert_type: str, message: str, severity: str = "warning", db: Session = Depends(get_db)):
    alert = models.Alert(truck_id=truck_id, type=alert_type, severity=severity, message=message)
    db.add(alert)
    db.commit()
    return {"status": "Alert sent", "truck_id": truck_id}


@app.get("/alerts/{truck_id}", tags=["Truck Driver"])
def get_alerts(truck_id: int, db: Session = Depends(get_db)):
    alerts = db.query(models.Alert).filter(models.Alert.truck_id == truck_id).order_by(models.Alert.id.desc()).limit(20)
    return [{"type": a.type, "severity": a.severity, "message": a.message} for a in alerts]


# --- TRUCK DRIVER: Send GPS (publishes to Kafka for Pathway to consume) ---
class TruckGpsInput(BaseModel):
    vehicle_id: str
    lat: float
    lon: float
    speed_kmh: float = 0
    temperature: Optional[float] = None
    reference_id: Optional[str] = None


async def _produce_to_kafka(vehicle_id: str, lat: float, lon: float, speed_kmh: float, temperature: Optional[float], reference_id: Optional[str]):
    from aiokafka import AIOKafkaProducer
    import json
    kafka_server = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic = os.getenv("KAFKA_TOPIC", "fleetsync-gps")
    producer = AIOKafkaProducer(
        bootstrap_servers=kafka_server,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    try:
        payload = {
            "update_timestamp": datetime.utcnow().isoformat() + "Z",
            "vehicle_id": vehicle_id,
            "reference_id": reference_id,
            "gps": {"lat": lat, "lon": lon, "speed_kmh": speed_kmh, "temperature": temperature, "is_valid": not (lat == 0 and lon == 0)},
        }
        await producer.send_and_wait(topic, value=payload, key=vehicle_id.encode("utf-8"))
    finally:
        await producer.stop()


@app.post("/truck/gps", tags=["Truck Driver"])
async def truck_gps(data: TruckGpsInput):
    """Truck driver sends GPS - forwards to Kafka; Pathway consumes and POSTs back to /ingest/pathway."""
    try:
        await _produce_to_kafka(
            data.vehicle_id, data.lat, data.lon, data.speed_kmh, data.temperature, data.reference_id
        )
        return {"status": "sent to Kafka"}
    except Exception:
        # Fallback: store directly if Kafka unavailable
        payload = {
            "update_timestamp": datetime.utcnow().isoformat() + "Z",
            "vehicle_id": data.vehicle_id,
            "reference_id": data.reference_id,
            "gps": {
                "lat": data.lat,
                "lon": data.lon,
                "speed_kmh": data.speed_kmh,
                "temperature": data.temperature,
                "is_valid": not (data.lat == 0 and data.lon == 0),
            },
        }
        fleet_state[data.vehicle_id] = payload
        if data.reference_id:
            ref_tracking[data.reference_id] = payload
        return {"status": "stored (Kafka unavailable)"}


# --- INGEST: Pathway / Kafka (truck driver data) ---
@app.post("/ingest/pathway", tags=["System"])
async def ingest_pathway(data: PathwayUpdate, db: Session = Depends(get_db)):
    print(f"[INGEST] Vehicle: {data.vehicle_id} | GPS: {data.gps.lat}, {data.gps.lon}")
    fleet_state[data.vehicle_id] = data.model_dump()
    if data.reference_id:
        ref_tracking[data.reference_id] = {
            "reference_id": data.reference_id,
            "vehicle_id": data.vehicle_id,
            "gps": data.gps.model_dump(),
        }
    return {"status": "Live & DB Updated"}


# --- Notifications (create shipment) ---
@app.post("/notifications/create-batch", tags=["Admin"])
def create_batch(ticket: dict, db: Session = Depends(get_db)):
    sid = ticket.get("shipment_id") or ticket.get("ticket_id") or (db.query(models.Shipment).count() + 1)
    new_s = models.Shipment(
        shipment_id=sid,
        reference_id=ticket.get("reference_id") or f"REF-{sid}",
        truck_id=ticket.get("driver_id") or ticket.get("truck_id"),
        origin_lat=ticket.get("origin_lat", 0),
        origin_long=ticket.get("origin_long", 0),
        destination_lat=ticket.get("destination_lat", 0),
        destination_long=ticket.get("destination_long", 0),
        load=ticket.get("load", 0),
        status=ticket.get("status", 0),
        co2_emission=ticket.get("co2_emission", "0"),
        distance_covered=ticket.get("distance_covered", 0),
    )
    db.add(new_s)
    db.commit()
    return {"status": "Ticket Assigned to Shipment Table"}


@app.get("/settings/config", tags=["Admin"])
def get_settings():
    return {"units": "metric", "refresh_rate": "5s", "theme": "enterprise-dark"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
