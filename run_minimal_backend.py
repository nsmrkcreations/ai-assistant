#!/usr/bin/env python3
"""
Minimal AI Assistant Backend - Runs without optional dependencies
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
from typing import Dict, Any, List
import time

# Simple logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Assistant Backend - Minimal")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory storage
chat_history: List[Dict[str, Any]] = []
settings: Dict[str, Any] = {
    "theme": "system",
    "language": "en",
    "voiceEnabled": False,
    "automationEnabled": False
}

# WebSocket connections
active_connections: List[WebSocket] = []

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "AI Assistant Backend - Minimal Version", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0-minimal",
        "services": {
            "api": {"status": "healthy", "uptime": time.time()},
            "websocket": {"status": "healthy", "connections": len(manager.active_connections)}
        }
    }

@app.get("/services/status")
async def get_service_status():
    return {
        "services": {
            "api": {
                "status": "healthy",
                "uptime": time.time(),
                "memory_usage": "N/A"
            },
            "websocket": {
                "status": "healthy",
                "connections": len(manager.active_connections)
            },
            "database": {
                "status": "healthy",
                "type": "memory"
            }
        },
        "overall_status": "healthy"
    }

@app.get("/api/settings")
async def get_settings():
    return settings

@app.post("/api/settings")
async def update_settings(new_settings: Dict[str, Any]):
    settings.update(new_settings)
    
    # Broadcast settings update
    await manager.broadcast(json.dumps({
        "type": "settings_updated",
        "data": settings
    }))
    
    return {"status": "success", "settings": settings}

@app.get("/api/chat/history")
async def get_chat_history(limit: int = 50):
    return {"history": chat_history[-limit:]}

@app.post("/chat/message")
async def chat_message(request: Dict[str, Any]):
    message = request.get("message", "")
    context_id = request.get("context_id", str(int(time.time())))
    
    # Simple echo response for testing
    response_message = f"Echo: {message}"
    
    # Store in history
    chat_entry = {
        "id": context_id,
        "user_message": message,
        "assistant_response": response_message,
        "timestamp": time.time(),
        "metadata": {}
    }
    chat_history.append(chat_entry)
    
    # Keep only last 100 messages
    if len(chat_history) > 100:
        chat_history.pop(0)
    
    response = {
        "message": response_message,
        "context_id": context_id,
        "timestamp": time.time()
    }
    
    return response

@app.post("/api/errors")
async def log_error(error_data: Dict[str, Any]):
    logger.error(f"Frontend error: {error_data}")
    return {"status": "logged"}

@app.get("/api/performance")
async def get_performance():
    return {
        "cpu_percent": 10.0,
        "memory_percent": 15.0,
        "disk_usage": 50.0,
        "network_io": {"bytes_sent": 1024, "bytes_recv": 2048},
        "timestamp": time.time()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))
                
                elif message.get("type") == "chat":
                    chat_data = message.get("data", {})
                    user_message = chat_data.get("message", "")
                    context_id = chat_data.get("context_id", str(int(time.time())))
                    
                    # Simple echo response
                    response_message = f"WebSocket Echo: {user_message}"
                    
                    # Store in history
                    chat_entry = {
                        "id": context_id,
                        "user_message": user_message,
                        "assistant_response": response_message,
                        "timestamp": time.time(),
                        "metadata": {}
                    }
                    chat_history.append(chat_entry)
                    
                    # Send response
                    response = {
                        "type": "chat_response",
                        "data": {
                            "message": response_message,
                            "context_id": context_id,
                            "timestamp": time.time()
                        }
                    }
                    await websocket.send_text(json.dumps(response))
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {data}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Serve static files for frontend
static_dir = Path(__file__).parent / "backend" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Simple HTML page for testing
@app.get("/test")
async def test_page():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Assistant - Test Page</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .healthy { background-color: #d4edda; color: #155724; }
            .error { background-color: #f8d7da; color: #721c24; }
            button { padding: 10px 20px; margin: 5px; cursor: pointer; }
            #messages { border: 1px solid #ccc; height: 300px; overflow-y: auto; padding: 10px; margin: 10px 0; }
            input[type="text"] { width: 70%; padding: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AI Assistant - Minimal Backend Test</h1>
            
            <div id="status" class="status healthy">
                Backend is running successfully!
            </div>
            
            <h2>WebSocket Chat Test</h2>
            <div id="messages"></div>
            <input type="text" id="messageInput" placeholder="Type a message..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">Send</button>
            <button onclick="connectWebSocket()">Connect WebSocket</button>
            
            <h2>API Tests</h2>
            <button onclick="testHealth()">Test Health</button>
            <button onclick="testSettings()">Test Settings</button>
            <button onclick="testChat()">Test Chat API</button>
            
            <div id="results"></div>
        </div>
        
        <script>
            let ws = null;
            
            function log(message) {
                const messages = document.getElementById('messages');
                messages.innerHTML += '<div>' + new Date().toLocaleTimeString() + ': ' + message + '</div>';
                messages.scrollTop = messages.scrollHeight;
            }
            
            function connectWebSocket() {
                if (ws) {
                    ws.close();
                }
                
                ws = new WebSocket('ws://localhost:8000/ws');
                
                ws.onopen = function() {
                    log('WebSocket connected');
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    log('Received: ' + JSON.stringify(data));
                };
                
                ws.onclose = function() {
                    log('WebSocket disconnected');
                };
                
                ws.onerror = function(error) {
                    log('WebSocket error: ' + error);
                };
            }
            
            function sendMessage() {
                const input = document.getElementById('messageInput');
                const message = input.value.trim();
                if (!message || !ws) return;
                
                const data = {
                    type: 'chat',
                    data: {
                        message: message,
                        context_id: Date.now().toString()
                    }
                };
                
                ws.send(JSON.stringify(data));
                log('Sent: ' + message);
                input.value = '';
            }
            
            async function testHealth() {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    document.getElementById('results').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    document.getElementById('results').innerHTML = '<div class="error">Error: ' + error.message + '</div>';
                }
            }
            
            async function testSettings() {
                try {
                    const response = await fetch('/api/settings');
                    const data = await response.json();
                    document.getElementById('results').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    document.getElementById('results').innerHTML = '<div class="error">Error: ' + error.message + '</div>';
                }
            }
            
            async function testChat() {
                try {
                    const response = await fetch('/chat/message', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: 'Hello from API test!' })
                    });
                    const data = await response.json();
                    document.getElementById('results').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    document.getElementById('results').innerHTML = '<div class="error">Error: ' + error.message + '</div>';
                }
            }
            
            // Auto-connect WebSocket on page load
            window.onload = function() {
                connectWebSocket();
            };
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    print("🚀 Starting AI Assistant Minimal Backend...")
    print("📍 Backend will be available at: http://localhost:8000")
    print("🧪 Test page available at: http://localhost:8000/test")
    print("💬 WebSocket endpoint: ws://localhost:8000/ws")
    print("📊 Health check: http://localhost:8000/health")
    
    # Try different ports if 8000 is busy
    for port in [8000, 8001, 8002, 8003]:
        try:
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=port,
                log_level="info",
                reload=False
            )
            break
        except OSError as e:
            if "address already in use" in str(e).lower() or "10048" in str(e):
                print(f"Port {port} is busy, trying next port...")
                continue
            else:
                raise