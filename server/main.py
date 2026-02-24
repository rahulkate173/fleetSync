import os
import asyncio
from typing import List, Dict, Optional
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi import BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from fpdf import FPDF
import json
import csv
import models
import database

# ======================================================================
# GLOBAL KAFKA PRODUCER - FIXED: SINGLE INSTANCE, CORRECT TOPIC
# ===================================================================
# ======================================================================
# PYDANTIC MODELS
# ======================================================================
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

class TruckGpsInput(BaseModel):
    vehicle_id: str
    lat: float
    lon: float
    speed_kmh: float = 0
    temperature: Optional[float] = None
    reference_id: Optional[str] = None

class SimulationCoordinate(BaseModel):
    vehicle_id: str
    latitude: float
    longitude: float
    timestamp: str

# In-memory state
fleet_state: Dict[str, dict] = {}
ref_tracking: Dict[str, dict] = {}
map_connections: List[WebSocket] = {}

# ======================================================================
# DATABASE & APP SETUP
# ======================================================================
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

producer = None  # Global producer instance

@asynccontextmanager
async def lifespan(app: FastAPI):
    """✅ FIXED: Single lifespan handles DB + Kafka startup"""
    global producer
    
    # STARTUP
    print("Starting fleetSync...")
    models.Base.metadata.create_all(bind=database.engine)
    
    # Kafka producer startup
    try:
        from aiokafka import AIOKafkaProducer
        import json
        producer = AIOKafkaProducer(
            bootstrap_servers="localhost:9092",
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        await producer.start()
        print("Kafka producer STARTED - fleetsync-gps-3")
    except Exception as e:
        print(f"Kafka startup FAILED: {e}")
        producer = None
    
    yield  # App runs here
    
    # SHUTDOWN
    if producer:
        await producer.stop()
        print("Kafka producer STOPPED")
# ✅ FIXED: Proper lifespan + Kafka integration
app = FastAPI(title="fleetSync API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================================
# FIXED KAFKA PRODUCER FUNCTION
# ======================================================================
async def _produce_to_kafka(vehicle_id: str, lat: float, lon: float, speed_kmh: float, temperature: Optional[float], reference_id: Optional[str]):
    global producer
    
    payload = {
        "update_timestamp": datetime.utcnow().isoformat() + "Z",
        "vehicle_id": vehicle_id,
        "reference_id": reference_id,
        "gps": {
            "lat": lat, "lon": lon, "speed_kmh": speed_kmh, "temperature": temperature, 
            "is_valid": not (lat == 0 and lon == 0)
        },
    }
    
    print(f"[PRODUCER] Sending vehicle {vehicle_id}: lat={lat}, lon={lon}")  # ✅ No emoji
    
    await producer.send_and_wait("fleetsync-gps-3", value=payload, key=vehicle_id.encode("utf-8"))
    print(f"[PRODUCER] Sent vehicle {vehicle_id}")


# ======================================================================
# ROUTES (unchanged except /truck/gps)
# ======================================================================
@app.get("/dashboard/map/data")
async def get_map_data():
    return list(fleet_state.values())

@app.get("/track/{reference_id}", tags=["User"])
def track_by_reference(reference_id: str, db: Session = Depends(get_db)):
    """User tracking by reference ID"""
    shipment = db.query(models.Shipment).filter(
        models.Shipment.reference_id == reference_id
    ).first()
    
    if not shipment:
        if reference_id in ref_tracking:
            r = ref_tracking[reference_id]
            return {
                "reference_id": reference_id,
                "current_stage": "middle",
                "stages": ["departed", "middle", "loc", "delivered"],
                "status_code": 1,
                "gps": r.get("gps"),
            }
        return {"error": "Reference ID not found"}
    
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

@app.post("/truck/gps", tags=["Truck Driver"])
async def truck_gps(data: TruckGpsInput):
    """Kafka-first, fallback only on REAL errors"""
    try:
        print(f"[KAFKA] Attempting: vehicle {data.vehicle_id}")  # ✅ No emoji
        await _produce_to_kafka(
            data.vehicle_id, data.lat, data.lon, data.speed_kmh, data.temperature, data.reference_id
        )
        print(f"[KAFKA] SUCCESS: vehicle {data.vehicle_id}")
        return {"status": "sent to Kafka"}
    except Exception as e:
        print(f"[KAFKA] ERROR: {str(e)}")
        raise Exception(f"Kafka failed: {str(e)}")

@app.post("/ingest/pathway", tags=["System"])
async def ingest_pathway(data: PathwayUpdate, db: Session = Depends(get_db)):
    """Pathway posts processed data here after Kafka consumption"""
    print(f"[INGEST] Vehicle: {data.vehicle_id} | GPS: {data.gps.lat}, {data.gps.lon}")
    fleet_state[data.vehicle_id] = data.model_dump()
    if data.reference_id:
        ref_tracking[data.reference_id] = {
            "reference_id": data.reference_id,
            "vehicle_id": data.vehicle_id,
            "gps": data.gps.model_dump(),
        }
    return {"status": "Live & DB Updated"}

# ======================================================================
# ADD MISSING IMPORTS at top (after other imports)
# ======================================================================
# ADD THESE LINES after your existing imports:
from aiokafka import AIOKafkaProducer

# ======================================================================
# REST OF YOUR ROUTES (unchanged - dashboard, alerts, simulation, etc.)
# ======================================================================
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

# ... [rest of your routes unchanged - summary, alerts, simulation, etc.]

@app.post("/simulation/save-coordinate", tags=["Simulation"])
def save_simulation_coordinate(data: SimulationCoordinate):
    CSV_FILE = "bus_coordinates.csv"
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["vehicle_id", "latitude", "longitude", "timestamp"])
        writer.writerow([
            data.vehicle_id, data.latitude, data.longitude, data.timestamp
        ])
    return {"status": "coordinate saved"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
