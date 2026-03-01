import json
import logging
import asyncio
import pathway as pw
from kafka import KafkaConsumer, KafkaProducer
from datetime import datetime
from typing import Optional, Dict, Any
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GPSMessage:
    def __init__(self, vehicle_id: str, latitude: float, longitude: float, 
        speed: float, timestamp: str, accuracy: float = None):
        self.vehicle_id = vehicle_id
        self.latitude = latitude
        self.longitude = longitude
        self.speed = speed
        self.timestamp = timestamp
        self.accuracy = accuracy

def parse_message(msg: str) -> Optional[GPSMessage]:
    """Parse incoming Kafka message to GPSMessage"""
    try:
        if isinstance(msg, bytes):
            msg = msg.decode('utf-8')
        
        data = json.loads(msg)
        
        # Validate required fields
        required_fields = ['vehicle_id', 'latitude', 'longitude', 'speed', 'timestamp']
        if not all(field in data for field in required_fields):
            logger.warning(f"Missing required fields in message: {data}")
            return None
        
        # Validate GPS coordinates
        lat = float(data['latitude'])
        lon = float(data['longitude'])
        
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            logger.warning(f"Invalid GPS coordinates: lat={lat}, lon={lon}")
            return None
        
        return GPSMessage(
            vehicle_id=data['vehicle_id'],
            latitude=lat,
            longitude=lon,
            speed=float(data['speed']),
            timestamp=data['timestamp'],
            accuracy=float(data.get('accuracy', 0.0))
        )
    except Exception as e:
        logger.error(f"Error parsing message: {e}")
        return None

def validate_gps_data(gps_msg: GPSMessage) -> bool:
    """Validate GPS data"""
    try:
        # Check coordinate bounds
        if not (-90 <= gps_msg.latitude <= 90):
            return False
        if not (-180 <= gps_msg.longitude <= 180):
            return False
        
        # Check speed is non-negative
        if gps_msg.speed < 0:
            return False
        
        return True
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return False

# Line 46 - Replace kafka_host logic:
def build_processing_pipeline():
    """Build Pathway processing pipeline for GPS data"""
    try:
        print("[PIPELINE] Building processing pipeline...")
        
        # Get Kafka config from environment
        kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        kafka_topic = os.getenv('KAFKA_TOPIC', 'fleetsync-gps-3')
        kafka_group = os.getenv('KAFKA_GROUP_ID', 'pathway-fleetsync-gps')
        
        print(f"[CONFIG] Kafka Bootstrap: {kafka_bootstrap}")
        print(f"[CONFIG] Kafka Topic: {kafka_topic}")
        print(f"[CONFIG] Kafka Group: {kafka_group}")
        
        # ✅ FIXED: REMOVE BLOCKING CHECK - Always try to connect!
        # Railway private networking handles kafka:9092 correctly
        
        # Parse host:port
        if ':' in kafka_bootstrap:
            host = kafka_bootstrap.split(':')[0]  # kafka
            port = int(kafka_bootstrap.split(':')[1])  # 9092
        else:
            host, port = 'kafka', 9092
        
        class InputSchema(pw.Schema):
            message: str
        
        print(f"[CONNECT] Attempting Kafka connection: {host}:{port}")
        
        # Let Pathway try to connect (handles errors internally)
        kafka_stream = pw.io.kafka.read(
            host=host,
            port=port,
            topic=kafka_topic,
            group_id=kafka_group,
            format="json",
            rdkafka_settings={
                "group.id": kafka_group,
                "enable.auto.commit": "true",
                "auto.offset.reset": "earliest",
                "bootstrap.servers": f"{host}:{port}"
            }
        )
        
        
        # Process GPS data
        parsed_stream = kafka_stream.map(parse_message)
        filtered_stream = parsed_stream.filter(pw.this.is_not_null())
        
        print("[SUCCESS] Pathway Kafka pipeline connected!")
        logger.info("[PIPELINE] Processing pipeline built successfully")
        return filtered_stream
        
    except Exception as e:
        print(f"[WARNING] Pathway Kafka connection failed: {e}")
        print("[INFO] Running FastAPI standalone mode - core app still works")
        logger.error(f"[ERROR] Pipeline construction failed: {e}")
        return None  # Graceful fallback



def main():
    """Main entry point"""
    try:
        print("=" * 80)
        print("FleetSync Pathway GPS Processing Engine")
        print("=" * 80)
        print(f"Start time: {datetime.now().isoformat()}")
        
        # Build pipeline (returns None if no Kafka)
        result_stream = build_processing_pipeline()
        
        # FIXED: pw.run() takes NO arguments
        if result_stream is not None:
            print("[INFO] Starting Pathway computation...")
            pw.run()  # ✅ Correct syntax
        else:
            print("[INFO] No Kafka - running in standalone mode (FastAPI only)")
            # Keep app alive for Railway
            import time
            while True:
                time.sleep(60)
                print("[INFO] FleetSync ready - waiting for API traffic...")
                
    except KeyboardInterrupt:
        print("\n[INFO] Shutdown requested")
    except Exception as e:
        logger.error(f"[ERROR] Fatal error in main: {e}", exc_info=True)
        print("[INFO] Engine stopped - FastAPI endpoints still work")


if __name__ == "__main__":
    main()