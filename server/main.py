import os
import asyncio
from typing import List, Dict, Optional
from contextlib import asynccontextmanager
from datetime import datetime
from aiokafka import AIOKafkaProducer
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
import hashlib
import secrets
from typing import Optional
from datetime import datetime, timezone


class DriverLogin(BaseModel):
    username: str
    password: str

class DriverResponse(BaseModel):
    id: str
    username: str
    driver_name: str
    truck_id: str
    token: str  # Simple JWT-like token

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

# In-memory state
fleet_state: Dict[str, dict] = {}
ref_tracking: Dict[str, dict] = {}
map_connections: List[WebSocket] = {}

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

producer = None  # Global producer instance

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FIXED: Single lifespan handles DB + Kafka startup"""
    global producer
    
    # STARTUP
    print("Starting fleetSync...")
    try:
        print("Creating SQLAlchemy tables...")
        models.Base.metadata.create_all(bind=database.engine)
        print(" SQLAlchemy tables ready")
    except Exception as e:
        print(f"Some tables missing (OK): {e}")
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
        
app = FastAPI(title="fleetSync API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _produce_to_kafka(vehicle_id: str, lat: float, lon: float, speed_kmh: float, temperature: Optional[float], reference_id: Optional[str]):
    global producer
    
    payload = {
        "update_timestamp": datetime.now(timezone.utc).isoformat(),
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
    try:
        body_bytes = await request.body()
        body_text = body_bytes.decode('utf-8')
        
        print(f"DEBUG RAW: {body_text[:100]}...")  # Debug log
        
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
        print(f"[KAFKA] Attempting: vehicle {data.vehicle_id}") 
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
async def ingest_pathway(data: PathwayUpdate, db: Session = Depends(get_db),request: Request = None):
    """Pathway posts processed data here after Kafka consumption"""
    client_ip = request.client.host if request else "unknown"
    print(f"[INGEST] From: {client_ip} | Vehicle: {data.vehicle_id} | GPS: {data.gps.lat}, {data.gps.lon}")
    print(f"[INGEST] Vehicle: {data.vehicle_id} | GPS: {data.gps.lat}, {data.gps.lon}")
    fleet_state[data.vehicle_id] = data.model_dump()
    if data.reference_id:
        ref_tracking[data.reference_id] = {
            "reference_id": data.reference_id,
            "vehicle_id": data.vehicle_id,
            "gps": data.gps.model_dump(),
        }
    return {"status": "Live & DB Updated"}



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

@app.get("/analysis/fleet-stats", tags=["Graph"])
async def get_fleet_stats():
    """🚀 Advanced analytics from PROCESSED fleet_state data"""
    
    if not fleet_state:
        return {
            "totalFleet": 0, "activeVehicles": 0, "avgSpeed": 0,
            "avgTemp": 0, "totalDistance": "0 km", "routeEfficiency": "0%",
            "totalCO2": "0 kg", "validGps": 0, "avgUptime": "0%"
        }
    
    total_vehicles = len(fleet_state)
    
    # Use PROCESSED fleet_state fields
    valid_gps_count = 0
    total_speed = 0
    total_temp = 0
    total_distance_estimate = 0
    idle_count = 0
    high_temp_count = 0
    
    for data in fleet_state.values():
        gps = data["gps"]
        
        # GPS validity (already processed by Pathway)
        if gps["is_valid"]:
            valid_gps_count += 1
            total_speed += gps["speed_kmh"]
            total_temp += gps.get("temperature", 0)
            
            # Distance estimate (speed * time factor)
            total_distance_estimate += gps["speed_kmh"] * 0.1  # Hourly estimate
        
        # Business rules from processed data
        if gps["speed_kmh"] < 5:
            idle_count += 1
        if gps.get("temperature", 0) > 25:
            high_temp_count += 1
    
    # COMPREHENSIVE METRICS
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
        "totalCO2": f"{total_vehicles * 5.6 * (avg_speed/60):.0f} kg",  # Dynamic CO2
        "uptime": f"{(valid_gps_count/total_vehicles)*100:.1f}%"
    }
@app.get("/analysis/speed-trends", tags=["Graph"])
async def get_speed_trends():
    
    # Aggregate speed by hour from fleet_state
    hourly_speeds = defaultdict(list)
    
    for vehicle_id, data in fleet_state.items():
        # Extract timestamp (handle missing timestamps)
        timestamp_str = data.get("update_timestamp", "")
        if timestamp_str:
            try:
                # Parse ISO timestamp → Unix seconds
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                hour_key = dt.strftime("%H:00")
                speed = data["gps"]["speed_kmh"]
                hourly_speeds[hour_key].append(speed)
            except:
                # Fallback: use current time
                hour_key = datetime.now().strftime("%H:00")
                speed = data["gps"]["speed_kmh"]
                hourly_speeds[hour_key].append(speed)
        else:
            # No timestamp → current hour
            hour_key = datetime.now().strftime("%H:00")
            speed = data["gps"]["speed_kmh"]
            hourly_speeds[hour_key].append(speed)
    
    # Calculate average speeds for last 24hr
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
    
    # Reverse to show oldest → newest
    labels.reverse()
    avg_speeds.reverse()
    
    return {
        "labels": labels[-6:],  # Last 6 hours
        "datasets": [{
            "label": f"Avg Fleet Speed ({len(fleet_state)} trucks)",
            "data": avg_speeds[-6:],
            "borderColor": "#10b981",
            "backgroundColor": "rgba(16, 185, 129, 0.1)",
            "fill": True,
            "tension": 0.4  # Smooth curve
        }]
    }

# ===== DIRECT ASSIGNMENT TICKETING =====
from supabase import create_client
import httpx
import uuid
import os

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

class OrderRequest(BaseModel):
    pickup_address: str
    delivery_address: str
    load_type: str  # dry, reefer, fragile
    payload_weight: float = 1000
    user_id: str = "USER001"

def haversine(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

async def geocode_address(address: str) -> tuple[float, float]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            url = "https://nominatim.openstreetmap.org/search"
            params = {"q": f"{address}, Pune", "format": "json", "limit": 1}
            resp = await client.get(url, params=params, headers={"User-Agent": "FleetSync"})
            data = resp.json()
            if data: 
                lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
                print(f"Geocoded: {lat:.4f}, {lon:.4f}")  # Safe print
                return lat, lon
    except Exception as e:
        print(f"Geocoding failed: {str(e)}")  # Safe print
    return 18.5204, 73.8567


@app.post("/api/orders", tags=["Orders"])
async def create_order(request: OrderRequest):
    if not supabase:
        return {"error": "Supabase not configured"}
    
    # 1. CREATE USER if doesn't exist (FIXES foreign key!)
    user_data = {
        "id": str(uuid.uuid4()),
        "name": request.user_id,  # "USER001" → name
        "phone": f"+91-9{request.user_id[-8:]}"
    }
    supabase.table("users").upsert(user_data).execute()
    
    # 2. Geocode
    pickup_lat, pickup_lon = await geocode_address(request.pickup_address)
    delivery_lat, delivery_lon = await geocode_address(request.delivery_address)
    
    # 3. Find user_id (just created)
    user = supabase.table("users").select("id").eq("name", request.user_id).execute().data[0]
    user_id = user["id"]
    
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    
    # 4. Find best truck
    trucks = supabase.table("trucks").select("*").eq("status", "free").eq("truck_type", request.load_type).execute()
    
    best_truck = None
    min_distance = float('inf')
    
    print(f"[MATCH] Searching {len(trucks.data)} trucks for '{request.load_type}'")
    
    for truck in trucks.data:
        if truck.get("current_lat") and truck.get("current_lon"):
            distance = haversine(pickup_lat, pickup_lon, truck["current_lat"], truck["current_lon"])
            print(f"  {truck['truck_id']}: {distance:.1f}km")
            if distance <= 5.0 and distance < min_distance:
                min_distance = distance
                best_truck = truck
    
    # 5. Create order
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



# DASHBOARD
@app.get("/api/orders", tags=["Orders"])
def get_orders(status: str = None, limit: int = 50):
    # Specific fields including pickup/delivery locations
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
        "success": True,  # Added
        "orders": data.data,
        "stats": {
            "total": len(data.data),
            "assigned": len([o for o in data.data if o["status"] == "assigned"]),
            "pending": len([o for o in data.data if o["status"] == "pending"])
        }
    }


# SAMPLE TRUCKS
@app.post("/api/trucks/sample", tags=["Test"])
def add_sample_trucks():
    trucks = [
        {"truck_id": "TRUCK-001", "driver_name": "Ramesh", "status": "free", "truck_type": "dry", "current_lat": 18.520, "current_lon": 73.857},
        {"truck_id": "TRUCK-002", "driver_name": "Suresh", "status": "free", "truck_type": "reefer", "current_lat": 18.518, "current_lon": 73.859},
        {"truck_id": "TRUCK-003", "driver_name": "Mahesh", "status": "free", "truck_type": "dry", "current_lat": 18.522, "current_lon": 73.856},
    ]
    
    for truck in trucks:
        supabase.table("trucks").upsert(truck).execute()
    
    return {"added": len(trucks)}



# Helper to hash password (simple for demo)
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

#  TRUCK DRIVER LOGIN
@app.post("/api/drivers/login", tags=["Truck Driver"], response_model=dict)
async def driver_login(request: DriverLogin):
    # Query driver by username
    drivers = supabase.table("drivers").select("*").eq("username", request.username).execute()
    
    if not drivers.data:
        return {"error": "Invalid credentials"}, 401
    
    driver = drivers.data[0]
    
    # Verify password
    if driver["password_hash"] != hash_password(request.password):
        return {"error": "Invalid credentials"}, 401
    
    # Generate simple token
    token = secrets.token_urlsafe(32)
    
    # Update driver's token
    supabase.table("drivers").update({"token": token}).eq("id", driver["id"]).execute()
    
    return {
        "success": True,
        "message": "Login successful",
        "driver": {
            "id": driver["id"],
            "username": driver["username"],
            "driver_name": driver["driver_name"],
            "truck_id": driver["truck_id"],
            "token": token
        }
    }, 200


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
