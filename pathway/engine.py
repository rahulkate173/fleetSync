"""
Pathway-style Engine: Consumes GPS from Kafka, filters invalid (0,0) and anomalies,
POSTs processed data to FastAPI server. Uses Pathway Kafka connector when available.
"""
import os
import json
import asyncio
from datetime import datetime
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

KAFKA_BOOTSTRAP = "localhost:9092"        
SERVER_URL = "http://localhost:8000"      
TOPIC = "fleetsync-gps-3"  


def is_valid_gps(lat: float, lon: float, temp: float | None = None) -> bool:
    """Filter invalid: (0,0), out-of-range coords. Optional temp excursion check."""
    if lat == 0 and lon == 0:
        return False
    if abs(lat) > 90 or abs(lon) > 180:
        return False
    # Temp excursion: e.g. > 50C or < -20C
    if temp is not None and (temp > 50 or temp < -20):
        return False
    return True

def safe_json_deserializer(message: bytes):
    try:
        return json.loads(message.decode("utf-8"))
    except Exception:
        print("[Pathway] Skipping invalid JSON message")
        return None


async def consume_and_post():
    """Kafka consumer: Pathway-style filtering, POST to FastAPI."""

    from aiokafka import AIOKafkaConsumer
    import httpx

    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=safe_json_deserializer,
        group_id="pathway-fleetsync",
        auto_offset_reset="latest",
    )

    await consumer.start()
    print(f"Pathway engine: consuming {TOPIC} -> {SERVER_URL}")

    try:
        async for msg in consumer:
            data = msg.value
            if not data:
                continue

            gps = data.get("gps", {})
            lat = gps.get("lat", 0)
            lon = gps.get("lon", 0)
            temp = gps.get("temperature")

            if not is_valid_gps(lat, lon, temp):
                continue

            payload = {
                "update_timestamp": data.get(
                    "update_timestamp",
                    datetime.now(timezone.utc).isoformat()
                ),
                "vehicle_id": data.get("vehicle_id", "unknown"),
                "reference_id": data.get("reference_id"),
                "shipment_id": data.get("shipment_id"),
                "gps": {
                    "lat": lat,
                    "lon": lon,
                    "speed_kmh": gps.get("speed_kmh", 0),
                    "temperature": temp,
                    "is_valid": True,
                },
            }

            try:
                async with httpx.AsyncClient() as client:
                    r = await client.post(
                        f"{SERVER_URL.rstrip('/')}/ingest/pathway",
                        json=payload,
                        timeout=5.0,
                    )
                    print(
                        f"[Pathway] {r.status_code} "
                        f"vehicle={payload['vehicle_id']}"
                    )
            except Exception as e:
                print(f"[Pathway] POST failed: {e}")

    finally:
        await consumer.stop()

def main():
    asyncio.run(consume_and_post())


if __name__ == "__main__":
    main()
