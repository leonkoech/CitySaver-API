from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from scalar_fastapi import get_scalar_api_reference
from typing import List
import json
import os
from datetime import datetime
import uvicorn
import logging
import sys

from Models.api import ApiResponse, ErrorResponse
from Models.server import SensorData, SensorDataResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


DEV_URL = "https://d12b95bc50a9.ngrok-free.app"
PROD_URL = "http://192.168.104.34:8000"

# Initialize FastAPI with comprehensive configuration
app = FastAPI(
    title="Flood Guard",
    description="""
## Real-time IoT Sensor Data Collection System

A comprehensive FastAPI-based system for collecting, storing, and analyzing data from ESP32-powered IoT sensors.

### **Supported Hardware**
- **HRS04 Ultrasonic Distance Sensor** - Measures distances up to 4 meters
- **DHT22 Temperature & Humidity Sensor** - High-precision environmental monitoring  
- **NEO-6M GPS Module** - Global positioning with NMEA sentence parsing

### **Key Features**
- **Real-time data ingestion** from multiple ESP32 devices
- **Persistent storage** with automatic JSON file backup
- **Statistical analysis** and data filtering capabilities
- **Live web dashboard** with auto-refresh functionality
- **RESTful API** with comprehensive documentation
- **Error handling** with graceful sensor failure recovery
- **CORS enabled** for cross-origin requests

### **Quick Start Guide**

1. **Send sensor data**: POST to `/data` endpoint with ESP32 readings
2. **View live dashboard**: Visit `/dashboard` for real-time monitoring
3. **Access raw data**: GET from `/data` for JSON data export
4. **Download backups**: Use `/data/file` for complete data export
5. **Monitor statistics**: Check `/stats` for analytical insights

### **Data Flow**
```
ESP32 Device → WiFi → FastAPI Server → JSON Storage → Live Dashboard
```

### **Security & Reliability**
- Input validation using Pydantic models
- Comprehensive error handling with proper HTTP status codes
- Automatic data backup every 10 records
- Graceful degradation when sensors fail
- CORS middleware for secure cross-origin access

---
**Built with FastAPI | Designed for ESP32 IoT Projects | Production Ready**
    """.strip(),
    version="2.1.0",
    contact={
        "name": "ESP32 Sensor System Support",
        "email": "leonkipkoech00@gmail.com",
        "url": "https://github.com/your-repo/esp32-sensor-api"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": f"{DEV_URL}",
            "description": "Development server"
        },
        {
            "url": f"{PROD_URL}", 
            "description": "Local network server"
        }
    ],
    # Disable default docs to use Scalar
    docs_url=None,
    redoc_url=None,
    openapi_tags=[
        {
            "name": "Data Collection",
            "description": "Endpoints for receiving and storing sensor data from ESP32 devices",
        },
        {
            "name": "Data Retrieval", 
            "description": "Endpoints for accessing and querying stored sensor data",
        },
        {
            "name": "Analytics",
            "description": "Statistical analysis and filtering operations on sensor data",
        },
        {
            "name": "File Operations",
            "description": "File download and direct storage access operations",
        },
        {
            "name": "Data Management",
            "description": "Operations for managing and clearing stored data",
        },
        {
            "name": "Dashboard",
            "description": "Web-based dashboard and visualization interfaces",
        }
    ]
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
sensor_data: List[SensorDataResponse] = []
DATA_FILE = "sensor_data.json"
MAX_RECORDS = 1000

# Utility functions
def load_existing_data():
    """Load existing sensor data from JSON file"""
    global sensor_data
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                sensor_data = [SensorDataResponse(**item) for item in data]
                logger.info(f"✅ Loaded {len(sensor_data)} existing records")
        else:
            logger.info("📝 Starting with empty database")
    except Exception as e:
        logger.error(f"⚠️ Error loading data: {e}")
        sensor_data = []

def save_data():
    """Save current sensor data to JSON file"""
    try:
        data_dict = [item.dict() for item in sensor_data]
        with open(DATA_FILE, 'w') as f:
            json.dump(data_dict, f, indent=2)
        logger.info(f"💾 Data saved to {DATA_FILE}")
    except Exception as e:
        logger.error(f"❌ Error saving data: {e}")

# Event handlers
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    load_existing_data()
    logger.info("ESP32 Sensor FastAPI Server started!")
    logger.info(" Available endpoints:")
    logger.info("   POST /data - Receive sensor data")
    logger.info("   GET /data - Get all data") 
    logger.info("   GET /data/latest - Get latest reading")
    logger.info("   GET /dashboard - View live dashboard")
    logger.info("   GET /docs - Scalar API documentation")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on application shutdown"""
    save_data()
    logger.info("Data saved on shutdown")

# Root redirect
@app.get("/", include_in_schema=False)
async def read_root():
    """Redirect root to documentation"""
    return RedirectResponse(url="/docs", status_code=307)

# Scalar documentation endpoint
@app.get("/docs", include_in_schema=False)
async def scalar_docs():
    """Modern API documentation using Scalar"""
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Interactive Documentation",
    )

# API Endpoints - Data Collection
@app.post("/data", 
          tags=["Data Collection"],
          response_model=ApiResponse,
          summary="Receive ESP32 sensor data",
          description="""
          **Receive and store sensor data from ESP32 devices**
          
          This endpoint accepts real-time sensor readings from ESP32 devices including:
          - Distance measurements from ultrasonic sensors
          - Temperature and humidity from DHT22 sensors  
          - GPS coordinates from NEO-6M modules
          
          The system automatically:
          - Validates input data format
          - Adds server-side timestamps
          - Stores data in memory and persistent storage
          - Maintains a rolling buffer of recent readings
          """)
async def receive_sensor_data(data: SensorData):
    try:
        # Validate device_id is not empty
        device_id = data.device_id.strip() if data.device_id else ""
        if not device_id or device_id.lower() in ['null', 'none', 'undefined']:
            raise HTTPException(
                status_code=400, 
                detail="Device ID is required and cannot be empty"
            )
        
        # Add received timestamp
        response_data = SensorDataResponse(
            **data.dict(),
            received_at=datetime.now().isoformat()
        )
        
        # Add to storage
        sensor_data.append(response_data)
        
        # Maintain rolling buffer
        if len(sensor_data) > MAX_RECORDS:
            sensor_data[:] = sensor_data[-MAX_RECORDS:]
        
        # Periodic save
        if len(sensor_data) % 10 == 0:
            save_data()
        
        # Log received data
        logger.info(f"📡 New data from {device_id}: {data.distance_cm}cm, {data.temperature_c}°C, GPS:{data.gps_valid}")
        
        return ApiResponse(
            status="success",
            message="Data received and stored successfully",
            data={"records_stored": len(sensor_data), "device_id": device_id}
        )
    except HTTPException:
        # Re-raise HTTP exceptions (like validation errors)
        raise
    except Exception as e:
        logger.error(f"❌ Error processing sensor data: {e}")
        raise HTTPException(status_code=500, detail="Failed to process sensor data")
    
# API Endpoints - Data Retrieval  
@app.get("/data",
         tags=["Data Retrieval"],
         summary="Get all sensor data",
         description="Retrieve complete dataset of all stored sensor readings with metadata")
async def get_all_data():
    return {
        "total_records": len(sensor_data),
        "oldest_record": sensor_data[0].received_at if sensor_data else None,
        "newest_record": sensor_data[-1].received_at if sensor_data else None,
        "data": [item.dict() for item in sensor_data]
    }


@app.get("/data/latest",
         tags=["Data Retrieval"], 
         summary="Get latest sensor readings",
         description="Retrieve the most recent sensor data - either from all devices or overall latest")
async def get_latest_data(show_all_devices: bool = True):
    if not sensor_data:
        raise HTTPException(status_code=404, detail="No sensor data available")
    
    if show_all_devices:
        # Group data by device_id and get the latest from each
        # Filter out entries with empty or invalid device IDs
        device_latest = {}
        for item in sensor_data:
            device_id = item.device_id.strip()  # Remove whitespace
            
            # Skip entries with empty, null, or invalid device IDs
            if not device_id or device_id.lower() in ['null', 'none', 'undefined']:
                continue
                
            if device_id not in device_latest or item.received_at > device_latest[device_id].received_at:
                device_latest[device_id] = item
        
        # If no valid devices found after filtering
        if not device_latest:
            raise HTTPException(status_code=404, detail="No valid device data available")
        
        return {
            "query_type": "latest_per_device",
            "total_devices": len(device_latest),
            "devices": {device_id: item.dict() for device_id, item in device_latest.items()}
        }
    else:
        # Return single most recent record
        return {
            "query_type": "single_latest",
            "data": sensor_data[-1].dict()
        }

@app.post("/data/cleanup",
           tags=["Data Management"],
           summary="Clean up invalid data",
           description="Remove records with empty or invalid device IDs")
async def cleanup_invalid_data():
    global sensor_data
    
    initial_count = len(sensor_data)
    
    # Filter out records with empty or invalid device IDs
    cleaned_data = []
    for item in sensor_data:
        device_id = item.device_id.strip() if item.device_id else ""
        if device_id and device_id.lower() not in ['null', 'none', 'undefined']:
            cleaned_data.append(item)
    
    removed_count = initial_count - len(cleaned_data)
    sensor_data = cleaned_data
    
    # Save cleaned data
    save_data()
    
    logger.info(f"🧹 Cleaned up {removed_count} invalid records")
    
    return ApiResponse(
        status="success",
        message=f"Cleanup completed: {removed_count} invalid records removed",
        data={
            "initial_records": initial_count,
            "remaining_records": len(sensor_data),
            "removed_records": removed_count
        }
    )


@app.get("/data/device/{device_id}",
         tags=["Data Retrieval"],
         summary="Get data by device ID", 
         description="Retrieve all sensor readings from a specific ESP32 device")
async def get_data_by_device(device_id: str):
    device_data = [item for item in sensor_data if item.device_id == device_id]
    if not device_data:
        raise HTTPException(status_code=404, detail=f"No data found for device: {device_id}")
    
    return {
        "device_id": device_id,
        "total_records": len(device_data),
        "first_reading": device_data[0].received_at,
        "last_reading": device_data[-1].received_at,
        "data": [item.dict() for item in device_data]
    }

# API Endpoints - Analytics
@app.get("/data/distance/{min_dist}/{max_dist}",
         tags=["Analytics"],
         summary="Filter by distance range",
         description="Get sensor readings within specified distance range (in centimeters)")
async def get_data_by_distance(min_dist: float, max_dist: float):
    if min_dist < 0 or max_dist < min_dist:
        raise HTTPException(status_code=400, detail="Invalid distance range parameters")
    
    filtered_data = [
        item for item in sensor_data 
        if min_dist <= item.distance_cm <= max_dist
    ]
    
    return {
        "filter_applied": f"Distance: {min_dist}cm - {max_dist}cm",
        "total_matching": len(filtered_data),
        "percentage_of_total": round((len(filtered_data) / len(sensor_data)) * 100, 2) if sensor_data else 0,
        "data": [item.dict() for item in filtered_data]
    }

@app.get("/data/temperature/{min_temp}/{max_temp}",
         tags=["Analytics"], 
         summary="Filter by temperature range",
         description="Get sensor readings within specified temperature range (in Celsius)")
async def get_data_by_temperature(min_temp: float, max_temp: float):
    if max_temp < min_temp:
        raise HTTPException(status_code=400, detail="Maximum temperature must be greater than minimum")
    
    filtered_data = [
        item for item in sensor_data 
        if min_temp <= item.temperature_c <= max_temp and item.temperature_c > -100
    ]
    
    return {
        "filter_applied": f"Temperature: {min_temp}°C - {max_temp}°C", 
        "total_matching": len(filtered_data),
        "percentage_of_total": round((len(filtered_data) / len(sensor_data)) * 100, 2) if sensor_data else 0,
        "data": [item.model_dump() for item in filtered_data]
    }

@app.get("/stats",
         tags=["Analytics"],
         summary="Get statistical analysis",
         description="Comprehensive statistical analysis of all sensor data including averages, ranges, and trends")
async def get_statistics():
    if not sensor_data:
        raise HTTPException(status_code=404, detail="No data available for analysis")
    
    # Filter valid readings
    valid_temp_data = [item.temperature_c for item in sensor_data if item.temperature_c > -100]
    valid_humidity_data = [item.humidity_percent for item in sensor_data if item.humidity_percent > -100]
    distance_data = [item.distance_cm for item in sensor_data if item.distance_cm > 0]
    
    stats = {
        "summary": {
            "total_records": len(sensor_data),
            "data_timespan_hours": (datetime.fromisoformat(sensor_data[-1].received_at) - 
                                  datetime.fromisoformat(sensor_data[0].received_at)).total_seconds() / 3600 if len(sensor_data) > 1 else 0,
            "latest_reading": sensor_data[-1].received_at,
            "gps_fix_rate_percent": round(sum(1 for item in sensor_data if item.gps_valid) / len(sensor_data) * 100, 2),
            "unique_devices": len(set(item.device_id for item in sensor_data))
        }
    }
    
    if valid_temp_data:
        stats["temperature"] = {
            "min_celsius": round(min(valid_temp_data), 2),
            "max_celsius": round(max(valid_temp_data), 2), 
            "average_celsius": round(sum(valid_temp_data) / len(valid_temp_data), 2),
            "valid_readings": len(valid_temp_data)
        }
    
    if valid_humidity_data:
        stats["humidity"] = {
            "min_percent": round(min(valid_humidity_data), 2),
            "max_percent": round(max(valid_humidity_data), 2),
            "average_percent": round(sum(valid_humidity_data) / len(valid_humidity_data), 2),
            "valid_readings": len(valid_humidity_data)
        }
    
    if distance_data:
        stats["distance"] = {
            "min_cm": round(min(distance_data), 2),
            "max_cm": round(max(distance_data), 2),
            "average_cm": round(sum(distance_data) / len(distance_data), 2),
            "valid_readings": len(distance_data)
        }
    
    return stats

# API Endpoints - File Operations
@app.get("/data/file",
         tags=["File Operations"],
         response_class=FileResponse,
         summary="⬇Download complete dataset",
         description="Download the complete sensor dataset as a JSON file for backup or external analysis")
async def download_data_file():
    if not os.path.exists(DATA_FILE):
        raise HTTPException(status_code=404, detail="Data file not found")
    
    return FileResponse(
        path=DATA_FILE,
        filename=f"esp32_sensor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        media_type="application/json"
    )

@app.get("/data/file/info",
         tags=["File Operations"],
         summary="Get file information", 
         description="Get metadata about the stored data file including size, modification time, and record count")
async def get_file_info():
    if not os.path.exists(DATA_FILE):
        raise HTTPException(status_code=404, detail="Data file not found")
    
    try:
        file_stats = os.stat(DATA_FILE)
        with open(DATA_FILE, 'r') as f:
            file_data = json.load(f)
        
        return {
            "file_path": DATA_FILE,
            "file_size_bytes": file_stats.st_size,
            "file_size_mb": round(file_stats.st_size / (1024*1024), 3),
            "last_modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
            "records_in_file": len(file_data),
            "records_in_memory": len(sensor_data),
            "file_structure_valid": all(key in file_data[0] for key in ["device_id", "timestamp", "received_at"]) if file_data else False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file info: {str(e)}")

# API Endpoints - Data Management
@app.delete("/data",
           tags=["Data Management"],
           summary="Clear all data",
           description="**⚠️ WARNING: This permanently deletes all sensor data from memory and storage file**")
async def clear_all_data():
    global sensor_data
    
    # Count records being deleted
    deleted_count = len(sensor_data)
    
    # Clear memory
    sensor_data = []
    
    # Delete file
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
        logger.warning(f"Cleared {deleted_count} sensor records and deleted storage file")
    
    return ApiResponse(
        status="success",
        message=f"Successfully cleared all data ({deleted_count} records deleted)",
        data={"deleted_records": deleted_count, "file_deleted": True}
    )

# API Endpoints - Dashboard
@app.get("/dashboard",
         tags=["Dashboard"], 
         response_class=HTMLResponse,
         summary="Live sensor dashboard",
         description="Access the web-based dashboard for real-time sensor monitoring and visualization")
async def get_dashboard():
    dashboard_file = "dashboard.html"
    
    if os.path.exists(dashboard_file):
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    else:
        # Enhanced fallback with inline dashboard
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>ESP32 Sensor Dashboard</title>
            <style>
                body {{
                    font-family: 'Segoe UI', sans-serif;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    color: white;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 40px 20px;
                    text-align: center;
                }}
                .card {{
                    background: rgba(255,255,255,0.95);
                    color: #333;
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    margin-bottom: 30px;
                }}
                .btn {{
                    background: linear-gradient(45deg, #667eea, #764ba2);
                    color: white;
                    padding: 12px 25px;
                    border: none;
                    border-radius: 25px;
                    text-decoration: none;
                    display: inline-block;
                    margin: 10px;
                    font-weight: 600;
                    transition: transform 0.3s ease;
                }}
                .btn:hover {{
                    transform: translateY(-2px);
                }}
                .grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin-top: 30px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h1>📊 ESP32 Sensor Dashboard</h1>
                    <p>Dashboard HTML file not found. Create <code>dashboard.html</code> in the server directory for the full dashboard experience.</p>
                    
                    <div class="grid">
                        <a href="/docs" class="btn">📚 API Documentation</a>
                        <a href="/data" class="btn">📊 Raw Data</a>
                        <a href="/data/latest" class="btn">🔄 Latest Reading</a>
                        <a href="/stats" class="btn">📈 Statistics</a>
                        <a href="/data/file" class="btn">💾 Download Data</a>
                    </div>
                    
                    <div style="margin-top: 40px; padding: 20px; background: #f8f9fa; border-radius: 10px; color: #666;">
                        <h3>🚀 Quick Setup</h3>
                        <p>To get the full dashboard:</p>
                        <ol style="text-align: left; max-width: 400px; margin: 0 auto;">
                            <li>Save the dashboard HTML file as <code>dashboard.html</code></li>
                            <li>Place it in the same directory as this server</li>
                            <li>Restart the server</li>
                            <li>Visit this page again for the full experience</li>
                        </ol>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error={
                "code": str(exc.status_code),
                "message": exc.detail if isinstance(exc.detail, str) else "HTTP error",
                "timestamp": datetime.now().isoformat()
            }
        ).model_dump(),
        headers=getattr(exc, 'headers', None)
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error={
                "code": "VALIDATION_ERROR", 
                "message": "Request validation failed",
                "details": exc.errors(),
                "timestamp": datetime.now().isoformat()
            }
        ).model_dump()
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error={
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": datetime.now().isoformat()
            }
        ).model_dump()
    )

if __name__ == "__main__":
    print("Starting ESP32 Sensor FastAPI Server with Scalar Documentation...")
    print(f"Dashboard: {DEV_URL}/dashboard")  
    print(f"API Docs (Scalar): {DEV_URL}/docs")
    print(f"Data endpoint: POST {DEV_URL}/data")
    print(f"File download: GET {DEV_URL}/data/file")
    print(f"Statistics: GET {DEV_URL}/stats")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )