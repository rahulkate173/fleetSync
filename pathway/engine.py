"""
FleetSync Pathway GPS Processing Engine
- Consumes GPS from Kafka using Pathway framework
- Real-time validation & filtering
- POSTs processed data to FastAPI server
- Production-ready with error handling
"""

import os
import sys
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Configure stdout for real-time logging
sys.stdout.reconfigure(line_buffering=True)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Pathway imports
import pathway as pw

# HTTP client
import httpx
import asyncio

# ============================================================================
# CONFIGURATION
# ============================================================================

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
SERVER_URL = os.getenv("FLEETSYNC_SERVER_URL", "http://localhost:8000")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "fleetsync-gps-3")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "pathway-fleetsync-gps")

# Processing config
GPS_VALIDATION_ENABLED = os.getenv("GPS_VALIDATION_ENABLED", "true").lower() == "true"
TEMPERATURE_EXCURSION_MAX = float(os.getenv("TEMPERATURE_EXCURSION_MAX", "50"))
TEMPERATURE_EXCURSION_MIN = float(os.getenv("TEMPERATURE_EXCURSION_MIN", "-20"))
SPEED_MAX_KMH = float(os.getenv("SPEED_MAX_KMH", "150"))
POST_TIMEOUT = float(os.getenv("POST_TIMEOUT", "5.0"))
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))

# Validate configuration
if not SERVER_URL or SERVER_URL == "":
    print("[ERROR] FLEETSYNC_SERVER_URL is not set!")
    SERVER_URL = "http://server:8000"
    print(f"[WARNING] Using default: {SERVER_URL}")

print(f"[CONFIG] Kafka Bootstrap: {KAFKA_BOOTSTRAP}")
print(f"[CONFIG] Kafka Topic: {KAFKA_TOPIC}")
print(f"[CONFIG] Kafka Group: {KAFKA_GROUP_ID}")
print(f"[CONFIG] Server URL: {SERVER_URL}")
print(f"[CONFIG] GPS Validation: {GPS_VALIDATION_ENABLED}")

# ============================================================================
# PATHWAY SCHEMAS
# ============================================================================

class RawGPSData(pw.Schema):
    """Raw GPS data from Kafka"""
    vehicle_id: str
    update_timestamp: str
    reference_id: Optional[str]
    shipment_id: Optional[str]
    gps_lat: float
    gps_lon: float
    gps_speed_kmh: float
    gps_temperature: Optional[float]
    gps_is_valid: bool


class ProcessedGPSData(pw.Schema):
    """Processed and validated GPS data"""
    vehicle_id: str
    update_timestamp: str
    reference_id: Optional[str]
    shipment_id: Optional[str]
    gps_lat: float
    gps_lon: float
    gps_speed_kmh: float
    gps_temperature: Optional[float]
    gps_is_valid: bool
    validation_passed: bool
    processed_at: str


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def is_valid_gps_coordinates(lat: float, lon: float) -> bool:
    """Validate GPS coordinates"""
    try:
        if lat == 0.0 and lon == 0.0:
            return False
        if lat < -90 or lat > 90:
            return False
        if lon < -180 or lon > 180:
            return False
        return True
    except (TypeError, ValueError):
        return False


def is_valid_temperature(temp: Optional[float]) -> bool:
    """Validate temperature reading"""
    if temp is None:
        return True
    try:
        if temp > TEMPERATURE_EXCURSION_MAX or temp < TEMPERATURE_EXCURSION_MIN:
            return False
        return True
    except (TypeError, ValueError):
        return False


def is_valid_speed(speed: float) -> bool:
    """Validate speed reading"""
    try:
        if speed < 0 or speed > SPEED_MAX_KMH:
            return False
        return True
    except (TypeError, ValueError):
        return False


def validate_gps_record(
    lat: float,
    lon: float,
    speed: float,
    temp: Optional[float]
) -> bool:
    """Complete GPS record validation"""
    if not GPS_VALIDATION_ENABLED:
        return True
    
    return (
        is_valid_gps_coordinates(lat, lon) and
        is_valid_temperature(temp) and
        is_valid_speed(speed)
    )


def parse_kafka_json(data: bytes) -> Optional[Dict[str, Any]]:
    """
    Parse Kafka message (bytes) to JSON
    Pathway will pass the raw byte message
    """
    try:
        if isinstance(data, bytes):
            return json.loads(data.decode("utf-8"))
        elif isinstance(data, str):
            return json.loads(data)
        else:
            return data
    except json.JSONDecodeError as e:
        print(f"[PARSE] JSON error: {e}")
        return None
    except Exception as e:
        print(f"[PARSE] Error: {e}")
        return None


def flatten_gps_data(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Flatten nested Kafka JSON to Pathway schema
    """
    try:
        if not isinstance(data, dict):
            print(f"[FLATTEN] Invalid data type: {type(data)}")
            return None
            
        gps = data.get("gps", {})
        
        return {
            "vehicle_id": data.get("vehicle_id", "unknown"),
            "update_timestamp": data.get(
                "update_timestamp",
                datetime.now(timezone.utc).isoformat()
            ),
            "reference_id": data.get("reference_id"),
            "shipment_id": data.get("shipment_id"),
            "gps_lat": float(gps.get("lat", 0)),
            "gps_lon": float(gps.get("lon", 0)),
            "gps_speed_kmh": float(gps.get("speed_kmh", 0)),
            "gps_temperature": (
                float(gps.get("temperature"))
                if gps.get("temperature") is not None
                else None
            ),
            "gps_is_valid": bool(gps.get("is_valid", False)),
        }
    except Exception as e:
        print(f"[FLATTEN] Error: {e}")
        return None


# ============================================================================
# HTTP POST WITH RETRY
# ============================================================================

async def post_to_fastapi_with_retry(row_dict: Dict[str, Any], attempt: int = 0) -> bool:
    """
    POST processed GPS to FastAPI /ingest/pathway with retry logic
    """
    try:
        payload = {
            "update_timestamp": row_dict["update_timestamp"],
            "vehicle_id": row_dict["vehicle_id"],
            "reference_id": row_dict["reference_id"],
            "shipment_id": row_dict["shipment_id"],
            "gps": {
                "lat": row_dict["gps_lat"],
                "lon": row_dict["gps_lon"],
                "speed_kmh": row_dict["gps_speed_kmh"],
                "temperature": row_dict["gps_temperature"],
                "is_valid": row_dict["gps_is_valid"],
            },
        }
        
        async with httpx.AsyncClient(timeout=POST_TIMEOUT) as client:
            response = await client.post(
                f"{SERVER_URL.rstrip('/')}/ingest/pathway",
                json=payload,
            )
            
            if response.status_code == 200:
                print(
                    f"[POST] ✓ 200 - {row_dict['vehicle_id']} "
                    f"({row_dict['gps_lat']:.4f}, {row_dict['gps_lon']:.4f})"
                )
                return True
            else:
                print(
                    f"[POST] ✗ {response.status_code} - {row_dict['vehicle_id']} "
                    f"(attempt {attempt + 1}/{RETRY_ATTEMPTS})"
                )
                
                # Retry on server errors
                if response.status_code >= 500 and attempt < RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(2 ** attempt)
                    return await post_to_fastapi_with_retry(row_dict, attempt + 1)
                
                return False
    
    except httpx.TimeoutException:
        print(f"[POST] ⏱ TIMEOUT - {row_dict['vehicle_id']} (attempt {attempt + 1}/{RETRY_ATTEMPTS})")
        if attempt < RETRY_ATTEMPTS - 1:
            await asyncio.sleep(2 ** attempt)
            return await post_to_fastapi_with_retry(row_dict, attempt + 1)
        return False
    
    except httpx.ConnectError as e:
        print(f"[POST] 🔌 CONNECTION ERROR - {row_dict['vehicle_id']}: {e} (attempt {attempt + 1}/{RETRY_ATTEMPTS})")
        if attempt < RETRY_ATTEMPTS - 1:
            await asyncio.sleep(2 ** attempt)
            return await post_to_fastapi_with_retry(row_dict, attempt + 1)
        return False
    
    except Exception as e:
        print(f"[POST] ❌ ERROR - {row_dict['vehicle_id']}: {e}")
        return False


# ============================================================================
# PATHWAY PROCESSING PIPELINE
# ============================================================================

def build_processing_pipeline():
    """
    Build Pathway streaming pipeline
    
    Flow:
    1. Read from Kafka (native Pathway format)
    2. Parse JSON
    3. Flatten schema
    4. Validate GPS
    5. POST to FastAPI
    6. Log results
    """
    
    print("[PIPELINE] Building processing pipeline...")
    
    # Step 1: Create Kafka connector (WITHOUT value_deserializer)
    try:
        print("[KAFKA] Connecting to Kafka...")
        
        kafka_stream = pw.io.kafka.read(
            rdkafka_settings={
                "bootstrap.servers": KAFKA_BOOTSTRAP,
                "group.id": KAFKA_GROUP_ID,
                "auto.offset.reset": "earliest",
                "session.timeout.ms": "30000",
                "api.version.request.timeout.ms": "10000",
            },
            topic=KAFKA_TOPIC,
            format="raw",
            mode="append",
        )
        
        print("[KAFKA] Connected successfully")
    except Exception as e:
        print(f"[KAFKA] Connection error: {e}")
        raise
    
    # Step 2: Parse JSON from Kafka messages
    def parse_message(row):
        """Parse Kafka message"""
        try:
            data = parse_kafka_json(row.data)
            return data
        except Exception as e:
            print(f"[PARSE] Error: {e}")
            return None
    
    parsed_stream = kafka_stream.map(parse_message).filter(lambda x: x is not None)
    
    # Step 3: Flatten to schema
    def apply_flatten(row):
        """Apply flattening transformation"""
        flattened = flatten_gps_data(row)
        return flattened
    
    flattened_stream = parsed_stream.map(apply_flatten).filter(lambda x: x is not None)
    
    # Step 4: Convert to RawGPSData schema
    def to_raw_gps(row):
        """Convert dict to RawGPSData"""
        try:
            return RawGPSData(
                vehicle_id=row["vehicle_id"],
                update_timestamp=row["update_timestamp"],
                reference_id=row["reference_id"],
                shipment_id=row["shipment_id"],
                gps_lat=row["gps_lat"],
                gps_lon=row["gps_lon"],
                gps_speed_kmh=row["gps_speed_kmh"],
                gps_temperature=row["gps_temperature"],
                gps_is_valid=row["gps_is_valid"],
            )
        except Exception as e:
            print(f"[SCHEMA] Error: {e}")
            return None
    
    raw_gps_stream = flattened_stream.map(to_raw_gps).filter(lambda x: x is not None)
    
    # Step 5: Validate GPS data
    def validate_gps(row):
        """Validate GPS record"""
        is_valid = validate_gps_record(
            row.gps_lat,
            row.gps_lon,
            row.gps_speed_kmh,
            row.gps_temperature
        )
        
        if is_valid:
            print(
                f"[VALIDATE] ✓ {row.vehicle_id} "
                f"({row.gps_lat:.4f}, {row.gps_lon:.4f})"
            )
        else:
            print(
                f"[VALIDATE] ✗ {row.vehicle_id} "
                f"({row.gps_lat:.4f}, {row.gps_lon:.4f})"
            )
        
        return ProcessedGPSData(
            vehicle_id=row.vehicle_id,
            update_timestamp=row.update_timestamp,
            reference_id=row.reference_id,
            shipment_id=row.shipment_id,
            gps_lat=row.gps_lat,
            gps_lon=row.gps_lon,
            gps_speed_kmh=row.gps_speed_kmh,
            gps_temperature=row.gps_temperature,
            gps_is_valid=row.gps_is_valid,
            validation_passed=is_valid,
            processed_at=datetime.now(timezone.utc).isoformat(),
        )
    
    processed_stream = raw_gps_stream.map(validate_gps)
    
    # Step 6: Filter only valid records before posting
    valid_stream = processed_stream.filter(lambda row: row.validation_passed)
    
    # Step 7: POST to FastAPI
    def post_wrapper(row):
        """Wrapper for async POST"""
        try:
            # Convert to dict for async function
            row_dict = {
                "vehicle_id": row.vehicle_id,
                "update_timestamp": row.update_timestamp,
                "reference_id": row.reference_id,
                "shipment_id": row.shipment_id,
                "gps_lat": row.gps_lat,
                "gps_lon": row.gps_lon,
                "gps_speed_kmh": row.gps_speed_kmh,
                "gps_temperature": row.gps_temperature,
                "gps_is_valid": row.gps_is_valid,
            }
            
            # Run async function in sync context
            result = asyncio.run(post_to_fastapi_with_retry(row_dict))
            return result
        except Exception as e:
            print(f"[WRAPPER] Error: {e}")
            return False
    
    # Apply POST and log results
    posted_stream = valid_stream.map(post_wrapper)
    
    print("[PIPELINE] Pipeline built successfully")
    return processed_stream


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """
    Main entry point - Run Pathway streaming pipeline
    """
    print("\n" + "=" * 80)
    print("FleetSync Pathway GPS Processing Engine")
    print("=" * 80)
    print(f"Start time: {datetime.now(timezone.utc).isoformat()}")
    print(f"Kafka Bootstrap: {KAFKA_BOOTSTRAP}")
    print(f"Kafka Topic: {KAFKA_TOPIC}")
    print(f"FastAPI Server: {SERVER_URL}")
    print(f"GPS Validation: {GPS_VALIDATION_ENABLED}")
    print("=" * 80 + "\n")
    
    try:
        # Build pipeline
        result_stream = build_processing_pipeline()
        
        # Run Pathway
        print("[PATHWAY] Starting event processing loop...\n")
        pw.run()
        
    except KeyboardInterrupt:
        print("\n\n[SHUTDOWN] Received interrupt signal")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()