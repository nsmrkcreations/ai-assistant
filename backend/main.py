"""
AI Assistant Desktop Application - FastAPI Backend
Main entry point for the backend services
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import os
from datetime import datetime

# Import our services
from services.service_manager import ServiceManager
from services.llm_service import LLMService
from services.stt_service import STTService
from services.tts_service import TTSService
from services.automation_service import AutomationService
from services.web_automation_service import WebAutomationService
from services.watchdog_service import WatchdogService
from services.learning_service import LearningService
from services.security_service import SecurityService
from services.update_service import UpdateService
from services.asset_generation_service import AssetGenerationService
from services.database_service import DatabaseService
from services.plugin_service import PluginService
from services.recovery_service import RecoveryService
from services.performance_service import PerformanceService
from models.chat_models import ChatRequest, ChatResponse, SystemStatus, ServiceStatus
from utils.config import Config
from utils.logger import setup_logging

# Global service manager
service_manager: Optional[ServiceManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup services using Service Manager"""
    global service_manager
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting AI Assistant Backend...")
    
    try:
        # Initialize configuration
        config = Config()
        
        # Create service manager
        service_manager = ServiceManager(config)
        
        # Register core services (always required)
        service_manager.register_service("database", DatabaseService, [], 10)
        service_manager.register_service("security", SecurityService, ["database"], 20)
        service_manager.register_service("recovery", RecoveryService, ["database"], 25)
        service_manager.register_service("performance", PerformanceService, ["database"], 78)
        
        # Register optional services with graceful degradation
        optional_services = [
            ("plugin", PluginService, ["database"], 30),
            ("llm", LLMService, ["database", "security"], 40),
            ("stt", STTService, ["database"], 50),
            ("tts", TTSService, ["database"], 50),
            ("automation", AutomationService, ["database", "security"], 60),
            ("web_automation", WebAutomationService, ["database", "security"], 60),
            ("learning", LearningService, ["database"], 70),
            ("asset_generation", AssetGenerationService, ["database"], 75),
            ("updater", UpdateService, ["database"], 90)
        ]
        
        for service_name, service_class, deps, priority in optional_services:
            try:
                service_manager.register_service(service_name, service_class, deps, priority)
                logger.info(f"Registered optional service: {service_name}")
            except Exception as e:
                logger.warning(f"Optional service {service_name} not available: {e}")
        
        # Start all services (core services must start, optional can fail)
        success = await service_manager.start_all_services(allow_partial_failure=True)
        if not success:
            logger.warning("Some services failed to start, but continuing with available services")
        
        # Register services with recovery service for monitoring
        recovery_service = service_manager.get_service("recovery")
        if recovery_service:
            for name in service_manager.services.keys():
                service = service_manager.get_service(name)
                if service and name != "recovery":
                    recovery_service.register_service(name, service)
        
        logger.info("All services initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    finally:
        # Cleanup services using service manager
        logger.info("Shutting down services...")
        if service_manager:
            await service_manager.stop_all_services()

# Create FastAPI app
app = FastAPI(
    title="AI Assistant Backend",
    description="Backend services for AI Assistant Desktop Application",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.get("/")
async def root():
    """Serve the main application"""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_file = os.path.join(static_dir, "index.html")
    
    if os.path.exists(index_file):
        return FileResponse(index_file)
    else:
        return {"message": "AI Assistant Backend is running", "version": "1.0.0", "note": "Frontend not available"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        status = await get_system_status()
        return {"status": "healthy", "timestamp": datetime.now().isoformat(), "details": status}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e), "timestamp": datetime.now().isoformat()}
        )

@app.get("/system/status")
async def get_system_status() -> SystemStatus:
    """Get comprehensive system status"""
    try:
        if not service_manager:
            raise HTTPException(status_code=503, detail="Service manager not initialized")
        
        # Get all service statuses using service manager
        all_statuses = await service_manager.get_all_service_status()
        
        # Extract specific service statuses
        llm_status = all_statuses.get('llm')
        stt_status = all_statuses.get('stt')
        tts_status = all_statuses.get('tts')
        automation_status = all_statuses.get('automation')
        learning_status = all_statuses.get('learning')
        security_status = all_statuses.get('security')
        update_status = all_statuses.get('updater')
        
        # Determine overall status
        status_values = [s.status.value for s in all_statuses.values() if s]
        
        if any(s == ServiceStatus.OFFLINE.value for s in status_values):
            overall_status = ServiceStatus.OFFLINE
        elif any(s == ServiceStatus.UNHEALTHY.value for s in status_values):
            overall_status = ServiceStatus.UNHEALTHY
        elif any(s == ServiceStatus.DEGRADED.value for s in status_values):
            overall_status = ServiceStatus.DEGRADED
        else:
            overall_status = ServiceStatus.HEALTHY
        
        status = SystemStatus(
            llm_status=llm_status,
            stt_status=stt_status,
            tts_status=tts_status,
            automation_status=automation_status,
            learning_status=learning_status,
            security_status=security_status,
            update_status=update_status,
            overall_status=overall_status
        )
        return status
    except Exception as e:
        logging.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/message")
async def process_message(request: ChatRequest) -> ChatResponse:
    """Process text message from user"""
    try:
        logger = logging.getLogger(__name__)
        logger.info(f"Processing message: {request.message[:100]}...")
        
        # Get services from service manager
        llm_service = service_manager.get_service('llm')
        automation_service = service_manager.get_service('automation')
        tts_service = service_manager.get_service('tts')
        learning_service = service_manager.get_service('learning')
        
        message_text = request.message
        
        # Handle voice input if provided
        if hasattr(request, 'audio_data') and request.audio_data:
            stt_service = service_manager.get_service('stt')
            if stt_service:
                try:
                    # Decode base64 audio data
                    import base64
                    audio_bytes = base64.b64decode(request.audio_data)
                    
                    # Transcribe audio
                    transcription = await stt_service.transcribe(audio_bytes)
                    message_text = transcription
                    logger.info(f"Voice transcribed: {transcription}")
                    
                except Exception as e:
                    logger.error(f"Voice transcription failed: {e}")
                    raise HTTPException(status_code=400, detail="Voice transcription failed")
        
        # Process with LLM
        llm_response = await llm_service.process_message(
            message_text, 
            request.context_id
        )
        
        # Check if automation is needed
        if llm_response.requires_automation and automation_service:
            automation_result = await automation_service.execute_task(
                llm_response.automation_task
            )
            llm_response.automation_result = automation_result
        
        # Generate TTS if requested
        audio_url = None
        if request.include_audio and tts_service:
            audio_url = await tts_service.generate_speech(llm_response.text)
        
        # Learn from interaction
        if learning_service:
            await learning_service.record_interaction(request, llm_response)
        
        response = ChatResponse(
            message=llm_response.text,
            context_id=llm_response.context_id,
            audio_url=audio_url,
            transcription=message_text if (hasattr(request, 'audio_data') and request.audio_data) else None,
            automation_result=llm_response.automation_result,
            suggestions=llm_response.suggestions,
            timestamp=datetime.now().isoformat()
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/voice")
async def process_voice(audio: UploadFile = File(...)) -> ChatResponse:
    """Process voice input from user"""
    try:
        logger = logging.getLogger(__name__)
        logger.info("Processing voice input...")
        
        # Get STT service from service manager
        stt_service = service_manager.get_service('stt')
        if not stt_service:
            raise HTTPException(status_code=503, detail="Speech-to-text service not available")
        
        # Convert speech to text
        audio_data = await audio.read()
        transcription = await stt_service.transcribe(audio_data)
        
        if not transcription.strip():
            raise HTTPException(status_code=400, detail="No speech detected")
        
        # Process as text message
        request = ChatRequest(
            message=transcription,
            include_audio=True,  # Always include audio for voice requests
            context_id=None
        )
        
        response = await process_message(request)
        response.transcription = transcription
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing voice: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "chat":
                request = ChatRequest(**message_data.get("data", {}))
                response = await process_message(request)
                await manager.send_personal_message(
                    json.dumps({
                        "type": "chat_response",
                        "data": response.dict()
                    }),
                    websocket
                )
            elif message_data.get("type") == "status":
                status = await get_system_status()
                await manager.send_personal_message(
                    json.dumps({
                        "type": "status_response",
                        "data": status.dict()
                    }),
                    websocket
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.post("/automation/execute")
async def execute_automation(task_data: dict):
    """Execute automation task"""
    try:
        automation_service = service_manager.get_service('automation')
        if not automation_service:
            raise HTTPException(status_code=503, detail="Automation service not available")
        
        result = await automation_service.execute_task(task_data)
        return {"status": "success", "result": result}
    except Exception as e:
        logging.error(f"Automation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/learning/feedback")
async def provide_feedback(feedback_data: dict):
    """Provide feedback for learning system"""
    try:
        learning_service = service_manager.get_service('learning')
        if not learning_service:
            raise HTTPException(status_code=503, detail="Learning service not available")
        
        await learning_service.process_feedback(feedback_data)
        return {"status": "success", "message": "Feedback recorded"}
    except Exception as e:
        logging.error(f"Learning feedback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/system/update")
async def trigger_update():
    """Trigger system update check and installation"""
    try:
        update_service = service_manager.get_service('updater')
        if not update_service:
            raise HTTPException(status_code=503, detail="Update service not available")
        
        result = await update_service.check_and_update()
        return {"status": "success", "result": result}
    except Exception as e:
        logging.error(f"Update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/services/{service_name}/restart")
async def restart_service(service_name: str):
    """Restart a specific service"""
    try:
        if not service_manager:
            raise HTTPException(status_code=503, detail="Service manager not available")
        
        success = await service_manager.restart_service(service_name)
        if success:
            return {"status": "success", "message": f"Service {service_name} restarted"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to restart service {service_name}")
    except Exception as e:
        logging.error(f"Service restart error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/services/status")
async def get_all_services_status():
    """Get status of all services"""
    try:
        if not service_manager:
            raise HTTPException(status_code=503, detail="Service manager not available")
        
        statuses = await service_manager.get_all_service_status()
        return {"services": {name: status.dict() for name, status in statuses.items()}}
    except Exception as e:
        logging.error(f"Error getting service statuses: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings")
async def get_settings():
    """Get application settings"""
    try:
        database_service = service_manager.get_service('database')
        if not database_service:
            raise HTTPException(status_code=503, detail="Database service not available")
        
        # Get all user preferences
        settings = {}
        
        # General settings
        settings['theme'] = await database_service.get_user_preference('theme', 'auto')
        settings['language'] = await database_service.get_user_preference('language', 'en')
        settings['autoStart'] = await database_service.get_user_preference('autoStart', True)
        settings['minimizeToTray'] = await database_service.get_user_preference('minimizeToTray', True)
        settings['notifications'] = await database_service.get_user_preference('notifications', True)
        
        # Voice settings
        settings['voiceActivation'] = await database_service.get_user_preference('voiceActivation', False)
        settings['llmModel'] = await database_service.get_user_preference('llmModel', 'llama3.1:8b')
        settings['sttModel'] = await database_service.get_user_preference('sttModel', 'base')
        settings['ttsVoice'] = await database_service.get_user_preference('ttsVoice', 'en_US-lessac-medium')
        settings['ttsSpeed'] = await database_service.get_user_preference('ttsSpeed', 1.0)
        
        # Automation settings
        settings['enableAutomation'] = await database_service.get_user_preference('enableAutomation', True)
        settings['confirmActions'] = await database_service.get_user_preference('confirmActions', True)
        settings['safetyMode'] = await database_service.get_user_preference('safetyMode', True)
        
        # Other settings
        settings['autoUpdate'] = await database_service.get_user_preference('autoUpdate', True)
        settings['enableLearning'] = await database_service.get_user_preference('enableLearning', True)
        
        # Global shortcuts
        settings['globalShortcuts'] = await database_service.get_user_preference('globalShortcuts', {
            'voiceCommand': 'CmdOrCtrl+Shift+V',
            'quickChat': 'CmdOrCtrl+Shift+C',
            'toggleWindow': 'CmdOrCtrl+Shift+A',
            'emergencyStop': 'CmdOrCtrl+Shift+Escape'
        })
        
        # Plugin settings
        settings['plugins'] = await database_service.get_user_preference('plugins', {
            'enabled': True,
            'autoUpdate': False
        })
        
        # Database settings
        settings['database'] = await database_service.get_user_preference('database', {
            'retentionDays': 30,
            'autoCleanup': True
        })
        
        # Recovery settings
        settings['recovery'] = await database_service.get_user_preference('recovery', {
            'enabled': True,
            'maxAttempts': 3
        })
        
        return settings
        
    except Exception as e:
        logging.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings")
async def update_settings(settings: dict):
    """Update application settings"""
    try:
        database_service = service_manager.get_service('database')
        if not database_service:
            raise HTTPException(status_code=503, detail="Database service not available")
        
        # Save all settings to database
        for key, value in settings.items():
            await database_service.save_user_preference(key, value)
        
        # Apply settings to services
        await _apply_settings_to_services(settings)
        
        # Broadcast settings update via WebSocket
        await manager.broadcast(json.dumps({
            "type": "settings_updated",
            "data": settings
        }))
        
        return {"status": "success", "message": "Settings updated successfully"}
        
    except Exception as e:
        logging.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _apply_settings_to_services(settings: dict):
    """Apply settings changes to relevant services"""
    try:
        # Update LLM service settings
        llm_service = service_manager.get_service('llm')
        if llm_service and hasattr(llm_service, 'update_model'):
            if 'llmModel' in settings:
                await llm_service.update_model(settings['llmModel'])
        
        # Update STT service settings
        stt_service = service_manager.get_service('stt')
        if stt_service and hasattr(stt_service, 'update_model'):
            if 'sttModel' in settings:
                await stt_service.update_model(settings['sttModel'])
        
        # Update TTS service settings
        tts_service = service_manager.get_service('tts')
        if tts_service:
            if hasattr(tts_service, 'update_voice') and 'ttsVoice' in settings:
                await tts_service.update_voice(settings['ttsVoice'])
            if hasattr(tts_service, 'update_speed') and 'ttsSpeed' in settings:
                await tts_service.update_speed(settings['ttsSpeed'])
        
        # Update automation service settings
        automation_service = service_manager.get_service('automation')
        if automation_service and hasattr(automation_service, 'update_settings'):
            automation_settings = {
                'enabled': settings.get('enableAutomation', True),
                'confirm_actions': settings.get('confirmActions', True),
                'safety_mode': settings.get('safetyMode', True)
            }
            await automation_service.update_settings(automation_settings)
        
        # Update learning service settings
        learning_service = service_manager.get_service('learning')
        if learning_service and hasattr(learning_service, 'update_settings'):
            if 'enableLearning' in settings:
                await learning_service.update_settings({'enabled': settings['enableLearning']})
        
        # Update plugin service settings
        plugin_service = service_manager.get_service('plugin')
        if plugin_service and hasattr(plugin_service, 'update_settings'):
            if 'plugins' in settings:
                await plugin_service.update_settings(settings['plugins'])
        
        # Update recovery service settings
        recovery_service = service_manager.get_service('recovery')
        if recovery_service and hasattr(recovery_service, 'update_settings'):
            if 'recovery' in settings:
                await recovery_service.update_settings(settings['recovery'])
        
    except Exception as e:
        logging.error(f"Error applying settings to services: {e}")

@app.get("/api/settings/shortcuts")
async def get_shortcuts():
    """Get current global shortcuts"""
    try:
        database_service = service_manager.get_service('database')
        if not database_service:
            raise HTTPException(status_code=503, detail="Database service not available")
        
        shortcuts = await database_service.get_user_preference('globalShortcuts', {
            'voiceCommand': 'CmdOrCtrl+Shift+V',
            'quickChat': 'CmdOrCtrl+Shift+C',
            'toggleWindow': 'CmdOrCtrl+Shift+A',
            'emergencyStop': 'CmdOrCtrl+Shift+Escape'
        })
        
        return shortcuts
        
    except Exception as e:
        logging.error(f"Error getting shortcuts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/shortcuts")
async def update_shortcuts(shortcuts: dict):
    """Update global shortcuts"""
    try:
        database_service = service_manager.get_service('database')
        if not database_service:
            raise HTTPException(status_code=503, detail="Database service not available")
        
        # Save shortcuts to database
        await database_service.save_user_preference('globalShortcuts', shortcuts)
        
        # Notify frontend to update shortcuts
        await manager.broadcast(json.dumps({
            "type": "shortcuts_updated",
            "data": shortcuts
        }))
        
        return {"status": "success", "message": "Shortcuts updated successfully"}
        
    except Exception as e:
        logging.error(f"Error updating shortcuts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/errors")
async def log_error(error_data: dict):
    """Log frontend errors"""
    try:
        database_service = service_manager.get_service('database')
        if database_service:
            await database_service.log_system_event(
                level="ERROR",
                service="frontend",
                message=f"Frontend Error: {error_data.get('error', {}).get('message', 'Unknown error')}"
            )
        
        # Log to console as well
        logging.error(f"Frontend Error: {json.dumps(error_data, indent=2)}")
        
        return {"status": "success", "message": "Error logged successfully"}
        
    except Exception as e:
        logging.error(f"Error logging frontend error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/performance")
async def get_performance_metrics():
    """Get current performance metrics"""
    try:
        performance_service = service_manager.get_service('performance')
        if not performance_service:
            raise HTTPException(status_code=503, detail="Performance service not available")
        
        summary = performance_service.get_performance_summary()
        return summary
        
    except Exception as e:
        logging.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/performance/optimize")
async def optimize_performance():
    """Manually trigger performance optimization"""
    try:
        performance_service = service_manager.get_service('performance')
        if not performance_service:
            raise HTTPException(status_code=503, detail="Performance service not available")
        
        result = await performance_service.optimize_performance()
        return result
        
    except Exception as e:
        logging.error(f"Error optimizing performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,  # Disable in production
        log_level="info"
    )