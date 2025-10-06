"""
Data models for chat and system communication
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"

class ChatRequest(BaseModel):
    message: str = Field(..., description="User message content")
    context_id: Optional[str] = Field(None, description="Conversation context ID")
    include_audio: bool = Field(False, description="Whether to include TTS audio")
    audio_data: Optional[str] = Field(None, description="Base64 encoded audio data for STT")
    user_id: Optional[str] = Field(None, description="User identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class AutomationTask(BaseModel):
    task_id: str = Field(..., description="Unique task identifier")
    task_type: str = Field(..., description="Type of automation task")
    parameters: Dict[str, Any] = Field(..., description="Task parameters")
    priority: int = Field(1, description="Task priority (1-10)")
    timeout: int = Field(300, description="Task timeout in seconds")

class AutomationResult(BaseModel):
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float
    timestamp: datetime = Field(default_factory=datetime.now)

class Suggestion(BaseModel):
    id: str
    text: str
    action: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)

class ChatResponse(BaseModel):
    message: str = Field(..., description="Assistant response message")
    context_id: str = Field(..., description="Conversation context ID")
    audio_url: Optional[str] = Field(None, description="URL to TTS audio file")
    transcription: Optional[str] = Field(None, description="Speech transcription if from voice")
    automation_result: Optional[AutomationResult] = Field(None, description="Automation execution result")
    suggestions: List[Suggestion] = Field(default_factory=list, description="Proactive suggestions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional response metadata")
    timestamp: datetime = Field(default_factory=datetime.now)

class ComponentStatus(BaseModel):
    name: str
    status: ServiceStatus
    version: Optional[str] = None
    last_check: datetime = Field(default_factory=datetime.now)
    details: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

class SystemStatus(BaseModel):
    overall_status: ServiceStatus
    llm_status: ComponentStatus
    stt_status: ComponentStatus
    tts_status: ComponentStatus
    automation_status: ComponentStatus
    learning_status: ComponentStatus
    security_status: ComponentStatus
    update_status: ComponentStatus
    timestamp: datetime = Field(default_factory=datetime.now)
    uptime: Optional[float] = None
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None

class UserProfile(BaseModel):
    user_id: str
    preferences: Dict[str, Any] = Field(default_factory=dict)
    workflow_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    custom_automations: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class WorkflowPattern(BaseModel):
    pattern_id: str
    application: str
    actions: List[Dict[str, Any]]
    frequency: int
    last_detected: datetime
    automation_suggested: bool = False
    user_approved: Optional[bool] = None

class LearningData(BaseModel):
    interaction_id: str
    user_input: str
    assistant_response: str
    user_feedback: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

class SecurityEvent(BaseModel):
    event_id: str
    event_type: str
    severity: str  # low, medium, high, critical
    description: str
    source: str
    timestamp: datetime = Field(default_factory=datetime.now)
    resolved: bool = False

class UpdateInfo(BaseModel):
    version: str
    release_date: datetime
    description: str
    download_url: str
    checksum: str
    size: int
    critical: bool = False
    changelog: List[str] = Field(default_factory=list)