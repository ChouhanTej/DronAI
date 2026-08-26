"""
Extreme Conditions Failure Risk Dashboard - FastAPI Backend Server
Hosts WebSocket telemetry stream, REST API endpoints, serial stream polling,
and anomaly inference pipeline.
"""

import asyncio
import datetime
import json
import os
import sys
import time
from typing import List, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from anomaly_service import AnomalyService
from serial_service import SerialHardwareService

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: launch telemetry background loop
    task = asyncio.create_task(telemetry_loop())
    yield
    # Shutdown: cancel task
    task.cancel()

app = FastAPI(
    title="Extreme Conditions Sensing & Failure Risk Monitoring API",
    description="Real-Time Telemetry & Isolation Forest Anomaly Detection Backend",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for React frontend (Vite dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate services
anomaly_service = AnomalyService()
serial_service = SerialHardwareService(port="/dev/cu.SLAB_USBtoUART")

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WS] Client connected. Total active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[WS] Client disconnected. Active connections remaining: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# Background Telemetry Polling Loop
async def telemetry_loop():
    """Background task reading serial telemetry, running anomaly detection, and broadcasting via WS."""
    print("[BACKEND] Telemetry processing loop started.")
    while True:
        try:
            raw_sample = serial_service.read_next_sample()
            
            now_str = datetime.datetime.now().strftime("%H:%M:%S")

            if raw_sample is not None:
                # Process through Anomaly Service
                processed = anomaly_service.process_sample(raw_sample)

                payload = {
                    "type": "TELEMETRY_UPDATE",
                    "timestamp": now_str,
                    "esp32_status": "CONNECTED" if serial_service.is_connected else "DISCONNECTED",
                    "dht11_status": "ONLINE" if serial_service.dht11_online else "ERROR",
                    "mpu6050_status": "ONLINE" if serial_service.mpu6050_online else "ERROR",
                    "ml_model_status": "LOADED" if anomaly_service.is_loaded else "ERROR",
                    "demo_mode": serial_service.demo_mode,
                    "data": processed
                }
                await manager.broadcast(payload)
            else:
                # Send heartbeat with connection status when disconnected
                offline_payload = {
                    "type": "HEARTBEAT",
                    "timestamp": now_str,
                    "esp32_status": "CONNECTED" if serial_service.is_connected else "DISCONNECTED",
                    "dht11_status": "ONLINE" if serial_service.dht11_online else "ERROR",
                    "mpu6050_status": "ONLINE" if serial_service.mpu6050_online else "ERROR",
                    "ml_model_status": "LOADED" if anomaly_service.is_loaded else "ERROR",
                    "demo_mode": serial_service.demo_mode,
                    "data": None
                }
                await manager.broadcast(offline_payload)

        except Exception as e:
            print(f"[BACKEND ERROR] Exception in telemetry loop: {e}")

        # Sleep ~0.5s for 2 Hz update rate
        await asyncio.sleep(0.5)

@app.get("/api/status")
def get_system_status():
    """Returns system operational status and model readiness."""
    return {
        "esp32_status": "CONNECTED" if serial_service.is_connected else "DISCONNECTED",
        "dht11_status": "ONLINE" if serial_service.dht11_online else "ERROR",
        "mpu6050_status": "ONLINE" if serial_service.mpu6050_online else "ERROR",
        "ml_model": "Isolation Forest",
        "model_status": "LOADED" if anomaly_service.is_loaded else "ERROR",
        "demo_mode": serial_service.demo_mode,
        "sampling_rate": "~1 Hz"
    }

class DemoModeRequest(BaseModel):
    enabled: bool

@app.post("/api/demo-mode")
def set_demo_mode(req: DemoModeRequest):
    """Toggles Demo Mode dataset replay on or off."""
    serial_service.demo_mode = req.enabled
    if req.enabled:
        serial_service.connect()
    print(f"[API] Demo mode set to: {req.enabled}")
    return {"demo_mode": serial_service.demo_mode, "status": "SUCCESS"}

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time telemetry streaming."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive & handle incoming client messages if any
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
