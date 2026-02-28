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
from pathway.io.kafka import read as kafka_read

# HTTP client
import httpx
import asyncio

# ============================================================================
# CONFIGURATION
# ============================================================================

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
SERVER_URL = os.getenv("FLEETSYNC_SERVER_URL", "http://server:8000")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "fleetsync-gps-3")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "pathway-fleetsync-gps")

# Processing config
GPS_VALIDATION_ENABLED = os.getenv("GPS_VALIDATION_ENABLED", "true").lower() == "true"
TEMPERATURE_EXCURSION_MAX = float(os.getenv("TEMPERATURE_EXCURSION_MAX", "50"))
TEMPERATURE_EXCURSION_MIN = float(os.getenv("TEMPERATURE_EXCURSION_MIN", "-20"))
SPEED_MAX_KMH = float(os.getenv("SPEED_MAX_KMH", "150"))
POST_TIMEOUT = float(os.getenv("POST_TIMEOUT", "5.0"))
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))

print(f"[CONFIG] Kafka: {KAFKA_BOOTSTRAP}")
print(f"[CONFIG] Topic: {KAFKA_TOPIC}")
print(f"[CONFIG] Server: {SERVER_URL}")
print(f"[CONFIG] Group: {KAFKA_GROUP_ID}")
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
    """
    Validate GPS coordinates
    - Not (0, 0)
    - Within valid ranges: lat [-90, 90], lon [-180, 180]
    """
    try:
        # Reject (0, 0)
        if lat == 0.0 and lon == 0.0:
            return False
        
        # Validate ranges
        if lat < -90 or lat > 90:
            return False
        if lon < -180 or lon > 180:
            return False
        
        return True
    except (TypeError, ValueError):
        return False


def is_valid_temperature(temp: Optional[float]) -> bool:
    """
    Validate temperature reading
    - Optional (can be None)
    - If present: within reasonable range
    """
    if temp is None:
        return True  # Temperature is optional
    
    try:
        if temp > TEMPERATURE_EXCURSION_MAX or temp < TEMPERATURE_EXCURSION_MIN:
            return False
        return True
    except (TypeError, ValueError):
        return False


def is_valid_speed(speed: float) -> bool:
    """
    Validate speed reading
    - Non-negative
    - Below maximum
    """
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


def deserialize_kafka_value(data: bytes) -> Optional[Dict[str, Any]]:
    """
    Safely deserialize Kafka message
    Handles JSON errors gracefully
    """
    try:
        return json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as e:
        print(f"[DESERIALIZE] JSON error: {e}")
        return None
    except UnicodeDecodeError as e:
        print(f"[DESERIALIZE] Encoding error: {e}")
        return None
    except Exception as e:
        print(f"[DESERIALIZE] Unexpected error: {e}")
        return None


# ============================================================================
# KAFKA CONNECTOR
# ============================================================================

def create_kafka_connector():
    """
    Create Kafka connector with Pathway
    Returns stream of raw GPS data
    """
    print("[KAFKA] Connecting to Kafka...")
    
    try:
        # Read from Kafka
        kafka_stream = kafka_read(
            rdkafka_settings={
                "bootstrap.servers": KAFKA_BOOTSTRAP,
                "group.id": KAFKA_GROUP_ID,
                "auto.offset.reset": "earliest",
                "session.timeout.ms": "30000",
                "api.version.request.timeout.ms": "10000",
                "socket.keepalive.enable": "true",
            },
            topic=KAFKA_TOPIC,
            value_deserializer=deserialize_kafka_value,
            format="raw",
            mode="append",
        )
        
        print("[KAFKA] Connected successfully")
        return kafka_stream
    except Exception as e:
        print(f"[KAFKA] Connection error: {e}")
        raise


def flatten_gps_data(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Flatten nested Kafka JSON to Pathway schema
    
    Input:
    {
        "vehicle_id": "TRUCK-001",
        "update_timestamp": "2026-02-28T10:30:00Z",
        "gps": {
            "lat": 18.5204,
            "lon": 73.8567,
            "speed_kmh": 45.5,
            "temperature": 28.5,
            "is_valid": true
        },
        "reference_id": "REF-123"
    }
    
    Output: Flattened dict matching RawGPSData schema
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

async def post_to_fastapi_with_retry(row: Dict[str, Any], attempt: int = 0) -> bool:
    """
    POST processed GPS to FastAPI /ingest/pathway with retry logic
    """
    try:
        payload = {
            "update_timestamp": row["update_timestamp"],
            "vehicle_id": row["vehicle_id"],
            "reference_id": row["reference_id"],
            "shipment_id": row["shipment_id"],
            "gps": {
                "lat": row["gps_lat"],
                "lon": row["gps_lon"],
                "speed_kmh": row["gps_speed_kmh"],
                "temperature": row["gps_temperature"],
                "is_valid": row["gps_is_valid"],
            },
        }
        
        async with httpx.AsyncClient(timeout=POST_TIMEOUT) as client:
            response = await client.post(
                f"{SERVER_URL.rstrip('/')}/ingest/pathway",
                json=payload,
            )
            
            if response.status_code == 200:
                print(
                    f"[POST] ✓ 200 - {row['vehicle_id']} "
                    f"({row['gps_lat']:.4f}, {row['gps_lon']:.4f})"
                )
                return True
            else:
                print(
                    f"[POST] ✗ {response.status_code} - {row['vehicle_id']} "
                    f"(attempt {attempt + 1}/{RETRY_ATTEMPTS})"
                )
                
                # Retry on server errors
                if response.status_code >= 500 and attempt < RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    return await post_to_fastapi_with_retry(row, attempt + 1)
                
                return False
    
    except httpx.TimeoutException:
        print(f"[POST] ⏱ TIMEOUT - {row['vehicle_id']} (attempt {attempt + 1}/{RETRY_ATTEMPTS})")
        
        if attempt < RETRY_ATTEMPTS - 1:
            await asyncio.sleep(2 ** attempt)
            return await post_to_fastapi_with_retry(row, attempt + 1)
        return False
    
    except httpx.ConnectError:
        print(f"[POST] 🔌 CONNECTION ERROR - {row['vehicle_id']} (attempt {attempt + 1}/{RETRY_ATTEMPTS})")
        
        if attempt < RETRY_ATTEMPTS - 1:
            await asyncio.sleep(2 ** attempt)
            return await post_to_fastapi_with_retry(row, attempt + 1)
        return False
    
    except Exception as e:
        print(f"[POST] ❌ ERROR - {row['vehicle_id']}: {e}")
        return False


# ============================================================================
# PATHWAY PROCESSING PIPELINE
# ============================================================================

def build_processing_pipeline():
    """
    Build Pathway streaming pipeline
    
    Flow:
    1. Read from Kafka
    2. Parse JSON
    3. Flatten schema
    4. Validate GPS
    5. POST to FastAPI
    6. Log results
    """
    
    print("[PIPELINE] Building processing pipeline...")
    
    # Step 1: Create Kafka connector
    raw_stream = create_kafka_connector()
    
    # Step 2: Parse JSON from Kafka messages
    def parse_kafka_message(msg):
        """Extract value from Kafka message"""
        try:
            if isinstance(msg, dict):
                return msg
            return None
        except Exception as e:
            print(f"[PARSE] Error: {e}")
            return None
    
    parsed_stream = raw_stream.map(parse_kafka_message).filter(lambda x: x is not None)
    
    # Step 3: Flatten to schema
    def apply_flatten(row):
        """Apply flattening transformation"""
        return flatten_gps_data(row)
    
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
    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()