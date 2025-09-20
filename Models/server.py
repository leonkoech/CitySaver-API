from pydantic import BaseModel
from typing import List, Optional

class SensorData(BaseModel):
    device_id: str
    timestamp: int
    distance_cm: float
    distance_inch: float
    temperature_c: float
    humidity_percent: float
    latitude: float
    longitude: float
    gps_valid: bool
    gps_raw: str
    gps_status: str

class SensorDataResponse(BaseModel):
    device_id: str
    timestamp: int
    distance_cm: float
    distance_inch: float
    temperature_c: float
    humidity_percent: float
    latitude: float
    longitude: float
    gps_valid: bool
    gps_raw: str
    gps_status: str
    received_at: str
