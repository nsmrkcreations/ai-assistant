"""
Logging configuration for AI Assistant
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry)

def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    enable_console: bool = True,
    enable_json: bool = False,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """Setup logging configuration"""
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        
        if enable_json:
            console_formatter = JSONFormatter()
        else:
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        
        if enable_json:
            file_formatter = JSONFormatter()
        else:
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
        
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('chromadb').setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Level: {log_level}, File: {log_file}")

class ContextLogger:
    """Logger with context information"""
    
    def __init__(self, name: str, context: dict = None):
        self.logger = logging.getLogger(name)
        self.context = context or {}
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with context"""
        extra = {**self.context, **kwargs}
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        extra = {**self.context, **kwargs}
        self.logger.exception(message, extra=extra)

class SecurityLogger:
    """Specialized logger for security events"""
    
    def __init__(self):
        self.logger = logging.getLogger('security')
        
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        source: str,
        user_id: Optional[str] = None,
        **kwargs
    ):
        """Log security event"""
        extra = {
            'event_type': event_type,
            'severity': severity,
            'source': source,
            'user_id': user_id,
            **kwargs
        }
        
        level = {
            'low': logging.INFO,
            'medium': logging.WARNING,
            'high': logging.ERROR,
            'critical': logging.CRITICAL
        }.get(severity.lower(), logging.WARNING)
        
        self.logger.log(level, f"SECURITY: {description}", extra=extra)
    
    def log_authentication(self, user_id: str, success: bool, source: str):
        """Log authentication attempt"""
        self.log_security_event(
            event_type='authentication',
            severity='medium' if not success else 'low',
            description=f"Authentication {'successful' if success else 'failed'} for user {user_id}",
            source=source,
            user_id=user_id,
            success=success
        )
    
    def log_permission_request(self, user_id: str, resource: str, granted: bool):
        """Log permission request"""
        self.log_security_event(
            event_type='permission',
            severity='medium',
            description=f"Permission {'granted' if granted else 'denied'} for resource {resource}",
            source='permission_manager',
            user_id=user_id,
            resource=resource,
            granted=granted
        )
    
    def log_automation_execution(self, user_id: str, task_type: str, success: bool):
        """Log automation execution"""
        self.log_security_event(
            event_type='automation',
            severity='low' if success else 'medium',
            description=f"Automation task {task_type} {'completed' if success else 'failed'}",
            source='automation_service',
            user_id=user_id,
            task_type=task_type,
            success=success
        )

class PerformanceLogger:
    """Logger for performance metrics"""
    
    def __init__(self):
        self.logger = logging.getLogger('performance')
    
    def log_timing(self, operation: str, duration: float, **kwargs):
        """Log operation timing"""
        extra = {
            'operation': operation,
            'duration': duration,
            'unit': 'seconds',
            **kwargs
        }
        self.logger.info(f"TIMING: {operation} took {duration:.3f}s", extra=extra)
    
    def log_resource_usage(self, cpu_percent: float, memory_mb: float, **kwargs):
        """Log resource usage"""
        extra = {
            'cpu_percent': cpu_percent,
            'memory_mb': memory_mb,
            **kwargs
        }
        self.logger.info(f"RESOURCES: CPU {cpu_percent:.1f}%, Memory {memory_mb:.1f}MB", extra=extra)