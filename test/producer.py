from kafka import KafkaProducer
import json
import time
import random
from datetime import datetime, timezone

# Connect to Kafka broker
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    acks='all',
    retries=3,
    linger_ms=5,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

topic = "fleetsync-gps"

# Constant vehicle
vehicle_id = "TRUCK-1110"
shipment_id = "SHIP-9001"
reference_id = "REF-ABC"

# Starting coordinates (Pune)
lat = 18.5204
lon = 73.8567

steps = 50

for i in range(steps):

    # Simulate movement (small incremental changes)
    lat += random.uniform(0.0001, 0.0005)
    lon += random.uniform(0.0001, 0.0005)

    # Dynamic timestamp (UTC ISO format)
    timestamp = datetime.now(timezone.utc).isoformat()

    data = {
        "update_timestamp": timestamp,
        "vehicle_id": vehicle_id,
        "shipment_id": shipment_id,
        "reference_id": reference_id,
        "gps": {
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "speed_kmh": random.randint(40, 80),
            "temperature": random.randint(4, 8),
            "is_valid": True
        }
    }

    producer.send(topic, value=data)
    print(f"Step {i+1} sent:", data)

    time.sleep(2)

producer.flush()
producer.close()

print("Simulation completed successfully.")
