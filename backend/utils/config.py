"""
Configuration management for AI Assistant
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

class ModelConfig(BaseModel):
    llm_model: str = "llama3.1:8b"
    stt_model: str = "base"
    tts_voice: str = "en_US-lessac-medium"
    image_model: Optional[str] = "stable-diffusion-v1-5"
    embedding_model: str = "all-MiniLM-L6-v2"

class AutomationConfig(BaseModel):
    enable_gui_automation: bool = True
    enable_web_automation: bool = True
    enable_file_operations: bool = True
    automation_timeout: int = 300
    safety_checks: bool = True
    screenshot_on_error: bool = True

class SecurityConfig(BaseModel):
    encryption_key_path: str = "data/keys/master.key"
    enable_sandboxing: bool = True
    require_permissions: bool = True
    audit_logging: bool = True
    max_automation_privileges: str = "user"

class StartupConfig(BaseModel):
    auto_start: bool = True
    start_minimized: bool = True
    enable_tray_icon: bool = True
    startup_delay: int = 5

class UpdateConfig(BaseModel):
    auto_update: bool = True
    update_channel: str = "stable"  # stable, beta, dev
    check_interval: int = 86400  # 24 hours
    backup_before_update: bool = True

class LearningConfig(BaseModel):
    enable_learning: bool = True
    pattern_detection: bool = True
    personalization: bool = True
    data_retention_days: int = 365
    min_pattern_frequency: int = 3

class Config:
    """Main configuration class"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config_dir = Path(self.config_path).parent
        self.data_dir = self.config_dir / "data"
        
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "keys").mkdir(exist_ok=True)
        (self.data_dir / "models").mkdir(exist_ok=True)
        (self.data_dir / "logs").mkdir(exist_ok=True)
        (self.data_dir / "audio").mkdir(exist_ok=True)
        (self.data_dir / "temp").mkdir(exist_ok=True)
        
        # Load configuration
        self._load_config()
        
    def _get_default_config_path(self) -> str:
        """Get default configuration path based on OS"""
        if os.name == 'nt':  # Windows
            config_dir = Path(os.environ.get('APPDATA', '')) / "AIAssistant"
        elif os.name == 'posix':  # macOS/Linux
            if os.uname().sysname == 'Darwin':  # macOS
                config_dir = Path.home() / "Library" / "Application Support" / "AIAssistant"
            else:  # Linux
                config_dir = Path.home() / ".config" / "ai-assistant"
        else:
            config_dir = Path.cwd() / "config"
            
        return str(config_dir / "config.json")
    
    def _load_config(self):
        """Load configuration from file or create default"""
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
            else:
                config_data = {}
                
            # Initialize configuration sections
            self.models = ModelConfig(**config_data.get('models', {}))
            self.automation = AutomationConfig(**config_data.get('automation', {}))
            self.security = SecurityConfig(**config_data.get('security', {}))
            self.startup = StartupConfig(**config_data.get('startup', {}))
            self.updates = UpdateConfig(**config_data.get('updates', {}))
            self.learning = LearningConfig(**config_data.get('learning', {}))
            
            # General settings
            self.debug = config_data.get('debug', False)
            self.log_level = config_data.get('log_level', 'INFO')
            self.api_host = config_data.get('api_host', '127.0.0.1')
            self.api_port = config_data.get('api_port', 8000)
            self.frontend_port = config_data.get('frontend_port', 3000)
            
            # Save config to ensure all defaults are written
            self.save_config()
            
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            # Use defaults
            self.models = ModelConfig()
            self.automation = AutomationConfig()
            self.security = SecurityConfig()
            self.startup = StartupConfig()
            self.updates = UpdateConfig()
            self.learning = LearningConfig()
            
            self.debug = False
            self.log_level = 'INFO'
            self.api_host = '127.0.0.1'
            self.api_port = 8000
            self.frontend_port = 3000
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            config_data = {
                'models': self.models.model_dump(),
                'automation': self.automation.model_dump(),
                'security': self.security.model_dump(),
                'startup': self.startup.model_dump(),
                'updates': self.updates.model_dump(),
                'learning': self.learning.model_dump(),
                'debug': self.debug,
                'log_level': self.log_level,
                'api_host': self.api_host,
                'api_port': self.api_port,
                'frontend_port': self.frontend_port
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
                
        except Exception as e:
            logging.error(f"Error saving config: {e}")
    
    def get_data_path(self, *path_parts: str) -> Path:
        """Get path within data directory"""
        return self.data_dir.joinpath(*path_parts)
    
    def get_log_path(self) -> Path:
        """Get log file path"""
        return self.get_data_path("logs", "ai_assistant.log")
    
    def get_db_path(self) -> Path:
        """Get database path"""
        return self.get_data_path("ai_assistant.db")
    
    def get_models_path(self) -> Path:
        """Get models directory path"""
        return self.get_data_path("models")
    
    def get_temp_path(self) -> Path:
        """Get temporary files path"""
        return self.get_data_path("temp")
    
    def get_audio_path(self) -> Path:
        """Get audio files path"""
        return self.get_data_path("audio")
    
    def update_setting(self, section: str, key: str, value: Any):
        """Update a specific setting"""
        if hasattr(self, section):
            section_obj = getattr(self, section)
            if hasattr(section_obj, key):
                setattr(section_obj, key, value)
                self.save_config()
            else:
                raise ValueError(f"Setting {key} not found in section {section}")
        else:
            # Direct setting
            if hasattr(self, key):
                setattr(self, key, value)
                self.save_config()
            else:
                raise ValueError(f"Setting {key} not found")
    
    def get_setting(self, section: str, key: str, default: Any = None) -> Any:
        """Get a specific setting"""
        if hasattr(self, section):
            section_obj = getattr(self, section)
            return getattr(section_obj, key, default)
        else:
            return getattr(self, key, default)
    
    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        self.models = ModelConfig()
        self.automation = AutomationConfig()
        self.security = SecurityConfig()
        self.startup = StartupConfig()
        self.updates = UpdateConfig()
        self.learning = LearningConfig()
        
        self.debug = False
        self.log_level = 'INFO'
        self.api_host = '127.0.0.1'
        self.api_port = 8000
        self.frontend_port = 3000
        
        self.save_config()
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration and return any issues"""
        issues = []
        
        # Check required directories
        required_dirs = [
            self.get_data_path("keys"),
            self.get_data_path("models"),
            self.get_data_path("logs"),
            self.get_data_path("audio"),
            self.get_data_path("temp")
        ]
        
        for dir_path in required_dirs:
            if not dir_path.exists():
                issues.append(f"Missing directory: {dir_path}")
        
        # Check port availability
        import socket
        for port in [self.api_port, self.frontend_port]:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex((self.api_host, port)) == 0:
                    issues.append(f"Port {port} is already in use")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }