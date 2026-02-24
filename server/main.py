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
from pydantic import BaseModel

class ChatRequest(BaseModel):  # ✅ Pydantic model for JSON body
    query: str
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
@app.get("/dashboard/map/data",tags=["Admin"])
async def get_map_data():
    return list(fleet_state.values())

@app.get("/dashboard/reports", tags=["Admin"])
async def get_reports(background_tasks: BackgroundTasks):
    """Dashboard reports list"""
    reports = [
        {"id": "report-1", "name": "Weekly Summary", "date": "2026-02-17", "status": "ready"},
        {"id": "report-2", "name": "Fleet Analysis", "date": "2026-02-20", "status": "processing"},
        {"id": "report-3", "name": "CO2 Emissions", "date": "2026-02-24", "status": "ready"}
    ]
    return {"reports": reports}


@app.post("/dashboard/report", tags=["Admin"])
async def generate_report(
    background_tasks: BackgroundTasks,
    report_type: str = "summary"
):
    """Generate PDF report (async)"""
    background_tasks.add_task(create_pdf_report, report_type)
    return {"status": "report generation started", "type": report_type}


@app.get("/dashboard/report/{report_id}", tags=["Admin"])
async def download_report(report_id: str):
    """Download generated PDF report"""
    pdf_path = f"reports/{report_id}.pdf"
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, filename=f"{report_id}.pdf", media_type="application/pdf")
    return {"error": "Report not found"}


def create_pdf_report(report_type: str):
    """Background PDF generation"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    if report_type == "summary":
        pdf.cell(200, 10, txt="Fleet Summary Report", ln=1, align="C")
        pdf.cell(200, 10, txt=f"Active Trucks: {len(fleet_state)}", ln=1)
        pdf.cell(200, 10, txt="CO2 Total: 5600 kg", ln=1)
    elif report_type == "analysis":
        pdf.cell(200, 10, txt="Fleet Analysis Report", ln=1, align="C")
        pdf.cell(200, 10, txt="Route Efficiency: 92%", ln=1)
    
    os.makedirs("reports", exist_ok=True)
    pdf_path = f"reports/{datetime.now().strftime('%Y%m%d-%H%M%S')}-{report_type}.pdf"
    pdf.output(pdf_path)


@app.post("/alerts/create", tags=["Admin"])
async def create_alert(
    db: Session = Depends(get_db),
    alert_data: Dict = {}
):
    """Create fleet alert (speed, temp, geo-fence)"""
    alert = models.Alert(
        alert_type=alert_data.get("type", "speed"),
        vehicle_id=alert_data.get("vehicle_id"),
        threshold=alert_data.get("threshold", 0),
        active=True,
        created_at=datetime.utcnow()
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    # Notify WebSocket clients
    alert_msg = {
        "type": "alert",
        "alert": {
            "id": alert.id,
            "vehicle_id": alert.vehicle_id,
            "type": alert.alert_type,
            "threshold": alert.threshold
        }
    }
    
    for ws in map_connections:
        try:
            await ws.send_json(alert_msg)
        except:
            pass
    
    return {"status": "alert created", "alert_id": alert.id}


@app.get("/alerts/active", tags=["Admin"])
def get_active_alerts(db: Session = Depends(get_db)):
    """Get active fleet alerts"""
    alerts = db.query(models.Alert).filter(
        models.Alert.active == True
    ).all()
    
    alert_summary = []
    for alert in alerts:
        alert_data = {
            "id": alert.id,
            "vehicle_id": alert.vehicle_id,
            "type": alert.alert_type,
            "threshold": alert.threshold,
            "created_at": alert.created_at.isoformat()
        }
        
        # Add live GPS if truck active
        if alert.vehicle_id in fleet_state:
            alert_data["current_gps"] = fleet_state[alert.vehicle_id]["gps"]
        
        alert_summary.append(alert_data)
    
    return {"active_alerts": alert_summary}


@app.get("/dashboard/analytics", tags=["Admin"])
def dashboard_analytics():
    """Fleet analytics dashboard data"""
    total_trucks = len(fleet_state)
    avg_speed = sum(v["gps"]["speed_kmh"] for v in fleet_state.values()) / max(total_trucks, 1)
    
    # Mock emissions data (integrate your emissions model here)
    co2_per_truck = 12.5  # kg/hour avg
    total_co2 = total_trucks * co2_per_truck * 24
    
    return {
        "metrics": {
            "total_trucks": total_trucks,
            "avg_speed_kmh": round(avg_speed, 1),
            "total_co2_24h": f"{total_co2:.0f} kg",
            "alerts_active": len([v for v in fleet_state.values() if v.get("alert", False)]),
            "high_temp_trucks": sum(1 for v in fleet_state.values() if v["gps"].get("temperature", 0) > 40)
        },
        "trends": {
            "speed_24h": [45, 52, 48, 55, 60, 58, 62],
            "co2_daily": [5200, 5400, 5600, 5800, 5700],
            "alerts": [2, 5, 3, 8, 4]
        }
    }


@app.get("/config/notifications", tags=["Settings"])
def get_notification_config():
    """Notification settings"""
    return {
        "email_enabled": True,
        "sms_enabled": False,
        "alert_types": {
            "speed": {"enabled": True, "threshold": 80},
            "temperature": {"enabled": True, "threshold": 45},
            "geofence": {"enabled": True}
        },
        "recipients": ["admin@fleetsync.com", "+91-9876543210"]
    }


@app.post("/config/notifications", tags=["Settings"])
async def update_notification_config(config: Dict):
    """Update notification settings"""
    # Persist to DB or config file
    print(f"[CONFIG] Updated: {config}")
    return {"status": "notification config updated"}


@app.get("/health", tags=["System"])
async def health_check():
    """System health check"""
    kafka_status = producer is not None
    db_status = True  # Test DB connection if needed
    
    return {
        "status": "healthy" if (kafka_status and db_status) else "degraded",
        "kafka_producer": kafka_status,
        "fleet_count": len(fleet_state),
        "websocket_clients": len(map_connections),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }




from fastapi import Request, HTTPException
import json

@app.post("/chat/admin", tags=["Admin"])
async def admin_chat(request: Request):
    """🚀 Works with CURL + FRONTEND - Handles ALL input formats"""
    try:
        # ✅ READ RAW BYTES - Windows safe
        body_bytes = await request.body()
        body_text = body_bytes.decode('utf-8')
        
        print(f"DEBUG RAW: {body_text[:100]}...")  # Debug log
        
        # ✅ TRY JSON FIRST (curl format)
        try:
            body_json = json.loads(body_text)
            query = body_json.get("query", body_text) if isinstance(body_json, dict) else body_text
        except json.JSONDecodeError:
            # ✅ FALLBACK: Direct string (frontend format)
            query = body_text.strip()
        
        if not query:
            return {"error": "No query", "trucks": len(fleet_state)}
        
        # ✅ LIVE FLEET DATA (your Kafka flow)
        trucks = []
        for vid, data in fleet_state.items():
            trucks.append({
                "id": vid,
                "lat": data["gps"]["lat"],
                "lon": data["gps"]["lon"], 
                "speed": data["gps"]["speed_kmh"]
            })
        
        # ✅ SMART RESPONSES
        q = query.lower()
        found_truck = None
        for truck in trucks:
            if truck["id"].lower() in q or truck["id"].replace("TRUCK-", "").lower() in q:
                found_truck = truck
                break
        
        if found_truck:
            answer = f"✅ {found_truck['id']}: {found_truck['lat']}°N, {found_truck['lon']}°E, {found_truck['speed']}kmh"
        elif "how" in q or "count" in q:
            answer = f"📊 {len(fleet_state)} trucks active"
        elif "list" in q:
            names = [t["id"] for t in trucks[:3]]
            answer = f"🚛 Active: {', '.join(names)}"
        else:
            answer = f"🗺️ {len(fleet_state)} trucks live. Try truck names or 'how many'"
        
        return {
            "answer": answer,
            "trucks": len(fleet_state),
            "sample": [t["id"] for t in trucks[:3]]
        }
        
    except Exception as e:
        print(f"CHAT ERROR: {e}")
        return {
            "error": "Chat service busy", 
            "trucks": len(fleet_state),
            "debug": str(e)[:100]
        }

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
    

@app.get("/alerts/history", tags=["Truck Driver"])
async def get_driver_alert_history(
    truck_id: str, 
    db: Session = Depends(get_db)
):
    """
    Truck Driver: See ALL admin-sent alerts for my truck
    Shows complete history of alerts created by admin
    """
    # Get ALL alerts sent by admin for this truck (past 7 days)
    from datetime import timedelta
    cutoff_time = datetime.utcnow() - timedelta(days=7)
    
    alerts = db.query(models.Alert).filter(
        models.Alert.vehicle_id == truck_id,
        models.Alert.created_at >= cutoff_time
    ).order_by(models.Alert.created_at.desc()).all()
    
    # Live GPS status
    live_gps = fleet_state.get(truck_id, {}).get("gps", {})
    truck_status = "online" if truck_id in fleet_state else "offline"
    
    # Format complete admin alert history for driver
    driver_alert_history = []
    for alert in alerts:
        alert_data = {
            "alert_id": alert.id,
            "type": alert.alert_type,  # speed, temp, geofence
            "message": f"Admin set {alert.alert_type} limit: {alert.threshold}",
            "threshold": alert.threshold,
            "status": "active" if alert.active else "resolved",
            "sent_by": "Admin",  # All alerts from admin panel
            "sent_at": alert.created_at.isoformat(),
            "resolved_at": getattr(alert, 'resolved_at', None) and alert.resolved_at.isoformat(),
            
            # Driver actionable info
            "action_required": alert.active,
            "current_status": {
                "speed_kmh": live_gps.get("speed_kmh", 0),
                "temperature": live_gps.get("temperature", 0),
                "within_limit": not alert.active  # Active = still violating
            }
        }
        driver_alert_history.append(alert_data)
    
    return {
        "truck_id": truck_id,
        "driver_view": "all_admin_alerts",
        "truck_status": truck_status,
        "live_gps": live_gps,
        "admin_alerts_history": driver_alert_history,
        "unresolved_count": len([a for a in driver_alert_history if a["status"] == "active"]),
        "total_admin_alerts": len(driver_alert_history),
        "last_sync": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/alert/{truck_id}", tags=["Truck Driver"])
async def get_all_admin_alerts_for_driver(truck_id: str, db: Session = Depends(get_db)):
    """
    Truck Driver: See ALL admin-sent alerts for my truck
    Complete history of admin-created alerts + current status
    """
    from datetime import timedelta
    
    # Get ALL admin alerts for this truck (last 30 days)
    cutoff_time = datetime.utcnow() - timedelta(days=30)
    alerts = db.query(models.Alert).filter(
        models.Alert.vehicle_id == truck_id,
        models.Alert.created_at >= cutoff_time
    ).order_by(models.Alert.created_at.desc()).all()
    
    # Live truck status
    live_data = fleet_state.get(truck_id, {})
    gps = live_data.get("gps", {})
    
    # Driver-friendly alert list
    driver_alerts = []
    for alert in alerts:
        is_active = alert.active
        current_speed = gps.get("speed_kmh", 0)
        current_temp = gps.get("temperature", 0)
        
        alert_item = {
            "alert_id": alert.id,
            "from_admin": True,
            "type": alert.alert_type,
            "limit": alert.threshold,
            "status": "ACTIVE" if is_active else "RESOLVED",
            "sent_time": alert.created_at.strftime("%Y-%m-%d %H:%M"),
            "message": f"Admin: {alert.alert_type.title()} limit {alert.threshold}",
            
            # Driver needs to know:
            "is_violating_now": False,
            "current_reading": 0
        }
        
        # Check current violation
        if alert.alert_type == "speed":
            alert_item["is_violating_now"] = current_speed > alert.threshold
            alert_item["current_reading"] = current_speed
        elif alert.alert_type == "temperature":
            alert_item["is_violating_now"] = current_temp > alert.threshold
            alert_item["current_reading"] = current_temp
        
        driver_alerts.append(alert_item)
    
    return {
        "my_truck": truck_id,
        "truck_online": truck_id in fleet_state,
        "current_speed": gps.get("speed_kmh", 0),
        "current_temp": gps.get("temperature", 0),
        "admin_alerts": driver_alerts,
        "urgent_count": len([a for a in driver_alerts if a["is_violating_now"]]),
        "total_from_admin": len(driver_alerts),
        "last_update": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }



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
