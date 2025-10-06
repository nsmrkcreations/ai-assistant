"""
Pytest configuration and fixtures for AI Assistant tests
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import shutil
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock
import json
import os

# Mock torch and other ML dependencies before importing services
sys.modules['torch'] = Mock()
sys.modules['diffusers'] = Mock()
sys.modules['PIL'] = Mock()
sys.modules['cv2'] = Mock()

# Import application components
from utils.config import Config
from services.llm_service import LLMService
from services.stt_service import STTService
from services.tts_service import TTSService
from services.automation_service import AutomationService
from services.security_service import SecurityService
from services.learning_service import LearningService
from services.watchdog_service import WatchdogService
from services.update_service import UpdateService
from services.asset_generation_service import AssetGenerationService
from services.web_automation_service import WebAutomationService

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture
def test_config(temp_dir):
    """Create test configuration"""
    config_path = temp_dir / "config.json"
    test_config_data = {
        "models": {
            "llm_model": "test-model",
            "stt_model": "tiny",
            "tts_voice": "test-voice",
            "image_model": "test-image-model"
        },
        "automation": {
            "enable_gui_automation": True,
            "enable_web_automation": True,
            "safety_checks": True
        },
        "security": {
            "enable_sandboxing": True,
            "require_permissions": True
        },
        "learning": {
            "enable_learning": True,
            "pattern_detection": True
        },
        "updates": {
            "auto_update": False,
            "check_interval": 3600
        }
    }
    
    with open(config_path, 'w') as f:
        json.dump(test_config_data, f)
    
    # Mock the config to use temp directory
    config = Config(str(config_path))
    config.data_dir = temp_dir / "data"
    config.data_dir.mkdir(exist_ok=True)
    
    return config

@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response"""
    return {
        "message": {
            "content": "This is a test response from the AI assistant."
        }
    }

@pytest.fixture
def mock_audio_data():
    """Mock audio data for testing"""
    return b"fake_audio_data_for_testing"

@pytest.fixture
def sample_chat_request():
    """Sample chat request for testing"""
    from models.chat_models import ChatRequest
    return ChatRequest(
        message="Hello, can you help me with a task?",
        include_audio=True,
        context_id="test-context-123"
    )

@pytest.fixture
def sample_automation_task():
    """Sample automation task for testing"""
    from models.chat_models import AutomationTask
    return AutomationTask(
        task_id="test-task-123",
        task_type="app_control",
        parameters={
            "action": "open",
            "app_name": "notepad"
        },
        priority=1,
        timeout=30
    )

@pytest_asyncio.fixture
async def llm_service(test_config):
    """Create LLM service for testing"""
    service = LLMService(test_config)
    # Mock the Ollama client
    service.ollama_url = "http://mock-ollama:11434"
    # Mock the start method to avoid actual Ollama connection
    service._check_ollama_status = AsyncMock()
    service._ensure_model_available = AsyncMock()
    await service.start()
    yield service

@pytest_asyncio.fixture
async def stt_service(test_config):
    """Create STT service for testing"""
    service = STTService(test_config)
    # Mock whisper executable
    service.whisper_path = Path("/mock/whisper")
    service.model_path = "/mock/model.bin"
    await service.start()
    yield service

@pytest_asyncio.fixture
async def tts_service(test_config):
    """Create TTS service for testing"""
    service = TTSService(test_config)
    # Mock piper executable
    service.piper_path = Path("/mock/piper")
    service.voice_model_path = "/mock/voice.onnx"
    await service.start()
    yield service

@pytest_asyncio.fixture
async def automation_service(test_config):
    """Create automation service for testing"""
    service = AutomationService(test_config)
    await service.start()
    yield service

@pytest_asyncio.fixture
async def security_service(test_config):
    """Create security service for testing"""
    service = SecurityService(test_config)
    await service.start()
    yield service

@pytest_asyncio.fixture
async def learning_service(test_config):
    """Create learning service for testing"""
    service = LearningService(test_config)
    await service.start()
    yield service

@pytest_asyncio.fixture
async def all_services(test_config):
    """Create all services for integration testing"""
    services = {}
    
    services['config'] = test_config
    services['security'] = SecurityService(test_config)
    services['llm'] = LLMService(test_config)
    services['stt'] = STTService(test_config)
    services['tts'] = TTSService(test_config)
    services['automation'] = AutomationService(test_config)
    services['web_automation'] = WebAutomationService(test_config)
    services['learning'] = LearningService(test_config)
    # Mock asset generation service to avoid torch dependency
    services['asset_generation'] = Mock()
    services['asset_generation'].start = AsyncMock()
    services['asset_generation'].config = test_config
    services['updater'] = UpdateService(test_config)
    
    # Initialize services that need startup
    await services['security'].start()
    
    # Mock LLM service dependencies
    services['llm'].ollama_url = "http://mock-ollama:11434"
    services['llm']._check_ollama_status = AsyncMock()
    services['llm']._ensure_model_available = AsyncMock()
    await services['llm'].start()
    
    # Mock STT service dependencies
    services['stt']._ensure_model_available = AsyncMock()
    services['stt']._download_model = AsyncMock()
    services['stt'].model_path = "/mock/path/to/model.bin"
    services['stt'].whisper_path = "/mock/path/to/whisper"
    await services['stt'].start()
    
    # Mock TTS service dependencies
    services['tts']._ensure_piper_available = AsyncMock()
    services['tts']._install_piper = AsyncMock()
    services['tts']._ensure_voice_model_available = AsyncMock()
    services['tts']._download_voice_model = AsyncMock()
    services['tts'].piper_path = Path("/mock/path/to/piper")
    services['tts'].voice_model_path = "/mock/path/to/voice.onnx"
    await services['tts'].start()
    await services['automation'].start()
    await services['web_automation'].start()
    await services['learning'].start()
    await services['asset_generation'].start()
    await services['updater'].start()
    
    # Create watchdog service after other services are initialized
    services['watchdog'] = WatchdogService(test_config, services)
    await services['watchdog'].start()
    
    yield services

@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for HTTP requests"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_response.content = b"mock content"
    mock_client.get.return_value = mock_response
    mock_client.post.return_value = mock_response
    return mock_client

@pytest.fixture
def mock_subprocess():
    """Mock subprocess for external command testing"""
    mock_process = Mock()
    mock_process.returncode = 0
    mock_process.stdout = b"mock stdout"
    mock_process.stderr = b""
    mock_process.communicate.return_value = (b"mock stdout", b"")
    return mock_process

@pytest.fixture
def sample_user_interaction():
    """Sample user interaction for learning tests"""
    from models.chat_models import LearningData
    return LearningData(
        interaction_id="test-interaction-123",
        user_input="Open Excel and create a spreadsheet",
        assistant_response="I'll help you open Excel and create a new spreadsheet.",
        context={"application": "excel", "task_type": "document_creation"}
    )

@pytest.fixture
def sample_security_event():
    """Sample security event for testing"""
    from models.chat_models import SecurityEvent
    return SecurityEvent(
        event_id="test-event-123",
        event_type="permission_request",
        severity="medium",
        description="User requested file access permission",
        source="automation_service"
    )

# Test data fixtures
@pytest.fixture
def test_image_prompt():
    """Test image generation prompt"""
    return "A beautiful sunset over mountains with vibrant colors"

@pytest.fixture
def test_voice_commands():
    """Common voice commands for testing"""
    return [
        "Open Microsoft Excel",
        "Create a new document",
        "Generate an image of a cat",
        "Browse to Google.com",
        "What's the weather today?",
        "Help me automate my daily tasks"
    ]

@pytest.fixture
def test_file_paths(temp_dir):
    """Test file paths for file operations"""
    return {
        "text_file": temp_dir / "test.txt",
        "image_file": temp_dir / "test.png",
        "audio_file": temp_dir / "test.wav",
        "config_file": temp_dir / "config.json"
    }

# Performance test fixtures
@pytest.fixture
def performance_thresholds():
    """Performance thresholds for testing"""
    return {
        "llm_response_time": 5.0,  # seconds
        "stt_processing_time": 3.0,  # seconds
        "tts_generation_time": 2.0,  # seconds
        "automation_execution_time": 10.0,  # seconds
        "image_generation_time": 30.0,  # seconds
        "memory_usage_limit": 1024 * 1024 * 1024,  # 1GB
        "cpu_usage_limit": 80.0  # percent
    }

# Error simulation fixtures
@pytest.fixture
def network_error():
    """Simulate network error"""
    from httpx import ConnectError
    return ConnectError("Connection failed")

@pytest.fixture
def file_permission_error():
    """Simulate file permission error"""
    return PermissionError("Access denied")

@pytest.fixture
def memory_error():
    """Simulate memory error"""
    return MemoryError("Out of memory")

# Mock external dependencies
@pytest.fixture(autouse=True)
def mock_external_deps(monkeypatch):
    """Mock external dependencies that might not be available in test environment"""
    
    # Mock torch/CUDA
    mock_torch = Mock()
    mock_torch.cuda.is_available.return_value = False
    mock_torch.float16 = "float16"
    mock_torch.float32 = "float32"
    monkeypatch.setitem(sys.modules, "torch", mock_torch)
    
    # Mock GUI libraries
    mock_pyautogui = Mock()
    mock_pyautogui.FAILSAFE = True
    mock_pyautogui.PAUSE = 0.1
    monkeypatch.setitem(sys.modules, "pyautogui", mock_pyautogui)
    
    # Mock audio libraries
    mock_speech_recognition = Mock()
    monkeypatch.setitem(sys.modules, "speech_recognition", mock_speech_recognition)
    
    # Mock Playwright
    mock_playwright = Mock()
    monkeypatch.setitem(sys.modules, "playwright", mock_playwright)

# Database fixtures for learning service
@pytest.fixture
def mock_chroma_client():
    """Mock ChromaDB client"""
    mock_client = Mock()
    mock_collection = Mock()
    mock_collection.add = Mock()
    mock_collection.query = Mock(return_value={"documents": [], "metadatas": []})
    mock_client.get_or_create_collection.return_value = mock_collection
    return mock_client

# FastAPI test client fixture
@pytest_asyncio.fixture
async def client():
    """Create FastAPI test client"""
    from fastapi.testclient import TestClient
    from main import app
    
    with TestClient(app) as test_client:
        yield test_client

# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Cleanup test files after each test"""
    yield
    # Cleanup any test files that might have been created
    test_patterns = ["test_*", "mock_*", "temp_*"]
    for pattern in test_patterns:
        for file_path in Path.cwd().glob(pattern):
            try:
                if file_path.is_file():
                    file_path.unlink()
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
            except:
                pass