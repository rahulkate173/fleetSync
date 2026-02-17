from sqlalchemy import Column, Integer, String, Float, Numeric, DateTime, Text
from sqlalchemy.sql import func
from database import Base


class Profile(Base):
    __tablename__ = "profile"
    emailid = Column(String(255), primary_key=True)
    phoneNo = Column(String(15))
    name = Column(String(100), nullable=False)
    company_name = Column(String(150))
    company_address = Column(String(255))


class Shipment(Base):
    __tablename__ = "shipment"
    shipment_id = Column(Integer, primary_key=True, autoincrement=True)
    reference_id = Column(String(50), unique=True, index=True)  # For user tracking
    origin_lat = Column(Numeric(9, 6), nullable=False)
    origin_long = Column(Numeric(9, 6), nullable=False)
    destination_lat = Column(Numeric(9, 6), nullable=False)
    destination_long = Column(Numeric(9, 6), nullable=False)
    truck_id = Column(Integer, nullable=False)
    load = Column(Numeric, nullable=False)
    status = Column(Integer, nullable=False)  # 0=departed, 1=middle, 2=loc, 3=delivered
    co2_emission = Column(String(10), nullable=False)
    avg_speed = Column(Float)
    distance_covered = Column(Float, nullable=False, default=0)
    departed_at = Column(DateTime(timezone=True))
    middle_at = Column(DateTime(timezone=True))
    loc_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))


class TruckProfile(Base):
    __tablename__ = "truck_profile"
    truck_id = Column(Integer, primary_key=True)
    email_id = Column(String(255), nullable=False)
    phone_no = Column(String(15))
    name = Column(String(100), nullable=False)
    company_name = Column(String(100))
    active_status = Column(Integer, nullable=False, default=1)


class VehicleLive(Base):
    """Live vehicle position (for real-time map). Aggregated/streamed data."""
    __tablename__ = "vehicle_live"
    vehicle_id = Column(String(50), primary_key=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    speed_kmh = Column(Float)
    temperature = Column(Float)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    shipment_ref_id = Column(String(50))


class Alert(Base):
    """Alerts sent from Admin to Truck Driver (overspeed, route deviation, temp)."""
    __tablename__ = "alert"
    id = Column(Integer, primary_key=True, autoincrement=True)
    truck_id = Column(Integer, nullable=False)
    type = Column(String(50))  # overspeed, route_deviation, temperature
    severity = Column(String(20))
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
