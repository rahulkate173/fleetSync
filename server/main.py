import os
import asyncio
import json
import csv
import hashlib
import secrets
import uuid
from typing import List, Dict, Optional
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from math import radians, sin, cos, sqrt, atan2

from aiokafka import AIOKafkaProducer
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fpdf import FPDF
from enum import Enum
from supabase import create_client
import models
import database

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC = "fleetsync-gps-3"
CSV_FILE = "bus_coordinates.csv"
REPORTS_DIR = "reports"
MAX_TRUCK_DISTANCE_KM = 5.0
HAVERSINE_EARTH_RADIUS_KM = 6371

# NAR Pune Coordinates
NAR_PUNE_DRIVERS = {
    "DRIVER-NAR001": {"name": "Ramesh", "truck_id": "TRUCK-NAR001", "lat": 18.5390, "lon": 73.8780},
    "DRIVER-NAR002": {"name": "Suresh", "truck_id": "TRUCK-NAR002", "lat": 18.5402, "lon": 73.8795},
    "DRIVER-NAR003": {"name": "Mahesh", "truck_id": "TRUCK-NAR003", "lat": 18.5385, "lon": 73.8772}
}

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class DriverLogin(BaseModel):
    username: str
    password: str

class DriverResponse(BaseModel):
    id: str
    username: str
    driver_name: str
    truck_id: str
    token: str

class ChatRequest(BaseModel):
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

class AlertRequest(BaseModel):
    driver_id: str
    message: str
    type: str = "info"  # info, warning, critical
    truck_id: Optional[str] = None

class AlertResponse(BaseModel):
    alert_id: str
    driver_id: str
    truck_id: Optional[str]
    message: str
    type: str
    timestamp: str
    read: bool = False

class OrderRequest(BaseModel):
    pickup_address: str
    delivery_address: str
    load_type: str  # dry, reefer, fragile
    payload_weight: float = 1000
    user_id: str = "USER001"

class SimulateDriver(BaseModel):
    driver_id: str
    active: bool = True

class AssignOrder(BaseModel):
    driver_id: str
    pickup: str
    delivery: str
    load_type: str = "dry"

class OrderStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PICKUP_IN_PROGRESS = "pickup_in_progress"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class DriverOrderStatus(str, Enum):
    UNREAD = "unread"
    SEEN = "seen"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    STARTED = "started"
    COMPLETED = "completed" 

class TicketOrderRequest(BaseModel):
    """Customer books a ticket/order"""
    pickup_address: str
    delivery_address: str
    load_type: str  # dry, reefer, fragile
    payload_weight: float = 1000
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    special_instructions: Optional[str] = None

class TicketOrderResponse(BaseModel):
    """Response when customer books"""
    order_id: str
    status: str
    message: str
    estimated_pickup_time: Optional[str] = None
    assigned_driver: Optional[str] = None
    assigned_truck: Optional[str] = None

class DriverOrderNotification(BaseModel):
    """Notification sent to driver"""
    order_id: str
    customer_name: str
    pickup_address: str
    delivery_address: str
    payload_weight: float
    load_type: str
    special_instructions: Optional[str] = None
    pickup_lat: float
    pickup_lon: float
    delivery_lat: float
    delivery_lon: float
    estimated_distance_km: float
    created_at: str

class DriverOrderResponse(BaseModel):
    """Driver's action on order"""
    order_id: str
    driver_id: str
    action: str  # "accept" or "reject"
    reason: Optional[str] = None

class AdminOrderNotification(BaseModel):
    """Notification for admin"""
    order_id: str
    customer_name: str
    customer_phone: str
    pickup_address: str
    delivery_address: str
    load_type: str
    payload_weight: float
    status: str
    assigned_truck_id: Optional[str] = None
    assigned_driver: Optional[str] = None
    created_at: str
    priority: str  # "normal", "urgent"



# ============================================================================
# GLOBAL STATE & MANAGERS
# ============================================================================

fleet_state: Dict[str, dict] = {}
ref_tracking: Dict[str, dict] = {}
map_connections: List[WebSocket] = []
alerts_db: Dict[str, AlertResponse] = {}
producer: Optional[AIOKafkaProducer] = None
tickets_db: Dict[str, dict] = {}
pending_driver_responses: Dict[str, dict] = {}
admin_connections: Dict[str, WebSocket] = {}
# Driver order status tracking
driver_order_status: Dict[str, Dict[str, str]] = {} 
class ConnectionManager:
    """Manages WebSocket connections for real-time notifications"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, driver_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[driver_id] = websocket
        print(f"[NOTIFY] Driver {driver_id} connected ({len(self.active_connections)} total)")

    def disconnect(self, driver_id: str):
        if driver_id in self.active_connections:
            del self.active_connections[driver_id]
            print(f"[NOTIFY] Driver {driver_id} disconnected")

    async def send_to_driver(self, driver_id: str, message: dict) -> bool:
        websocket = self.active_connections.get(driver_id)
        if websocket:
            try:
                await websocket.send_json(message)
                print(f"[NOTIFY] SENT to {driver_id}: {message.get('type', 'unknown')}")
                return True
            except Exception as e:
                print(f"[NOTIFY] Failed to send to {driver_id}: {e}")
                self.disconnect(driver_id)
                return False
        else:
            print(f"[NOTIFY] Driver {driver_id} OFFLINE - stored only")
            return False

    async def broadcast_all(self, message: dict):
        """Send message to all connected drivers"""
        disconnected = []
        for driver_id, websocket in list(self.active_connections.items()):
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(driver_id)
        
        for driver_id in disconnected:
            self.disconnect(driver_id)

notification_manager = ConnectionManager()

class AdminConnectionManager:
    """Manage admin WebSocket connections for notifications"""
    
    def __init__(self):
        self.active_admins: Dict[str, WebSocket] = {}

    async def connect(self, admin_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_admins[admin_id] = websocket
        print(f"[ADMIN-NOTIFY] Admin {admin_id} connected ({len(self.active_admins)} total)")

    def disconnect(self, admin_id: str):
        if admin_id in self.active_admins:
            del self.active_admins[admin_id]
            print(f"[ADMIN-NOTIFY] Admin {admin_id} disconnected")

    async def notify_admins(self, message: dict) -> int:
        """Send notification to all connected admins"""
        disconnected = []
        sent_count = 0
        
        for admin_id, websocket in list(self.active_admins.items()):
            try:
                await websocket.send_json(message)
                sent_count += 1
                print(f"[ADMIN-NOTIFY] Sent to admin {admin_id}")
            except Exception as e:
                print(f"[ADMIN-NOTIFY] Failed to send to {admin_id}: {e}")
                disconnected.append(admin_id)
        
        for admin_id in disconnected:
            self.disconnect(admin_id)
        
        return sent_count

admin_manager = AdminConnectionManager()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_db():
    """Database session dependency"""
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers"""
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return HAVERSINE_EARTH_RADIUS_KM * 2 * atan2(sqrt(a), sqrt(1-a))

async def _produce_to_kafka(
    vehicle_id: str, 
    lat: float, 
    lon: float, 
    speed_kmh: float, 
    temperature: Optional[float], 
    reference_id: Optional[str]
) -> None:
    """Send GPS data to Kafka topic"""
    global producer
    
    if producer is None:
        raise Exception("Kafka producer not initialized")
    
    payload = {
        "update_timestamp": datetime.now(timezone.utc).isoformat(),
        "vehicle_id": vehicle_id,
        "reference_id": reference_id,
        "gps": {
            "lat": lat, 
            "lon": lon, 
            "speed_kmh": speed_kmh, 
            "temperature": temperature, 
            "is_valid": not (lat == 0 and lon == 0)
        },
    }
    
    print(f"[PRODUCER] Sending vehicle {vehicle_id}: lat={lat}, lon={lon}")
    await producer.send_and_wait(KAFKA_TOPIC, value=payload, key=vehicle_id.encode("utf-8"))
    print(f"[PRODUCER] Sent vehicle {vehicle_id}")

async def geocode_address(address: str) -> tuple[float, float]:
    """Geocode address using Nominatim API"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            url = "https://nominatim.openstreetmap.org/search"
            params = {"q": f"{address}, Pune", "format": "json", "limit": 1}
            resp = await client.get(url, params=params, headers={"User-Agent": "FleetSync"})
            data = resp.json()
            if data:
                lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
                print(f"Geocoded: {lat:.4f}, {lon:.4f}")
                return lat, lon
    except Exception as e:
        print(f"Geocoding failed: {str(e)}")
    
    # Fallback coordinates (Pune center)
    return 18.5204, 73.8567

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between coordinates"""
    from math import radians, sin, cos, sqrt, atan2
    R = 6371
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

async def geocode_address(address: str) -> tuple[float, float]:
    """Geocode address to coordinates"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            url = "https://nominatim.openstreetmap.org/search"
            params = {"q": f"{address}, Pune", "format": "json", "limit": 1}
            resp = await client.get(url, params=params, headers={"User-Agent": "FleetSync"})
            data = resp.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        print(f"Geocoding failed: {str(e)}")
    
    return 18.5204, 73.8567

async def find_best_truck(
    pickup_lat: float,
    pickup_lon: float,
    load_type: str,
    supabase
) -> Optional[dict]:
    """Find nearest free truck of required type"""
    trucks = supabase.table("trucks").select("*").eq("status", "free").eq("truck_type", load_type).execute()
    
    best_truck = None
    min_distance = float('inf')
    
    print(f"[MATCH] Searching {len(trucks.data)} trucks for '{load_type}'")
    
    for truck in trucks.data:
        if truck.get("current_lat") and truck.get("current_lon"):
            distance = haversine(
                pickup_lat, pickup_lon, 
                truck["current_lat"], truck["current_lon"]
            )
            print(f"  {truck['truck_id']}: {distance:.1f}km")
            
            if distance <= 5.0 and distance < min_distance:
                min_distance = distance
                best_truck = truck
    
    return best_truck


def create_pdf_report(report_type: str) -> None:
    """Background task: Generate PDF report"""
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
    
    os.makedirs(REPORTS_DIR, exist_ok=True)
    pdf_path = f"{REPORTS_DIR}/{datetime.now().strftime('%Y%m%d-%H%M%S')}-{report_type}.pdf"
    pdf.output(pdf_path)

# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown"""
    global producer
    
    # STARTUP
    print("Starting fleetSync...")
    try:
        print("Creating SQLAlchemy tables...")
        models.Base.metadata.create_all(bind=database.engine)
        print("SQLAlchemy tables ready")
    except Exception as e:
        print(f"Some tables missing (OK): {e}")
    
    # Kafka producer startup
    try:
        producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all"
        )
        await producer.start()
        print(f"Kafka producer STARTED - {KAFKA_TOPIC}")
    except Exception as e:
        print(f"Kafka startup FAILED: {e}")
        producer = None
    
    yield  # App runs here
    
    # SHUTDOWN
    if producer:
        await producer.stop()
        print("Kafka producer STOPPED")

app = FastAPI(title="fleetSync API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://fleetsync-production-4ffc.up.railway.app",  # Add your production frontend
        "https://server-production-cd13.up.railway.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# ADMIN ROUTES - DASHBOARD
# ============================================================================

@app.get("/dashboard/map/data", tags=["Admin"])
async def get_map_data():
    """Get current fleet state for map"""
    return list(fleet_state.values())

@app.get("/dashboard/reports", tags=["Admin"])
async def get_reports():
    """Dashboard reports list"""
    reports = [
        {"id": "report-1", "name": "Weekly Summary", "date": "2026-02-17", "status": "ready"},
        {"id": "report-2", "name": "Fleet Analysis", "date": "2026-02-20", "status": "processing"},
        {"id": "report-3", "name": "CO2 Emissions", "date": "2026-02-24", "status": "ready"}
    ]
    return {"reports": reports}

@app.post("/dashboard/report", tags=["Admin"])
async def generate_report(background_tasks: BackgroundTasks, report_type: str = "summary"):
    """Generate PDF report asynchronously"""
    background_tasks.add_task(create_pdf_report, report_type)
    return {"status": "report generation started", "type": report_type}

@app.get("/dashboard/report/{report_id}", tags=["Admin"])
async def download_report(report_id: str):
    """Download generated PDF report"""
    pdf_path = f"{REPORTS_DIR}/{report_id}.pdf"
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, filename=f"{report_id}.pdf", media_type="application/pdf")
    return {"error": "Report not found"}

@app.get("/dashboard/summary", tags=["Admin"])
def dashboard_summary():
    """Fleet summary statistics"""
    active = len(fleet_state)
    delayed = sum(1 for v in fleet_state.values() if v.get("eta", {}).get("delay_minutes", 0) > 30)
    return {
        "co2_total_fleet": "5600 kg",
        "fleet_status": {"total": active, "delayed": delayed},
        "route_efficiency": "92%",
        "shipment_trends": [40, 55, 45, 70],
    }

@app.get("/dashboard/analytics", tags=["Admin"])
def dashboard_analytics():
    """Fleet analytics dashboard data"""
    total_trucks = len(fleet_state)
    avg_speed = sum(v["gps"]["speed_kmh"] for v in fleet_state.values()) / max(total_trucks, 1)
    
    # Mock emissions data
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

# ============================================================================
# ALERTS & NOTIFICATIONS
# ============================================================================

@app.post("/alerts/create", tags=["Admin"])
async def create_alert(db: Session = Depends(get_db), alert_data: Dict = {}):
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
        except Exception:
            pass
    
    return {"status": "alert created", "alert_id": alert.id}

@app.get("/alerts/active", tags=["Admin"])
def get_active_alerts(db: Session = Depends(get_db)):
    """Get active fleet alerts"""
    alerts = db.query(models.Alert).filter(models.Alert.active == True).all()
    
    alert_summary = []
    for alert in alerts:
        alert_data = {
            "id": alert.id,
            "vehicle_id": alert.vehicle_id,
            "type": alert.alert_type,
            "threshold": alert.threshold,
            "created_at": alert.created_at.isoformat()
        }
        
        if alert.vehicle_id in fleet_state:
            alert_data["current_gps"] = fleet_state[alert.vehicle_id]["gps"]
        
        alert_summary.append(alert_data)
    
    return {"active_alerts": alert_summary}

@app.post("/alerts/send", tags=["Notifications"])
async def send_driver_alert(alert: AlertRequest):
    """Admin sends targeted alert to specific driver"""
    alert_id = f"alert_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    
    new_alert = AlertResponse(
        alert_id=alert_id,
        driver_id=alert.driver_id,
        truck_id=alert.truck_id,
        message=alert.message,
        type=alert.type,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    alerts_db[alert_id] = new_alert
    
    sent = await notification_manager.send_to_driver(alert.driver_id, {
        "type": "new_alert",
        "alert": new_alert.model_dump()
    })
    
    return {
        "status": "sent",
        "alert_id": alert_id,
        "driver_online": sent,
        "total_stored": len(alerts_db)
    }

@app.get("/alerts/{driver_id}", tags=["Notifications"], response_model=List[AlertResponse])
async def get_driver_alerts(driver_id: str):
    """Driver fetches all their alerts"""
    driver_alerts = [
        alert for alert in alerts_db.values() 
        if alert.driver_id == driver_id
    ]
    return sorted(driver_alerts, key=lambda x: x.timestamp, reverse=True)

@app.put("/alerts/read/{alert_id}", tags=["Notifications"])
async def mark_alert_read(alert_id: str):
    """Driver marks specific alert as read"""
    if alert_id in alerts_db:
        alerts_db[alert_id].read = True
        return {"status": "marked_read", "alert_id": alert_id}
    return {"error": "Alert not found"}, 404

@app.post("/alerts/broadcast", tags=["Notifications"])
async def broadcast_fleet_alert(message: str, alert_type: str = "info"):
    """Admin emergency broadcast to ALL drivers"""
    broadcast_data = {
        "type": "broadcast",
        "message": message,
        "alert_type": alert_type,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await notification_manager.broadcast_all(broadcast_data)
    
    return {
        "status": "broadcast_sent",
        "connected_drivers": len(notification_manager.active_connections)
    }

@app.get("/notifications/stats", tags=["Admin"])
async def notification_stats():
    """Admin dashboard stats"""
    unread_count = sum(1 for alert in alerts_db.values() if not alert.read)
    connected_drivers = len(notification_manager.active_connections)
    
    return {
        "total_alerts": len(alerts_db),
        "unread_alerts": unread_count,
        "connected_drivers": connected_drivers,
        "online_percentage": f"{(connected_drivers/len(alerts_db)*100):.1f}%" if alerts_db else "0%"
    }

@app.websocket("/ws/notifications/{driver_id}")
async def driver_notifications(websocket: WebSocket, driver_id: str):
    """Driver WebSocket for real-time alerts"""
    await notification_manager.connect(driver_id, websocket)
    
    try:
        missed_alerts = [a for a in alerts_db.values() if a.driver_id == driver_id and not a.read]
        if missed_alerts:
            await websocket.send_json({
                "type": "missed_alerts", 
                "count": len(missed_alerts),
                "alerts": [alert.model_dump() for alert in missed_alerts]
            })
        
        while True:
            data = await websocket.receive_text()
            if data.startswith("ACK:"):
                alert_id = data[4:]
                if alert_id in alerts_db:
                    alerts_db[alert_id].read = True
                    print(f"[NOTIFY] Alert {alert_id} marked read by {driver_id}")
                    
    except WebSocketDisconnect:
        notification_manager.disconnect(driver_id)
    except Exception as e:
        print(f"[NOTIFY] WS Error {driver_id}: {e}")
        notification_manager.disconnect(driver_id)

# ============================================================================
# TRUCK DRIVER ROUTES
# ============================================================================

@app.post("/truck/gps", tags=["Truck Driver"])
async def truck_gps(data: TruckGpsInput):
    """Send GPS data to Kafka with graceful fallback"""
    print(f"[TRUCK/GPS] Received: vehicle {data.vehicle_id}")
    
    # Try Kafka producer first
    if producer is not None:
        try:
            print(f"[KAFKA] Attempting: vehicle {data.vehicle_id}")
            await _produce_to_kafka(
                data.vehicle_id, data.lat, data.lon, data.speed_kmh, data.temperature, data.reference_id
            )
            print(f"[KAFKA] SUCCESS: vehicle {data.vehicle_id}")
            return {"status": "sent to Kafka", "vehicle_id": data.vehicle_id}
        except Exception as e:
            print(f"[KAFKA] ERROR: {str(e)}")
    
    # FALLBACK: Store in fleet_state (like /ingest/pathway)
    print(f"[FALLBACK] Stored in-memory: {data.vehicle_id}")
    global fleet_state  # Your global state dict
    fleet_state[data.vehicle_id] = {
        "lat": data.lat,
        "lon": data.lon, 
        "speed_kmh": data.speed_kmh,
        "temperature": data.temperature,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    return {"status": "received", "vehicle_id": data.vehicle_id, "method": "in-memory"}

@app.get("/alerts/history", tags=["Truck Driver"])
async def get_driver_alert_history(truck_id: str, db: Session = Depends(get_db)):
    """Truck Driver: See all admin-sent alerts for their truck"""
    cutoff_time = datetime.utcnow() - timedelta(days=7)
    
    alerts = db.query(models.Alert).filter(
        models.Alert.vehicle_id == truck_id,
        models.Alert.created_at >= cutoff_time
    ).order_by(models.Alert.created_at.desc()).all()
    
    live_gps = fleet_state.get(truck_id, {}).get("gps", {})
    truck_status = "online" if truck_id in fleet_state else "offline"
    
    driver_alert_history = []
    for alert in alerts:
        alert_data = {
            "alert_id": alert.id,
            "type": alert.alert_type,
            "message": f"Admin set {alert.alert_type} limit: {alert.threshold}",
            "threshold": alert.threshold,
            "status": "active" if alert.active else "resolved",
            "sent_by": "Admin",
            "sent_at": alert.created_at.isoformat(),
            "resolved_at": getattr(alert, 'resolved_at', None) and alert.resolved_at.isoformat(),
            "action_required": alert.active,
            "current_status": {
                "speed_kmh": live_gps.get("speed_kmh", 0),
                "temperature": live_gps.get("temperature", 0),
                "within_limit": not alert.active
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
    """Truck Driver: See all admin-sent alerts with current status"""
    cutoff_time = datetime.utcnow() - timedelta(days=30)
    alerts = db.query(models.Alert).filter(
        models.Alert.vehicle_id == truck_id,
        models.Alert.created_at >= cutoff_time
    ).order_by(models.Alert.created_at.desc()).all()
    
    live_data = fleet_state.get(truck_id, {})
    gps = live_data.get("gps", {})
    
    driver_alerts = []
    for alert in alerts:
        current_speed = gps.get("speed_kmh", 0)
        current_temp = gps.get("temperature", 0)
        
        alert_item = {
            "alert_id": alert.id,
            "from_admin": True,
            "type": alert.alert_type,
            "limit": alert.threshold,
            "status": "ACTIVE" if alert.active else "RESOLVED",
            "sent_time": alert.created_at.strftime("%Y-%m-%d %H:%M"),
            "message": f"Admin: {alert.alert_type.title()} limit {alert.threshold}",
            "is_violating_now": False,
            "current_reading": 0
        }
        
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
class DriverLoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/drivers/login", tags=["Truck Driver"])
async def driver_login(request: DriverLoginRequest):
    """Driver login - using EMAIL not username"""
    try:
        from supabase import create_client
        supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY"))
        
        # Query by email instead of username
        drivers = supabase.table("drivers").select("*").eq("email", request.email).execute()
        
        if not drivers.data:
            return {"error": "Invalid credentials"}, 401
        
        driver = drivers.data[0]
        
        # Verify password
        if driver["password_hash"] != hash_password(request.password):
            return {"error": "Invalid credentials"}, 401
        
        # Generate token
        token = secrets.token_urlsafe(32)
        supabase.table("drivers").update({"token": token}).eq("id", driver["id"]).execute()
        
        return {
            "success": True,
            "message": "Login successful",
            "driver": {
                "id": driver["id"],
                "driver_id": driver.get("driver_id"),
                "email": driver["email"],
                "driver_name": driver["driver_name"],
                "truck_id": driver["truck_id"],
                "token": token
            }
        }
    except Exception as e:
        print(f"[LOGIN ERROR] {str(e)}")
        return {"error": "Login failed"}, 500

# ============================================================================
# SYSTEM & TRACKING ROUTES
# ============================================================================
from fastapi.responses import JSONResponse
from typing import Optional
from starlette.requests import Request
from fastapi import Depends, Request

async def get_request(request: Request):
    return request

@app.post("/ingest/pathway", response_model=None, tags=["System"])
async def ingest_pathway_endpoint(
    data: PathwayUpdate, 
    db: Session = Depends(get_db),
    request: Optional[Request] = Depends(get_request, use_cache=False)
) -> dict:
    """Pathway posts processed data here after Kafka consumption"""
    client_ip = request.client.host if request else "unknown"
    print(f"[INGEST] From: {client_ip} | Vehicle: {data.vehicle_id}")
    
    fleet_state[data.vehicle_id] = data.model_dump()
    
    if data.reference_id:
        ref_tracking[data.reference_id] = {
            "reference_id": data.reference_id,
            "vehicle_id": data.vehicle_id,
            "gps": data.gps.model_dump(),
        }
    
    return {"status": "Live & DB Updated"}


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

@app.post("/chat/admin", tags=["Admin"])
async def admin_chat(request: Request):
    """Admin chat interface"""
    try:
        body_bytes = await request.body()
        body_text = body_bytes.decode('utf-8')
        
        print(f"DEBUG RAW: {body_text[:100]}...")
        
        try:
            body_json = json.loads(body_text)
            query = body_json.get("query", body_text) if isinstance(body_json, dict) else body_text
        except json.JSONDecodeError:
            query = body_text.strip()
        
        if not query:
            return {"error": "No query", "trucks": len(fleet_state)}
        
        trucks = []
        for vid, data in fleet_state.items():
            trucks.append({
                "id": vid,
                "lat": data["gps"]["lat"],
                "lon": data["gps"]["lon"], 
                "speed": data["gps"]["speed_kmh"]
            })
        
        q = query.lower()
        found_truck = None
        for truck in trucks:
            if truck["id"].lower() in q or truck["id"].replace("TRUCK-", "").lower() in q:
                found_truck = truck
                break
        
        if found_truck:
            answer = f"{found_truck['id']}: {found_truck['lat']}°N, {found_truck['lon']}°E, {found_truck['speed']}kmh"
        elif "how" in q or "count" in q:
            answer = f"{len(fleet_state)} trucks active"
        elif "list" in q:
            names = [t["id"] for t in trucks[:3]]
            answer = f"Active: {', '.join(names)}"
        else:
            answer = f"{len(fleet_state)} trucks live. Try truck names or 'how many'"
        
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

@app.get("/health", tags=["System"])
async def health_check():
    """System health check"""
    return {
        "status": "healthy" if producer else "degraded",
        "kafka_producer": producer is not None,
        "fleet_count": len(fleet_state),
        "websocket_clients": len(map_connections),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/config/notifications", tags=["Settings"])
def get_notification_config():
    """Get notification settings"""
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
    print(f"[CONFIG] Updated: {config}")
    return {"status": "notification config updated"}

# ============================================================================
# WEBSOCKET ROUTES
# ============================================================================

@app.websocket("/dashboard/map/ws")
async def dashboard_map_ws(websocket: WebSocket):
    """Map WebSocket for real-time fleet updates"""
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

# ============================================================================
# ANALYTICS & GRAPHS
# ============================================================================

@app.get("/analysis/fleet-stats", tags=["Graph"])
async def get_fleet_stats():
    """Advanced analytics from fleet state"""
    if not fleet_state:
        return {
            "totalFleet": 0, "activeVehicles": 0, "avgSpeed": 0,
            "avgTemp": 0, "totalDistance": "0 km", "routeEfficiency": "0%",
            "totalCO2": "0 kg", "validGps": 0, "avgUptime": "0%"
        }
    
    total_vehicles = len(fleet_state)
    valid_gps_count = 0
    total_speed = 0
    total_temp = 0
    total_distance_estimate = 0
    idle_count = 0
    high_temp_count = 0
    
    for data in fleet_state.values():
        gps = data["gps"]
        
        if gps["is_valid"]:
            valid_gps_count += 1
            total_speed += gps["speed_kmh"]
            total_temp += gps.get("temperature", 0)
            total_distance_estimate += gps["speed_kmh"] * 0.1
        
        if gps["speed_kmh"] < 5:
            idle_count += 1
        if gps.get("temperature", 0) > 25:
            high_temp_count += 1
    
    active_vehicles = valid_gps_count
    avg_speed = total_speed / valid_gps_count if valid_gps_count else 0
    avg_temp = total_temp / valid_gps_count if valid_gps_count else 0
    
    return {
        "totalFleet": total_vehicles,
        "activeVehicles": active_vehicles,
        "validGpsCount": valid_gps_count,
        "idleVehicles": idle_count,
        "highTempVehicles": high_temp_count,
        "avgSpeed": round(avg_speed, 1),
        "avgTemp": round(avg_temp, 1),
        "totalDistance": f"{total_distance_estimate:.0f} km",
        "routeEfficiency": f"{min(98, 85 + (active_vehicles/total_vehicles*15)):.0f}%",
        "totalCO2": f"{total_vehicles * 5.6 * (avg_speed/60):.0f} kg",
        "uptime": f"{(valid_gps_count/total_vehicles)*100:.1f}%"
    }

@app.get("/analysis/speed-trends", tags=["Graph"])
async def get_speed_trends():
    """Get speed trends over last 24 hours"""
    hourly_speeds = defaultdict(list)
    
    for vehicle_id, data in fleet_state.items():
        timestamp_str = data.get("update_timestamp", "")
        if timestamp_str:
            try:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                hour_key = dt.strftime("%H:00")
                speed = data["gps"]["speed_kmh"]
                hourly_speeds[hour_key].append(speed)
            except Exception:
                hour_key = datetime.now().strftime("%H:00")
                speed = data["gps"]["speed_kmh"]
                hourly_speeds[hour_key].append(speed)
        else:
            hour_key = datetime.now().strftime("%H:00")
            speed = data["gps"]["speed_kmh"]
            hourly_speeds[hour_key].append(speed)
    
    now = datetime.now()
    labels = []
    avg_speeds = []
    
    for i in range(24):
        hour_ago = now - timedelta(hours=i)
        hour_key = hour_ago.strftime("%H:00")
        speeds = hourly_speeds.get(hour_key, [0])
        avg_speed = sum(speeds) / len(speeds)
        
        labels.append(hour_key)
        avg_speeds.append(round(avg_speed, 1))
    
    labels.reverse()
    avg_speeds.reverse()
    
    return {
        "labels": labels[-6:],
        "datasets": [{
            "label": f"Avg Fleet Speed ({len(fleet_state)} trucks)",
            "data": avg_speeds[-6:],
            "borderColor": "#10b981",
            "backgroundColor": "rgba(16, 185, 129, 0.1)",
            "fill": True,
            "tension": 0.4
        }]
    }

# ============================================================================
# ORDER MANAGEMENT
# ============================================================================

@app.post("/api/orders", tags=["Orders"])
async def create_order(request: OrderRequest):
    """Create and assign new order"""
    from supabase import create_client
    supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY"))
    
    if not supabase:
        return {"error": "Supabase not configured"}
    
    # Create user
    user_data = {
        "id": str(uuid.uuid4()),
        "name": request.user_id,
        "phone": f"+91-9{request.user_id[-8:]}"
    }
    supabase.table("users").upsert(user_data).execute()
    
    # Geocode addresses
    pickup_lat, pickup_lon = await geocode_address(request.pickup_address)
    delivery_lat, delivery_lon = await geocode_address(request.delivery_address)
    
    # Get user ID
    user = supabase.table("users").select("id").eq("name", request.user_id).execute().data[0]
    user_id = user["id"]
    
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    
    # Find best truck
    trucks = supabase.table("trucks").select("*").eq("status", "free").eq("truck_type", request.load_type).execute()
    
    best_truck = None
    min_distance = float('inf')
    
    print(f"[MATCH] Searching {len(trucks.data)} trucks for '{request.load_type}'")
    
    for truck in trucks.data:
        if truck.get("current_lat") and truck.get("current_lon"):
            distance = haversine(pickup_lat, pickup_lon, truck["current_lat"], truck["current_lon"])
            print(f"  {truck['truck_id']}: {distance:.1f}km")
            if distance <= MAX_TRUCK_DISTANCE_KM and distance < min_distance:
                min_distance = distance
                best_truck = truck
    
    # Create order
    order_data = {
        "order_id": order_id,
        "user_id": user_id,
        "pickup_address": request.pickup_address,
        "delivery_address": request.delivery_address,
        "pickup_lat": pickup_lat,
        "pickup_lon": pickup_lon,
        "delivery_lat": delivery_lat,
        "delivery_lon": delivery_lon,
        "load_type": request.load_type,
        "payload_weight": request.payload_weight,
        "status": "assigned" if best_truck else "pending",
        "assigned_truck_id": best_truck["id"] if best_truck else None,
        "assigned_driver_name": best_truck["driver_name"] if best_truck else None,
        "distance_km": round(min_distance, 1) if best_truck else None
    }
    
    supabase.table("orders").insert(order_data).execute()
    print(f"[SUCCESS] Created {order_id}")
    
    if best_truck:
        supabase.table("trucks").update({"status": "busy"}).eq("id", best_truck["id"]).execute()
        return {
            "success": True,
            "order_id": order_id,
            "status": "assigned",
            "truck_id": best_truck["truck_id"],
            "driver": best_truck.get("driver_name", "N/A"),
            "distance_km": round(min_distance, 1)
        }
    
    return {
        "success": True,
        "order_id": order_id,
        "status": "pending",
        "message": "No truck within 5km"
    }

@app.get("/api/orders", tags=["Orders"])
def get_orders(status: Optional[str] = None, limit: int = 50):
    """Get orders with optional filtering"""
    from supabase import create_client
    supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY"))
    
    query = supabase.table("orders").select("""
        order_id, status, pickup_address, delivery_address,
        pickup_lat, pickup_lon, delivery_lat, delivery_lon,
        load_type, payload_weight, assigned_truck_id,
        assigned_driver_name, distance_km, created_at
    """).order("created_at", desc=True).limit(limit)
    
    if status:
        query = query.eq("status", status)
    
    data = query.execute()
    
    return {
        "success": True,
        "orders": data.data,
        "stats": {
            "total": len(data.data),
            "assigned": len([o for o in data.data if o["status"] == "assigned"]),
            "pending": len([o for o in data.data if o["status"] == "pending"])
        }
    }

@app.post("/api/trucks/sample", tags=["Test"])
def add_sample_trucks():
    """Add sample trucks for testing"""
    from supabase import create_client
    supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY"))
    
    trucks = [
        {"truck_id": "TRUCK-001", "driver_name": "Ramesh", "status": "free", "truck_type": "dry", "current_lat": 18.520, "current_lon": 73.857},
        {"truck_id": "TRUCK-002", "driver_name": "Suresh", "status": "free", "truck_type": "reefer", "current_lat": 18.518, "current_lon": 73.859},
        {"truck_id": "TRUCK-003", "driver_name": "Mahesh", "status": "free", "truck_type": "dry", "current_lat": 18.522, "current_lon": 73.856},
    ]
    
    for truck in trucks:
        supabase.table("trucks").upsert(truck).execute()
    
    return {"added": len(trucks)}

# ============================================================================
# SIMULATION ROUTES
# ============================================================================

@app.post("/simulation/save-coordinate", tags=["Simulation"])
def save_simulation_coordinate(data: SimulationCoordinate):
    """Save coordinate to CSV"""
    file_exists = os.path.isfile(CSV_FILE)
    try:
        with open(CSV_FILE, mode="a", newline="") as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["vehicle_id", "latitude", "longitude", "timestamp"])
            writer.writerow([
                data.vehicle_id, data.latitude, data.longitude, data.timestamp
            ])
        return {"status": "coordinate saved"}
    except IOError as e:
        print(f"CSV write error: {e}")
        return {"error": "Failed to save coordinate"}, 500

@app.post("/simulate/drivers/activate", tags=["Simulate"])
async def activate_nar_drivers():
    """Activate NAR Pune drivers"""
    from supabase import create_client
    supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY"))
    
    activated = []
    
    for driver_id, info in NAR_PUNE_DRIVERS.items():
        truck_data = {
            "truck_id": info["truck_id"],
            "driver_name": info["name"],
            "status": "free",
            "truck_type": "dry",
            "current_lat": info["lat"],
            "current_lon": info["lon"]
        }
        supabase.table("trucks").upsert(truck_data).execute()
        
        if producer:
            await _produce_to_kafka(
                vehicle_id=info["truck_id"],
                lat=info["lat"],
                lon=info["lon"],
                speed_kmh=25.5,
                temperature=28.2,
                reference_id=None
            )
        
        activated.append({
            "driver_id": driver_id,
            "truck_id": info["truck_id"],
            "location": "NAR Pune",
            "lat": info["lat"],
            "lon": info["lon"],
            "status": "ACTIVE - GPS sent"
        })
        
        print(f"[SIMULATE] Activated {driver_id} at NAR Pune")
    
    return {"activated": activated, "total": 3}

@app.get("/simulate/drivers/status", tags=["Simulate"])
async def get_simulation_status():
    """Check simulation driver status"""
    status = []
    for driver_id, info in NAR_PUNE_DRIVERS.items():
        truck_id = info["truck_id"]
        is_live = truck_id in fleet_state
        status.append({
            "driver_id": driver_id,
            "truck_id": truck_id,
            "name": info["name"],
            "location": "NAR Pune",
            "online": is_live,
            "current_gps": fleet_state.get(truck_id, {}).get("gps", None),
            "supabase_status": "free"
        })
    return {"nar_pune_drivers": status}

@app.post("/simulate/gps/{driver_id}", tags=["Simulate"])
async def simulate_gps_movement(driver_id: str):
    """Simulate GPS movement for driver"""
    if driver_id not in NAR_PUNE_DRIVERS:
        return {"error": "Driver not found in NAR Pune"}
    
    if producer is None:
        return {"error": "Kafka producer not available"}, 503
    
    info = NAR_PUNE_DRIVERS[driver_id]
    truck_id = info["truck_id"]
    
    movements = [
        (info["lat"], info["lon"], 28.5, 29.1),
        (info["lat"]+0.001, info["lon"]+0.002, 35.2, 30.5),
        (info["lat"]+0.003, info["lon"]+0.005, 42.8, 31.2),
        (info["lat"]+0.002, info["lon"]+0.003, 15.3, 32.8),
    ]
    
    for lat, lon, speed, temp in movements:
        await _produce_to_kafka(truck_id, lat, lon, speed, temp, None)
        await asyncio.sleep(0.5)
    
    return {"status": "GPS simulation complete", "updates": 4, "final_pos": f"{lat:.4f},{lon:.4f}"}

@app.post("/simulate/order/{driver_id}", tags=["Simulate"])
async def assign_simulation_order(driver_id: str, order: AssignOrder):
    """Assign order to simulation driver"""
    from supabase import create_client
    supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY"))
    
    if driver_id not in NAR_PUNE_DRIVERS:
        return {"error": f"Driver {driver_id} not in NAR Pune simulation"}
    
    info = NAR_PUNE_DRIVERS[driver_id]
    truck_id = info["truck_id"]
    
    pickup_lat, pickup_lon = await geocode_address(f"{order.pickup}, Pune")
    delivery_lat, delivery_lon = await geocode_address(f"{order.delivery}, Pune")
    
    order_id = f"SIM-ORD-{uuid.uuid4().hex[:6].upper()}"
    user_id = "SIM-USER"
    
    user_data = {"id": str(uuid.uuid4()), "name": user_id}
    supabase.table("users").upsert(user_data).execute()
    user = supabase.table("users").select("id").eq("name", user_id).execute().data[0]
    
    order_data = {
        "order_id": order_id,
        "user_id": user["id"],
        "pickup_address": order.pickup,
        "delivery_address": order.delivery,
        "pickup_lat": pickup_lat,
        "pickup_lon": pickup_lon,
        "delivery_lat": delivery_lat,
        "delivery_lon": delivery_lon,
        "load_type": order.load_type,
        "payload_weight": 1500,
        "status": "assigned",
        "assigned_truck_id": truck_id,
        "assigned_driver_name": info["name"],
        "reference_id": f"REF-{order_id}"
    }
    
    supabase.table("orders").insert(order_data).execute()
    supabase.table("trucks").update({"status": "busy"}).eq("truck_id", truck_id).execute()
    
    await send_driver_alert(AlertRequest(
        driver_id=driver_id,
        message=f"NEW ORDER {order_id}: {order.pickup} → {order.delivery}",
        type="critical",
        truck_id=truck_id
    ))
    
    return {
        "success": True,
        "order_id": order_id,
        "driver": driver_id,
        "truck": truck_id,
        "pickup": f"{pickup_lat:.4f}, {pickup_lon:.4f}",
        "delivery": f"{delivery_lat:.4f}, {delivery_lon:.4f}",
        "notification_sent": True
    }

@app.post("/simulate/full-scenario", tags=["Simulate"])
async def run_complete_simulation():
    """Run complete simulation scenario"""
    await activate_nar_drivers()
    await asyncio.sleep(1)
    
    gps_tasks = []
    for driver_id in NAR_PUNE_DRIVERS.keys():
        gps_tasks.append(simulate_gps_movement(driver_id))
    await asyncio.gather(*gps_tasks, return_exceptions=True)
    await asyncio.sleep(2)
    
    order_result = await assign_simulation_order(
        driver_id="DRIVER-NAR001",
        order=AssignOrder(
            driver_id="DRIVER-NAR001",
            pickup="Phoenix Mall",
            delivery="Magarpatta City",
            load_type="dry"
        )
    )
    
    return {
        "status": "COMPLETE SIMULATION RUN",
        "steps": {
            "drivers_activated": 3,
            "gps_updates_sent": 12,
            "order_assigned": order_result["order_id"]
        },
        "check": {
            "map_data": "http://localhost:8000/dashboard/map/data",
            "driver_alerts": "http://localhost:8000/alerts/DRIVER-NAR001",
            "orders": "http://localhost:8000/api/orders?limit=5"
        }
    }

# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================


async def send_driver_order_notification(
    driver_id: str,
    truck_id: str,
    notification_data: dict,
    notification_manager
):
    """Background task: Send order notification to driver"""
    try:
        message = {
            "type": "new_order",
            "order_id": notification_data["order_id"],
            "customer_name": notification_data["customer_name"],
            "pickup_address": notification_data["pickup_address"],
            "delivery_address": notification_data["delivery_address"],
            "distance_km": notification_data["estimated_distance_km"],
            "load_type": notification_data["load_type"],
            "special_instructions": notification_data.get("special_instructions"),
            "created_at": notification_data["created_at"],
            "action_required": True
        }
        
        sent = await notification_manager.send_to_driver(driver_id, message)
        
        if sent:
            print(f"[DRIVER-NOTIFY] Driver {driver_id} notified for order {notification_data['order_id']}")
            if driver_id in driver_order_status:
                driver_order_status[driver_id][notification_data["order_id"]] = DriverOrderStatus.SEEN.value
        else:
            print(f"[DRIVER-NOTIFY] Driver {driver_id} OFFLINE - alert stored")
        
        return sent
    except Exception as e:
        print(f"[DRIVER-NOTIFY] Error notifying driver {driver_id}: {e}")
        return False

# ============================================================================
# ADD THESE TICKETING ROUTES AT THE END (before main block)
# ============================================================================

@app.post("/tickets/book", tags=["Ticketing"])
async def book_new_ticket(
    request: TicketOrderRequest,
    background_tasks: BackgroundTasks
) -> TicketOrderResponse:
    """
    Customer books a ticket/order
    
    Complete Workflow:
    1. Order created with customer details
    2. Auto-search for nearest free truck
    3. If truck found: Assign order
    4. Notify Admin (WebSocket)
    5. Notify Driver (WebSocket + Alert)
    6. Return confirmation to customer
    
    If no truck found:
    1. Order saved as PENDING
    2. Admin notified for manual assignment
    """
    
    try:
        # Step 1: Create order ID
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        # Step 2: Geocode addresses
        print(f"[TICKET] Processing order {order_id}")
        pickup_lat, pickup_lon = await geocode_address(request.pickup_address)
        delivery_lat, delivery_lon = await geocode_address(request.delivery_address)
        
        supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY"))
        
        # Step 3: Find best truck
        best_truck = await find_best_truck(pickup_lat, pickup_lon, request.load_type, supabase)
        
        if not best_truck:
            print(f"[TICKET] No truck found for order {order_id}")
            
            # Save as PENDING order in Supabase
            order_data = {
                "order_id": order_id,
                "customer_name": request.customer_name,
                "customer_phone": request.customer_phone,
                "customer_email": request.customer_email,
                "pickup_address": request.pickup_address,
                "delivery_address": request.delivery_address,
                "pickup_lat": pickup_lat,
                "pickup_lon": pickup_lon,
                "delivery_lat": delivery_lat,
                "delivery_lon": delivery_lon,
                "load_type": request.load_type,
                "payload_weight": request.payload_weight,
                "special_instructions": request.special_instructions,
                "status": OrderStatus.PENDING.value,
                "assigned_truck_id": None,
                "assigned_driver_id": None,
                "assigned_driver_name": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Save to Supabase
            supabase.table("orders").insert(order_data).execute()
            tickets_db[order_id] = order_data
            
            # Notify admin that order is pending
            await admin_manager.notify_admins({
                "type": "order_pending",
                "order_id": order_id,
                "customer_name": request.customer_name,
                "customer_phone": request.customer_phone,
                "pickup_address": request.pickup_address,
                "delivery_address": request.delivery_address,
                "load_type": request.load_type,
                "message": "No truck available - awaiting manual assignment",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            return {
                "success": True,
                "order_id": order_id,
                "status": OrderStatus.PENDING.value,
                "message": "Order created. No free truck available. Admin will assign manually.",
                "estimated_pickup_time": None,
                "assigned_driver": None,
                "assigned_truck": None
            }
        
        # Step 4: Truck found! Calculate distance
        distance = haversine(pickup_lat, pickup_lon, best_truck["current_lat"], best_truck["current_lon"])
        
        # Step 5: Save order to Supabase as ASSIGNED
        order_data = {
            "order_id": order_id,
            "customer_name": request.customer_name,
            "customer_phone": request.customer_phone,
            "customer_email": request.customer_email,
            "pickup_address": request.pickup_address,
            "delivery_address": request.delivery_address,
            "pickup_lat": pickup_lat,
            "pickup_lon": pickup_lon,
            "delivery_lat": delivery_lat,
            "delivery_lon": delivery_lon,
            "load_type": request.load_type,
            "payload_weight": request.payload_weight,
            "special_instructions": request.special_instructions,
            "status": OrderStatus.ASSIGNED.value,
            "assigned_truck_id": best_truck["id"],
            "assigned_truck_number": best_truck["truck_id"],
            "assigned_driver_id": best_truck.get("driver_id"),
            "assigned_driver_name": best_truck["driver_name"],
            "distance_km": round(distance, 1),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("orders").insert(order_data).execute()
        tickets_db[order_id] = order_data
        
        # Step 6: ADMIN NOTIFICATION - Order assigned to truck
        admin_notification = {
            "type": "order_assigned",
            "order_id": order_id,
            "customer_name": request.customer_name,
            "customer_phone": request.customer_phone,
            "pickup_address": request.pickup_address,
            "delivery_address": request.delivery_address,
            "load_type": request.load_type,
            "payload_weight": request.payload_weight,
            "assigned_truck": best_truck["truck_id"],
            "assigned_driver": best_truck["driver_name"],
            "distance_km": round(distance, 1),
            "message": f"Order {order_id} assigned to {best_truck['driver_name']} ({best_truck['truck_id']})",
            "priority": "normal",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        admins_notified = await admin_manager.notify_admins(admin_notification)
        print(f"[TICKET] Admin notified: {admins_notified} admins received notification")
        
        # Step 7: DRIVER NOTIFICATION - New order assigned
        driver_notification = DriverOrderNotification(
            order_id=order_id,
            customer_name=request.customer_name,
            pickup_address=request.pickup_address,
            delivery_address=request.delivery_address,
            payload_weight=request.payload_weight,
            load_type=request.load_type,
            special_instructions=request.special_instructions,
            pickup_lat=pickup_lat,
            pickup_lon=pickup_lon,
            delivery_lat=delivery_lat,
            delivery_lon=delivery_lon,
            estimated_distance_km=round(distance, 1),
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        driver_id = best_truck.get("driver_id", f"DRIVER-{best_truck['truck_id']}")
        
        # Store pending response
        pending_driver_responses[order_id] = {
            "driver_id": driver_id,
            "truck_id": best_truck["id"],
            "order_id": order_id,
            "assigned_at": datetime.now(timezone.utc).isoformat(),
            "status": DriverOrderStatus.UNREAD.value
        }
        
        # Initialize driver order status
        if driver_id not in driver_order_status:
            driver_order_status[driver_id] = {}
        driver_order_status[driver_id][order_id] = DriverOrderStatus.UNREAD.value
        
        # Send driver notification in background
        background_tasks.add_task(
            send_driver_order_notification,
            driver_id,
            best_truck["truck_id"],
            driver_notification.model_dump(),
            notification_manager
        )
        
        # Estimated pickup time (10 min from now)
        estimated_pickup = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        
        print(f"[TICKET] Order {order_id} assigned to driver {driver_id}")
        
        return {
            "success": True,
            "order_id": order_id,
            "status": OrderStatus.ASSIGNED.value,
            "message": f"Order assigned to {best_truck['driver_name']}",
            "estimated_pickup_time": estimated_pickup,
            "assigned_driver": best_truck["driver_name"],
            "assigned_truck": best_truck["truck_id"]
        }
        
    except Exception as e:
        print(f"[TICKET] Error booking ticket: {e}")
        return {
            "success": False,
            "error": str(e)
        }, 500

@app.post("/tickets/{order_id}/accept", tags=["Ticketing"])
async def driver_accept_order(order_id: str, driver_id: str):
    """
    Driver accepts the assigned order
    
    Updates:
    - Order status → ACCEPTED
    - Truck status → busy
    - Admin notification
    - Customer email notification
    """
    try:
        supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY"))
        
        if order_id not in tickets_db:
            return {"error": "Order not found"}, 404
        
        order = tickets_db[order_id]
        
        if order["status"] != OrderStatus.ASSIGNED.value:
            return {"error": "Order is not in ASSIGNED state"}, 400
        
        # Update order status in Supabase
        supabase.table("orders").update({
            "status": OrderStatus.ACCEPTED.value,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("order_id", order_id).execute()
        
        # Update local record
        order["status"] = OrderStatus.ACCEPTED.value
        order["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Update driver order status
        if driver_id in driver_order_status:
            driver_order_status[driver_id][order_id] = DriverOrderStatus.ACCEPTED.value
        
        # Update truck status to busy
        try:
            supabase.table("trucks").update({"status": "busy"}).eq("id", order["assigned_truck_id"]).execute()
        except Exception as e:
            print(f"[TICKET] Failed to update truck status: {e}")
        
        # Notify admin
        await admin_manager.notify_admins({
            "type": "driver_accepted_order",
            "order_id": order_id,
            "driver_id": driver_id,
            "driver_name": order["assigned_driver_name"],
            "truck_id": order["assigned_truck_number"],
            "message": f"Driver {order['assigned_driver_name']} accepted order {order_id}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Send alert to driver confirming acceptance
        await notification_manager.send_to_driver(driver_id, {
            "type": "order_accepted",
            "order_id": order_id,
            "message": f"Order {order_id} confirmed. Proceed to pickup location.",
            "pickup_address": order["pickup_address"],
            "pickup_lat": order["pickup_lat"],
            "pickup_lon": order["pickup_lon"]
        })
        
        print(f"[TICKET] Order {order_id} ACCEPTED by driver {driver_id}")
        
        return {
            "success": True,
            "order_id": order_id,
            "status": OrderStatus.ACCEPTED.value,
            "message": "Order accepted successfully",
            "driver_name": order["assigned_driver_name"],
            "truck_id": order["assigned_truck_number"]
        }
    except Exception as e:
        print(f"[TICKET] Error accepting order: {e}")
        return {"error": str(e)}, 500

@app.post("/tickets/{order_id}/reject", tags=["Ticketing"])
async def driver_reject_order(order_id: str, driver_id: str, reason: str):
    """
    Driver rejects the order - tries to reassign to another truck
    
    Process:
    1. Mark order as rejected by this driver
    2. Find alternative truck
    3. If found: Reassign and notify new driver
    4. If not: Return to PENDING for manual assignment
    """
    try:
        supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY"))
        
        if order_id not in tickets_db:
            return {"error": "Order not found"}, 404
        
        order = tickets_db[order_id]
        
        # Mark as rejected for this driver
        if driver_id in driver_order_status:
            driver_order_status[driver_id][order_id] = DriverOrderStatus.REJECTED.value
        
        print(f"[TICKET] Order {order_id} REJECTED by driver {driver_id}: {reason}")
        
        # Try to find another truck
        best_truck = await find_best_truck(
            order["pickup_lat"],
            order["pickup_lon"],
            order["load_type"],
            supabase
        )
        
        if best_truck and best_truck["id"] != order["assigned_truck_id"]:
            # Reassign to new truck
            distance = haversine(
                order["pickup_lat"], order["pickup_lon"],
                best_truck["current_lat"], best_truck["current_lon"]
            )
            
            old_driver = order["assigned_driver_name"]
            
            # Update order
            supabase.table("orders").update({
                "assigned_truck_id": best_truck["id"],
                "assigned_truck_number": best_truck["truck_id"],
                "assigned_driver_id": best_truck.get("driver_id"),
                "assigned_driver_name": best_truck["driver_name"],
                "distance_km": round(distance, 1),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("order_id", order_id).execute()
            
            # Update local record
            order["assigned_truck_id"] = best_truck["id"]
            order["assigned_truck_number"] = best_truck["truck_id"]
            order["assigned_driver_id"] = best_truck.get("driver_id")
            order["assigned_driver_name"] = best_truck["driver_name"]
            order["distance_km"] = round(distance, 1)
            order["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Notify new driver
            new_driver_id = best_truck.get("driver_id", f"DRIVER-{best_truck['truck_id']}")
            
            await send_driver_order_notification(
                new_driver_id,
                best_truck["truck_id"],
                {
                    "order_id": order_id,
                    "customer_name": order["customer_name"],
                    "pickup_address": order["pickup_address"],
                    "delivery_address": order["delivery_address"],
                    "payload_weight": order["payload_weight"],
                    "load_type": order["load_type"],
                    "special_instructions": order.get("special_instructions"),
                    "estimated_distance_km": round(distance, 1),
                    "created_at": order["created_at"]
                },
                notification_manager
            )
            
            # Notify admin
            await admin_manager.notify_admins({
                "type": "order_reassigned",
                "order_id": order_id,
                "previous_driver": old_driver,
                "previous_driver_id": driver_id,
                "reason": reason,
                "new_driver": best_truck["driver_name"],
                "new_driver_id": new_driver_id,
                "truck_id": best_truck["truck_id"],
                "message": f"Order reassigned from {old_driver} to {best_truck['driver_name']}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            return {
                "success": True,
                "order_id": order_id,
                "message": f"Order reassigned to {best_truck['driver_name']}",
                "new_driver": best_truck["driver_name"],
                "new_truck": best_truck["truck_id"]
            }
        else:
            # No other truck available - back to PENDING
            supabase.table("orders").update({
                "status": OrderStatus.PENDING.value,
                "assigned_truck_id": None,
                "assigned_driver_id": None,
                "assigned_driver_name": None,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("order_id", order_id).execute()
            
            order["status"] = OrderStatus.PENDING.value
            order["assigned_truck_id"] = None
            order["assigned_driver_id"] = None
            order["assigned_driver_name"] = None
            order["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            await admin_manager.notify_admins({
                "type": "order_unassigned",
                "order_id": order_id,
                "driver_id": driver_id,
                "driver_name": order.get("assigned_driver_name"),
                "reason": reason,
                "message": f"Order {order_id} back to PENDING - no alternative trucks",
                "priority": "high",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            return {
                "success": True,
                "order_id": order_id,
                "status": OrderStatus.PENDING.value,
                "message": "Order rejected and moved back to pending. Admin will reassign.",
                "new_assignment": None
            }
    except Exception as e:
        print(f"[TICKET] Error rejecting order: {e}")
        return {"error": str(e)}, 500

@app.get("/tickets/{order_id}/status", tags=["Ticketing"])
async def ticket_status(order_id: str):
    """Check ticket status - Customer/Admin endpoint"""
    try:
        if order_id not in tickets_db:
            # Try to fetch from Supabase
            supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY"))
            result = supabase.table("orders").select("*").eq("order_id", order_id).execute()
            
            if not result.data:
                return {"error": "Order not found"}, 404
            
            order = result.data[0]
        else:
            order = tickets_db[order_id]
        
        return {
            "order_id": order_id,
            "customer_name": order["customer_name"],
            "status": order["status"],
            "pickup_address": order["pickup_address"],
            "delivery_address": order["delivery_address"],
            "assigned_driver": order.get("assigned_driver_name"),
            "assigned_truck": order.get("assigned_truck_number"),
            "distance_km": order.get("distance_km"),
            "created_at": order["created_at"],
            "updated_at": order["updated_at"]
        }
    except Exception as e:
        print(f"[TICKET] Error getting status: {e}")
        return {"error": str(e)}, 500

@app.get("/tickets/driver/{driver_id}", tags=["Ticketing"])
async def driver_tickets(driver_id: str):
    """Get all orders assigned to driver"""
    try:
        driver_orders = [
            order for order in tickets_db.values()
            if order.get("assigned_driver_id") == driver_id
        ]
        
        return {
            "driver_id": driver_id,
            "total_orders": len(driver_orders),
            "orders": driver_orders
        }
    except Exception as e:
        print(f"[TICKET] Error getting driver orders: {e}")
        return {"error": str(e)}, 500

@app.get("/tickets/active", tags=["Admin"])
async def active_tickets():
    """Admin view all active tickets"""
    try:
        active_statuses = [
            OrderStatus.PENDING.value,
            OrderStatus.ASSIGNED.value,
            OrderStatus.ACCEPTED.value,
            OrderStatus.PICKUP_IN_PROGRESS.value
        ]
        
        active_orders = [
            order for order in tickets_db.values()
            if order["status"] in active_statuses
        ]
        
        return {
            "total_active": len(active_orders),
            "pending": len([o for o in active_orders if o["status"] == OrderStatus.PENDING.value]),
            "assigned": len([o for o in active_orders if o["status"] == OrderStatus.ASSIGNED.value]),
            "accepted": len([o for o in active_orders if o["status"] == OrderStatus.ACCEPTED.value]),
            "orders": active_orders
        }
    except Exception as e:
        print(f"[TICKET] Error getting active tickets: {e}")
        return {"error": str(e)}, 500

@app.websocket("/ws/admin/dashboard/{admin_id}")
async def admin_dashboard_ws(websocket: WebSocket, admin_id: str):
    """Admin real-time dashboard - receives all order updates"""
    await admin_manager.connect(admin_id, websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        admin_manager.disconnect(admin_id)
    except Exception as e:
        print(f"[ADMIN-WS] Error: {e}")
        admin_manager.disconnect(admin_id)

from pydantic import BaseModel, EmailStr

class DriverSignupRequest(BaseModel):
    username: str
    email: str
    password: str
    driver_name: str
    phone: str
    truck_id: str

@app.post("/api/drivers/signup", tags=["Truck Driver"])
async def driver_signup(request: DriverSignupRequest):
    """Driver registration endpoint"""
    try:
        from supabase import create_client
        supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY"))
        
        # Check if driver already exists
        existing = supabase.table("drivers").select("*").eq("username", request.username).execute()
        if existing.data:
            return {"error": "Username already exists"}, 400
        
        # Hash password
        password_hash = hash_password(request.password)
        
        # Create driver record
        driver_data = {
            "username": request.username,
            "email": request.email,
            "password_hash": password_hash,
            "driver_name": request.driver_name,
            "phone": request.phone,
            "truck_id": request.truck_id,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("drivers").insert(driver_data).execute()
        
        if result.data:
            return {
                "success": True,
                "message": "Driver registered successfully",
                "driver_id": result.data[0].get("id")
            }
        else:
            return {"error": "Registration failed"}, 500
            
    except Exception as e:
        print(f"[SIGNUP ERROR] {str(e)}")
        return {"error": "Registration error"}, 500



if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)