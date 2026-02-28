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

def build_processing_pipeline():
    """Build Pathway processing pipeline for GPS data"""
    try:
        print("[PIPELINE] Building processing pipeline...")
        
        kafka_host = os.getenv('KAFKA_BOOTSTRAP', 'kafka:9092')
        kafka_topic = os.getenv('KAFKA_TOPIC', 'fleetsync-gps-3')
        kafka_group = os.getenv('KAFKA_GROUP', 'pathway-fleetsync-gps')
        
        print(f"[CONFIG] Kafka Bootstrap: {kafka_host}")
        print(f"[CONFIG] Kafka Topic: {kafka_topic}")
        print(f"[CONFIG] Kafka Group: {kafka_group}")
        
        # Create input schema for Pathway
        class InputSchema(pw.Schema):
            message: str
        
        # Connect to Kafka
        kafka_stream = pw.io.kafka.read(
            host=kafka_host.split(':')[0],
            port=int(kafka_host.split(':')[1]),
            topic=kafka_topic,
            group_id=kafka_group,
            format="json"
        )
        
        # Parse messages using a proper Pathway operation
        def parse_row(row):
            try:
                msg_dict = row.as_dict() if hasattr(row, 'as_dict') else row
                msg_str = json.dumps(msg_dict) if isinstance(msg_dict, dict) else str(msg_dict)
                gps_msg = parse_message(msg_str)
                if gps_msg and validate_gps_data(gps_msg):
                    return {
                        'vehicle_id': gps_msg.vehicle_id,
                        'latitude': gps_msg.latitude,
                        'longitude': gps_msg.longitude,
                        'speed': gps_msg.speed,
                        'timestamp': gps_msg.timestamp,
                        'accuracy': gps_msg.accuracy
                    }
                return None
            except Exception as e:
                logger.error(f"Row parsing error: {e}")
                return None
        
        # Apply transformation - CORRECTED PATHWAY SYNTAX
        try:
            # Use select with a transformation function instead of map
            parsed_stream = kafka_stream.select(
                vehicle_id=pw.this.vehicle_id,
                latitude=pw.this.latitude,
                longitude=pw.this.longitude,
                speed=pw.this.speed,
                timestamp=pw.this.timestamp
            )
            
            # Filter out None/invalid entries
            filtered_stream = parsed_stream.filter(
                (pw.this.latitude.is_not_null()) & 
                (pw.this.longitude.is_not_null())
            )
            
            logger.info("[PIPELINE] Processing pipeline built successfully")
            return filtered_stream
            
        except Exception as e:
            logger.error(f"[ERROR] Pipeline construction error: {e}")
            raise
            
    except Exception as e:
        logger.error(f"[ERROR] Fatal error: {e}")
        raise

def main():
    """Main entry point"""
    try:
        print("=" * 80)
        print("FleetSync Pathway GPS Processing Engine")
        print("=" * 80)
        print(f"Start time: {datetime.now().isoformat()}")
        
        # Build pipeline
        result_stream = build_processing_pipeline()
        
        # Run the Pathway computation
        pw.run(result_stream)
        
    except Exception as e:
        logger.error(f"[ERROR] Fatal error in main: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()