"""
Kafka Producer - Receives GPS/temp/coord from Truck Driver app (JSON format)
and publishes to Kafka topic for Pathway engine to consume.
"""
import os
import json
import asyncio
from datetime import datetime
from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv

load_dotenv()

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
TOPIC = os.getenv("KAFKA_TOPIC", "fleetsync-gps")


async def produce_gps(vehicle_id: str, lat: float, lon: float, speed_kmh: float = 0, temperature: float | None = None, reference_id: str | None = None):
    """Publish a single GPS event to Kafka (JSON format for Pathway)."""
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    try:
        payload = {
            "update_timestamp": datetime.utcnow().isoformat() + "Z",
            "vehicle_id": vehicle_id,
            "reference_id": reference_id,
            "gps": {
                "lat": lat,
                "lon": lon,
                "speed_kmh": speed_kmh,
                "temperature": temperature,
                "is_valid": not (lat == 0 and lon == 0),
            },
        }
        await producer.send_and_wait(TOPIC, value=payload, key=vehicle_id.encode("utf-8"))
        return True
    finally:
        await producer.stop()


async def main():
    """Simulate a truck driver sending GPS - for testing."""
    import sys
    vid = sys.argv[1] if len(sys.argv) > 1 else "TRUCK-001"
    await produce_gps(vid, 18.5167, 73.92, 45.0)
    print(f"Sent GPS for {vid}")


if __name__ == "__main__":
    asyncio.run(main())
