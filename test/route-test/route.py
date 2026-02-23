from fastapi import FastAPI, BackgroundTasks
from supabase import create_client, Client
from dotenv import load_dotenv
import os, asyncio, random
from datetime import datetime, timedelta
import requests
from typing import Dict

load_dotenv()

# Init
app = FastAPI(title="FleetSync - Swargate Logistics")
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
GEOAPIFY_KEY = os.getenv("GEOAPIFY_KEY")

# Swargate Hub (Main Depot) - [lat, lng]
SWARGATE_COORDS = [18.5056, 73.8667]  

# 10 Trucks
TRUCKS = {
    f"truck_{i:03d}": {"name": f"Tata Ace #{i}", "routes": []} 
    for i in range(1, 11)
}

# 25+ Pune + Maharashtra Destinations [lat, lng]
ROUTES = [
    # Pune Local (15)
    {"name": "Hadapsar", "coords": [18.4967, 73.9417]},
    {"name": "Magarpatta", "coords": [18.5158, 73.9272]},
    {"name": "Saswad", "coords": [18.3439, 73.9749]},
    {"name": "Pimpri", "coords": [18.6539, 73.8020]},
    {"name": "Chakan", "coords": [18.7629, 73.8541]},
    {"name": "Bhosari", "coords": [18.6175, 73.8981]},
    {"name": "Parvati", "coords": [18.4845, 73.8493]},
    {"name": "Dapodi", "coords": [18.5792, 73.8215]},
    {"name": "Wakad", "coords": [18.6146, 73.7539]},
    {"name": "Chinchwad", "coords": [18.6434, 73.6074]},
    {"name": "Vishrantwadi", "coords": [18.5825, 73.9000]},
    {"name": "Khopali", "coords": [18.6800, 73.6800]},
    {"name": "Kothrud", "coords": [18.5056, 73.8069]},
    {"name": "Baner", "coords": [18.5719, 73.7899]},
    {"name": "Aundh", "coords": [18.5659, 73.8220]},
    
    # Maharashtra Long-haul (12)
    {"name": "Kalyan", "coords": [19.2437, 73.1355]},
    {"name": "Solapur", "coords": [17.6716, 75.9102]},
    {"name": "Nashik", "coords": [20.0000, 73.7833]},
    {"name": "Nagpur", "coords": [21.1458, 79.0882]},
    {"name": "Aurangabad", "coords": [19.8762, 75.3433]},
    {"name": "Kolhapur", "coords": [16.6999, 74.2432]},
    {"name": "Sangli", "coords": [16.8567, 74.5881]},
    {"name": "Satara", "coords": [17.6850, 74.0171]},
    {"name": "Ahmednagar", "coords": [19.0951, 74.7513]},
    {"name": "Latur", "coords": [18.3983, 76.5734]},
    {"name": "Beed", "coords": [18.9894, 75.7565]},
    {"name": "Baramati", "coords": [18.2408, 74.5837]}
]

@app.on_event("startup")
async def init_routes():
    print(f"🚚 Initializing {len(TRUCKS)} trucks × {len(ROUTES)} destinations = {len(TRUCKS)*len(ROUTES)} routes")
    
    for truck_id, truck in TRUCKS.items():
        truck["routes"] = []
        for i, dest in enumerate(ROUTES):
            request_id = f"{truck_id}_{dest['name'].lower().replace(' ', '_')}"
            
            # ✅ V2.X SYNTAX - NO AWAIT on .execute()
            supabase.table("eta_requests").insert({
                "request_id": request_id,
                "vehicle_id": truck_id,
                "target_point": f"POINT({dest['coords'][1]} {dest['coords'][0]})"
            }).execute()
            
            # Geoapify call (unchanged)
            data = {
                "mode": "truck",
                "sources": [{"location": [SWARGATE_COORDS[1], SWARGATE_COORDS[0]]}],
                "targets": [{"location": [dest['coords'][1], dest['coords'][0]]}]
            }
            
            try:
                resp = requests.post(
                    "https://api.geoapify.com/v1/routematrix",
                    headers={"Content-Type": "application/json"},
                    params={"apiKey": GEOAPIFY_KEY},
                    json=data,
                    timeout=30
                ).json()
                
                duration = resp['sources_to_targets'][0][0]['duration']
                distance = resp['sources_to_targets'][0][0]['distance'] / 1000
                eta = datetime.now() + timedelta(seconds=duration)
                
                # ✅ V2.X SYNTAX - NO AWAIT
                supabase.table("eta_predictions").insert({
                    "request_id": request_id,
                    "predicted_eta": eta.isoformat(),
                    "confidence": 0.9,
                    "model_version": "geoapify_truck_v1",
                    "distance_km": distance
                }).execute()
                
                truck["routes"].append({"request_id": request_id, "duration": duration, "distance": distance})
                print(f"✅ {truck_id} → {dest['name']}: {duration/60:.1f}min")
                
            except Exception as e:
                print(f"❌ Geoapify: {e}")
                # ✅ Smart Pune-specific fallback
                base_distance = 15  # Swargate avg
                distance = base_distance + (i * 2)  # Longer destinations = more km
                duration = int(distance * 1.8 * 60)
                supabase.table("eta_predictions").insert({
                    "request_id": request_id,
                    "predicted_eta": (datetime.now() + timedelta(minutes=30)).isoformat(),
                    "confidence": 0.7,
                    "model_version": "fallback"
                }).execute()
                truck["routes"].append({"request_id": request_id, "duration": 1800})

@app.post("/simulate-gps/{truck_id}")
async def simulate_gps(truck_id: str, background_tasks: BackgroundTasks):
    """🚛 Start GPS simulation for specific truck"""
    if truck_id not in TRUCKS:
        return {"error": f"Truck {truck_id} not found. Available: {list(TRUCKS.keys())}"}
    
    background_tasks.add_task(run_gps_loop, truck_id)
    return {"status": f"GPS simulation started for {truck_id}", "total_routes": len(TRUCKS[truck_id]["routes"])}

async def run_gps_loop(truck_id: str):
    """📡 Realistic infinite GPS loop: Swargate → random destination → repeat"""
    print(f"🚛 {truck_id} GPS simulation started")
    
    while True:
        # Pick random destination for this truck
        route_idx = random.randint(0, len(TRUCKS[truck_id]["routes"])-1)
        dest = ROUTES[route_idx]
        request_id = TRUCKS[truck_id]["routes"][route_idx]["request_id"]
        route_duration = TRUCKS[truck_id]["routes"][route_idx]["duration"]
        
        # Simulate realistic steps (1 per 2-3% progress)
        steps = max(15, int(route_duration / 120))  # Min 15 steps
        for progress in range(0, 101, 100//steps):
            timestamp = datetime.now()
            
            # Linear interpolation Swargate → Destination
            lat = SWARGATE_COORDS[0] + (dest['coords'][0] - SWARGATE_COORDS[0]) * (progress/100)
            lng = SWARGATE_COORDS[1] + (dest['coords'][1] - SWARGATE_COORDS[1]) * (progress/100)
            
            speed = random.uniform(25, 65) if progress < 90 else random.uniform(0, 10)
            heading = random.uniform(0, 360)
            
            # 1. Raw GPS telemetry (time-series)
            supabase.table("vehicle_telemetry").insert({
                "vehicle_id": truck_id,
                "timestamp": timestamp.isoformat(),
                "location": f"POINT({lng} {lat})",
                "speed_kmh": speed,
                "heading_degrees": heading
            }).execute()
            # 2. Current vehicle state (live dashboard)
            supabase.table("vehicle_state").upsert({
                "vehicle_id": truck_id,
                "current_location": f"POINT({lng} {lat})",
                "speed_kmh": speed,
                "status": "en_route" if progress < 95 else "arrived",
                "last_update": timestamp.isoformat()
            }).execute()
            
            # 3. FINAL arrival (ground truth for ML training)
            if progress >= 100:
                # Add realistic delay (0-15min)
                actual_delay = random.uniform(0, 900)  # seconds
                arrival_time = timestamp + timedelta(seconds=actual_delay)
                
                await supabase.table("actual_arrivals").insert({
                    "request_id": request_id,
                    "actual_arrival_time": arrival_time.isoformat()
                }).execute()
                print(f"🎉 {truck_id} → {dest['name']} ARRIVED (+{actual_delay/60:.1f}min delay)")
                break
            
            # Realistic GPS update interval (30-90s)
            await asyncio.sleep(random.uniform(30, 90))
        
        # Truck break before next route (5-20min)
        await asyncio.sleep(random.uniform(300, 1200))

@app.get("/delay-stats")
async def get_delay_stats():
    """📊 La Poste-style delay analytics"""
    result = await supabase.rpc("""
        SELECT 
          ROUND(AVG(EXTRACT(EPOCH FROM (aa.actual_arrival_time - ep.predicted_eta))/60), 1) as avg_delay_minutes,
          COUNT(*) as total_deliveries,
          COUNT(DISTINCT ep.vehicle_id) as active_trucks,
          ROUND(AVG(ep.distance_km), 1) as avg_distance_km,
          ROUND(AVG(ep.confidence), 2) as avg_confidence,
          COUNT(*) FILTER (WHERE EXTRACT(EPOCH FROM (aa.actual_arrival_time - ep.predicted_eta)) > 0) as late_deliveries
        FROM eta_predictions ep
        FULL OUTER JOIN actual_arrivals aa ON ep.request_id = aa.request_id
        WHERE aa.actual_arrival_time IS NOT NULL
    """).execute()
    return result.data[0] if result.data else {
        "avg_delay_minutes": 0, 
        "total_deliveries": 0,
        "active_trucks": 0
    }

@app.get("/live-trucks")
async def live_trucks():
    """🗺️ Real-time dashboard - all 10 trucks"""
    result = await supabase.table("vehicle_state").select("*").execute()
    return {"live_trucks": result.data, "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    return {
        "FleetSync": "Swargate Logistics Hub",
        "trucks": len(TRUCKS),
        "destinations": len(ROUTES),
        "total_routes": len(TRUCKS) * len(ROUTES),
        "endpoints": ["/live-trucks", "/delay-stats", "/simulate-gps/{truck_id}"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
